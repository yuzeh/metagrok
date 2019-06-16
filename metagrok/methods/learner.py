import glob
import logging
import os
import shutil
import six
import sys

import multiprocessing as mulproc
from multiprocessing import sharedctypes
import threading
if sys.version_info[0] == 2:
    import Queue as queue
else:
    import queue

import numpy as np

import torch
import tqdm

from metagrok import battlelogs, config, utils, fileio
from metagrok.utils import mkdir_p
from metagrok.torch_policy import TorchPolicy
from metagrok.torch_utils.data import NDArrayDictDataset

logger = logging.getLogger(__name__)

def run(
    num_iters,
    out_dir,
    simulate_fn,
    gamma,
    lam,
    delete_logs,
    updater = None,
    policy = None,
):

  if updater:
    policy = updater.policy

  models = load_latest_policy(out_dir, policy)
  start_iter = len(models)

  for iter_num in range(num_iters):
    iter_num += start_iter
    logger.info('Iteration %05d', iter_num)

    run_iter(out_dir, iter_num, simulate_fn, clean = updater)

    if updater:
      run_update(updater, iter_num, out_dir, gamma, lam, delete_logs)

def load_latest_policy(out_dir, policy):
  model_dir = os.path.join(out_dir, 'models')
  mkdir_p(model_dir)

  models = sorted(glob.glob('%s/*.pytorch' % model_dir))

  if models:
    policy.load_state_dict(torch.load(sorted(models)[-1]))
  else:
    torch.save(policy.state_dict(), '%s/%s.pytorch' % (model_dir, mk_iter_name(0)))
    models = sorted(glob.glob('%s/*.pytorch' % model_dir))

  policy.type(config.tt())

  if config.use_cuda():
    policy = policy.cuda()

  return models

def mk_iter_name(iter_num): return 'iter%05d' % iter_num

def run_iter(out_dir, iter_num, simulate_fn, clean = False):
  iter_name = mk_iter_name(iter_num)
  iter_dir = os.path.join(out_dir, iter_name)

  if clean and os.path.isdir(iter_dir):
    shutil.rmtree(iter_dir)

  mkdir_p(iter_dir)
  simulate_fn(iter_dir)

def run_update(updater, iter_num, out_dir, gamma, lam, delete_logs):
  match_dir = os.path.join(out_dir, 'matches')
  model_dir = os.path.join(out_dir, 'models')

  mkdir_p(model_dir)
  mkdir_p(match_dir)

  iter_name = mk_iter_name(iter_num)
  iter_dir = os.path.join(out_dir, iter_name)

  fname = os.path.join(match_dir, '%s.npz' % iter_name)
  data = rollup(updater.policy, iter_dir, gamma, lam)
  np.savez_compressed(fname, **data)

  results = check_results(iter_dir)
  logger.info('Results: %s', results)

  if delete_logs:
    shutil.rmtree(iter_dir)

  extras = prepare([sorted(glob.glob('%s/*.npz' % match_dir))[-1]])
  post_prepare(extras)
  dataset = NDArrayDictDataset(extras)

  updater.update(dataset)
  mname = os.path.join(model_dir, '%s.pytorch' % iter_name)
  torch.save(updater.policy.state_dict(), mname)

def check_results(iter_dir):
  results = {'winner': 0, 'loser': 0, 'tie': 0}
  for fname in utils.find(iter_dir, '*.jsons.gz'):
    key = battlelogs.result_only(fname)
    results[key] += 1
  return results

def rollup(policy, iter_dir, gamma, lam, reward_shaper = None, num_workers = 0,
    progress_type = 'bar'):
  # Concatenate rollouts from this iteration, and store in parallel arrays:
  # - Features
  # - Action taken (as an index)
  # - Actual Return
  # - Advantage
  assert progress_type in {'bar', 'log', 'none'}

  if isinstance(iter_dir, six.string_types):
    fnames = list(utils.find(iter_dir, '*.jsons.gz'))
  else:
    assert isinstance(iter_dir, list)
    fnames = iter_dir

  fnames = sorted(fnames)

  logger.info('Rollup has %s files' % len(fnames))
  pool = mulproc.Pool()
  linecount = dict(zip(fnames, pool.map(utils.linecount, fnames)))
  pool.close()

  start_rows = {}
  nrows = 0
  for fname in fnames:
    start_rows[fname] = nrows
    nrows += (linecount[fname] - 1)

  logger.info('Rollup has %s rows' % nrows)

  # read the first file, to see what the sizes are
  t = battlelogs.parse(fnames[0], gamma = gamma, lam = lam, reward_shaper = reward_shaper)[-1]
  fs = policy.extract(t['state'], t['candidates'])
  n_actions = 0
  if 'mask' in fs:
    n_actions = fs['mask'].shape[0]

  type_info = {
      'actions': ((nrows,), 'int64'),
      'advantages': ((nrows,), config.nt()),
      'returns': ((nrows,), config.nt()),
      'value_preds': ((nrows,), config.nt()),
  }

  for k in ['probs', 'log_probs']:
    if k in t:
      na = max(t[k].shape[0], n_actions)
      type_info[k] = ((nrows, na), config.nt())

  for k, v in fs.iteritems():
    type_info['features_' + k] = ((nrows,) + v.shape, v.dtype)

  if num_workers > 0:
    mk_buf_fn = _mk_RawArray
    queue_mod = mulproc
  else:
    mk_buf_fn = _mk_volatile_buffer
    queue_mod = queue

  underlying = {}
  data = {}
  for k, (shape, dtype) in type_info.iteritems():
    size = six.moves.reduce(lambda x, y: x * y, shape, 1)
    u = underlying[k] = mk_buf_fn(shape, dtype)
    d = np.frombuffer(u, dtype = dtype, count = size)
    d.shape = shape
    data[k] = d

  in_queue = queue_mod.Queue()
  for kv in start_rows.iteritems():
    in_queue.put(kv)
  out_queue = queue_mod.Queue()

  kwargs = dict(
      type_info = type_info,
      underlying = underlying,
      policy_pkl = policy.pkl(),
      gamma = gamma,
      lam = lam,
      reward_shaper = reward_shaper,
      in_queue = in_queue,
      out_queue = out_queue,
  )

  # Read the rest of the files
  if num_workers == 0:
    in_queue.put(None)
    worker = threading.Thread(target = _worker_loop, kwargs = kwargs)
    worker.daemon = True
    worker.start()
    workers = [worker]
  else:
    workers = [
        mulproc.Process(target = _worker_loop, kwargs = kwargs)
        for _ in six.moves.range(num_workers)]
    for worker in workers:
      worker.daemon = True
      in_queue.put(None)
      worker.start()

  pbar = fnames
  total = len(fnames)
  if progress_type == 'bar':
    pbar = tqdm.tqdm(pbar)

  for i, _ in enumerate(pbar):
    fname = out_queue.get()
    if isinstance(fname, Exception):
      raise fname
    if progress_type == 'bar':
      pbar.set_description(fname)
    elif progress_type == 'log':
      current_pct = int(100 * (i + 1) / total)
      prev_pct = int(100 * i / total)
      if current_pct > prev_pct:
        logger.info('Rolled up: [%d/%d (%d%%)] %s', i + 1, total, current_pct, fname)

  for worker in workers:
    worker.join()

  return data

def _mk_RawArray(shape, dtype):
  size = six.moves.reduce(lambda x, y: x * y, shape, 1)

  dtype = np.dtype(dtype)

  return sharedctypes.RawArray('B', size * dtype.itemsize)

def _mk_volatile_buffer(shape, dtype):
  return np.getbuffer(np.zeros(shape, dtype = dtype))

def _worker_loop(
    type_info, underlying,
    policy_pkl, gamma, lam, reward_shaper,
    in_queue, out_queue):

  policy = TorchPolicy.unpkl(policy_pkl)
  data = {}
  for k, (shape, dtype) in type_info.iteritems():
    size = six.moves.reduce(lambda x, y: x * y, shape, 1)
    d = np.frombuffer(underlying[k], dtype = dtype, count = size)
    d.shape = shape
    data[k] = d

  try:
    while True:
      r = in_queue.get()
      if r is None:
        break
      fname, row_num = r
      ts = battlelogs.parse(fname, gamma = gamma, lam = lam, reward_shaper = reward_shaper)
      for t in ts:
        fs = policy.extract(t['state'], t['candidates'])
        _rollup_assign(data, t, fs, row_num)
        row_num += 1
      out_queue.put(fname)
  except Exception as e:
    out_queue.put(e)

def _rollup_assign(data, t, fs, row_num):
  for k, v in fs.iteritems():
    data['features_' + k][row_num] = v

  data['actions'][row_num] = t['action']
  data['advantages'][row_num] = t['advantage']
  data['value_preds'][row_num] = t['value_pred']
  data['returns'][row_num] = t['return']
  for k in ['probs', 'log_probs']:
    if k in t:
      data[k][row_num, :t[k].shape[0]] = t[k]

def prepare(match_files):
  shapes = {}
  dtypes = {}
  data = {}
  N = 0
  logger.info('Pre-reading files to understand how much to allocate')
  for match_file in match_files:
    logger.info('Pre-reading: ' + match_file)
    for name, shape, dtype in fileio.npz_headers(match_file):
      dtypes[name] = dtype
      shapes[name] = shape[1:]
    N += shape[0]

  for k in shapes:
    logger.info('Allocating {shape = %s, dtype = %s} for %s', shapes[k], dtypes[k], k)
    data[k] = np.zeros((N,) + shapes[k], dtype = dtypes[k])

  logger.info('N = %s', N)

  i = 0
  for match_file in match_files:
    logger.debug('Reading: ' + match_file)
    with np.load(match_file) as match:
      n = match[match.files[0]].shape[0]
      for k in match.files:
        data[k][i : i + n] = match[k]
      i += n

  extras = {}
  for k, v in data.items():
    if k.startswith('features.'):
      extras['features_' + k[len('features.'):]] = v
    else:
      extras[k] = v

  return extras

def post_prepare(extras):
  adv = extras['advantages']
  adv = adv - adv.mean()
  adv = adv / (1e-8 + adv.std())
  extras['advantages'] = adv

  N = extras['log_probs'].shape[0]
  extras['action_log_probs'] = extras['log_probs'][np.arange(N), extras['actions']]
