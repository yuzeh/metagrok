import collections
import glob
import logging
import multiprocessing as mp
import numpy as np
import os
import shutil
import six
import subprocess
import sys
import time
import threading
import torch

from metagrok import battlelogs
from metagrok import config
from metagrok import constants
from metagrok import formats
from metagrok import mail
from metagrok import np_json as json
from metagrok import torch_policy
from metagrok import utils

from metagrok.scheduler import Scheduler
from metagrok.methods import learner

from metagrok.pkmn.games import Game
from metagrok.pkmn import reward_shaper
from metagrok.pkmn.engine.player import EnginePkmnPlayer

from metagrok.torch_utils.data import TTensorDictDataset
from metagrok.torch_utils import debug as dbg


def simulate_and_rollup(expt_name, base_dir, parallelism, cuda):
  logger = logging.getLogger('simulate_and_rollup')

  expt = json.load(expt_name)

  # 1: Figure out which iteration we are running
  current_iter = divine_current_iteration(base_dir)
  iter_dir = os.path.join(base_dir, 'iter%06d' % current_iter)
  utils.mkdir_p(iter_dir)
  logger.info('Current iteration: %d', current_iter)

  # 2: Load the current policy file
  policy_tag = divine_current_policy_tag(expt, iter_dir, current_iter)
  logger.info('Using policy: %s', policy_tag)
  policy = torch_policy.load(policy_tag)

  # do a NaN check here
  for name, param in policy.named_parameters():
    if torch.isnan(param).any().item():
      raise ValueError('Encountered nan in latest model in parameter ' + name)

  rollup_fname = os.path.join(iter_dir, 'rollup.npz')
  assert not os.path.isfile(rollup_fname), 'rollup detected means matches already simulated'

  battles_dir = os.path.join(iter_dir, 'battles')
  utils.mkdir_p(battles_dir)
  num_battles = len([d
    for d in glob.glob(os.path.join(battles_dir, '*'))
    if len(os.listdir(d)) == 2])

  total_matches = expt['simulate_args']['num_matches']
  num_battles_remaining = total_matches - num_battles
  logger.info('%d battles left to simulate for this iteration', num_battles_remaining)
  if num_battles_remaining:
    start_time = time.time()

    def spawn_battler(bid):
      tag = str(bid)
      logger.info('Spawn battler with ID %s', bid)
      env = os.environ.copy()
      env['OMP_NUM_THREADS'] = '1'
      env['MKL_NUM_THREADS'] = '1'
      err_fd = open('/tmp/%03d.err.log' % bid, 'w')
      args = ['./rp', 'metagrok/exe/simulate_worker.py',
        policy_tag,
        expt.get('format', 'gen7randombattle'),
        str(bid),
      ]
      if 'epsilon' in expt['simulate_args']:
        args.append('--epsilon')
        args.append(str(expt['simulate_args']['epsilon']))
      if 'p2' in expt['simulate_args']:
        args.append('--p2-policy-tag')
        args.append(str(expt['simulate_args']['p2']))
      rv = subprocess.Popen(
        args,
        stdout = subprocess.PIPE,
        stdin = subprocess.PIPE,
        stderr = err_fd,
        env = env,
        encoding = 'utf-8',
        bufsize = 0,
      )
      os.system('taskset -p -c %d %d' % (bid % mp.cpu_count(), rv.pid))
      return rv, err_fd

    num_blocks = 0
    battle_number = num_battles

    workers, fds = list(zip(*[spawn_battler(i) for i in range(parallelism)]))
    for i in range(num_battles_remaining):
      workers[i % len(workers)].stdin.write('battle\n')
    
    while battle_number < total_matches:
      time.sleep(0.1)
      for w in workers:
        line = w.stdout.readline().strip()
        if line:
          proc_battle_dir, num_blocks_in_battle = line.split()
          num_blocks_in_battle = int(num_blocks_in_battle)
          num_blocks += num_blocks_in_battle
          battle_dir = os.path.join(battles_dir, '%06d' % battle_number)
          shutil.rmtree(battle_dir, ignore_errors = True)
          shutil.move(proc_battle_dir, battle_dir)
          battle_number += 1
          current_pct = int(100 * battle_number / total_matches)
          prev_pct = int(100 * (battle_number - 1) / total_matches)

          if current_pct > prev_pct:
            logger.info('Battle %s (%s%%) completed. Num blocks: %s',
              battle_number, current_pct, num_blocks_in_battle)

          if battle_number >= total_matches:
            break
      for fd in fds:
        fd.flush()

    for i, w in enumerate(workers):
      logger.info('Shutting down worker %s', i)
      w.stdin.write('done\n')
      w.communicate()

    for fd in fds:
      fd.close()

    for fname in glob.glob('/tmp/*.err.log'):
      os.remove(fname)

    total_time = time.time() - start_time
    logger.info('Ran %d blocks in %ss, rate = %s block/worker/s',
      num_blocks, total_time, float(num_blocks) / len(workers) / total_time)

  logger.info('Rolling up files...')
  rollup_fname = os.path.join(iter_dir, 'rollup.npz')
  num_records = perform_rollup(expt, iter_dir, policy_tag, parallelism, rollup_fname)

  expt_shortname = os.path.splitext(os.path.basename(expt_name))[0]

  return dict(
    a__status = 'Simulations complete',
    dir = iter_dir,
    iter = current_iter + 1,
    name = expt_shortname,
    num_matches = num_battles_remaining,
    num_total_records = num_records,
    subject = 'Experiment log: ' + base_dir,
    z__params = expt,
  )


def perform_policy_update(expt_name, base_dir, parallelism, cuda):
  logger = logging.getLogger('perform_policy_update')

  expt = json.load(expt_name)

  # 1: Figure out which iteration we are running
  current_iter = divine_current_iteration(base_dir)
  iter_dir = os.path.join(base_dir, 'iter%06d' % current_iter)
  utils.mkdir_p(iter_dir)
  logger.info('Current iteration: %d', current_iter)

  # 2: Load the current policy file
  policy_tag = divine_current_policy_tag(expt, iter_dir, current_iter)
  logger.info('Using policy: %s', policy_tag)

  rollup_fname = os.path.join(iter_dir, 'rollup.npz')
  assert os.path.isfile(rollup_fname), 'cannot do policy update without rollup file'

  start_time = time.time()
  npz = np.load(rollup_fname)
  all_extras = collections.defaultdict(list)
  for iter_offset in range(expt.get('updater_buffer_length_iters', 1)):
    iter_num = current_iter - iter_offset
    if iter_num >= 0:
      r_fname = os.path.join(base_dir, 'iter%06d' % iter_num, 'rollup.npz')
      logger.info('Loading: %s', r_fname)
      npz = np.load(r_fname)
      for k in npz.files:
        all_extras[k].append(npz[k])
  extras = {}
  for k, vs in list(all_extras.items()):
    extras[k] = np.concatenate(vs)
    # This is a hack to save on memory.
    # The optimal solution is to
    #   1) read each rollup to determine array size,
    #   2) pre-allocate a big array and
    #   3) fill.
    # (metagrok/methods/learner.py does a similar thing but operates on jsons files.)
    del all_extras[k]
    del vs
  del all_extras
  learner.post_prepare(extras)

  total_time = time.time() - start_time
  logger.info('Loaded rollups in %ss', total_time)

  start_time = time.time()
  logger.info('Starting policy update...')
  extras = {k: torch.from_numpy(v) for k, v in extras.items()}
  extras = TTensorDictDataset(extras, in_place_shuffle = True)

  policy = torch_policy.load(policy_tag)
  updater_cls = utils.hydrate(expt['updater'])
  updater_args = dict(expt['updater_args'])
  for k, v in expt.get('updater_args_schedules', {}).items():
    updater_args[k] = Scheduler(v).select(current_iter)
  updater = updater_cls(policy = policy, **updater_args)
  if config.use_cuda():
    policy.cuda()

  updater.update(extras)
  if config.use_cuda():
    policy.cpu()

  total_time = time.time() - start_time
  logger.info('Ran policy update in %ss', total_time)

  with open('/tmp/end_model_file.pytorch', 'wb') as fd:
    torch.save(policy.state_dict(), fd)
  end_model_file = os.path.join(iter_dir, 'end.pytorch')
  shutil.move('/tmp/end_model_file.pytorch', end_model_file)

  next_iter_dir = os.path.join(base_dir, 'iter%06d' % (current_iter + 1))
  next_start_model_file = os.path.join(next_iter_dir, 'start.pytorch')
  utils.mkdir_p(next_iter_dir)
  shutil.copy(end_model_file, next_start_model_file)
  logger.info('Wrote to %s', next_start_model_file)

  expt_shortname = os.path.splitext(os.path.basename(expt_name))[0]

  return dict(
    a__status = 'Policy update complete',
    dir = iter_dir,
    iter = current_iter + 1,
    name = expt_shortname,
    next_start_model_file = next_start_model_file,
    subject = 'Experiment log: ' + base_dir,
    z__params = expt,
  )


def run_one_iteration(expt_name, base_dir, parallelism = mp.cpu_count(), cuda = False):
  logger = logging.getLogger('run_one_iteration')

  expt = json.load(expt_name)

  # 1: Figure out which iteration we are running
  current_iter = divine_current_iteration(base_dir)
  iter_dir = os.path.join(base_dir, 'iter%06d' % current_iter)
  utils.mkdir_p(iter_dir)
  logger.info('Current iteration: %d', current_iter)

  # 2: If rollup file exists, we've finished simulating battles
  rollup_fname = os.path.join(iter_dir, 'rollup.npz')
  if not os.path.isfile(rollup_fname):
    # 3: If not, finish simulations and make the rollup file.
    simulate_and_rollup(expt_name, base_dir, parallelism, cuda)

  # 4: Do gradient update, write to end.pytorch
  result = perform_policy_update(expt_name, base_dir, parallelism, cuda)
  next_start_model_file = result['next_start_model_file']

  # 5: Email
  subject = 'Iteration [%d/%d] finished for [%s]' % (current_iter + 1, expt['num_iters'], base_dir)
  expt_shortname = os.path.splitext(os.path.basename(expt_name))[0]
  tag = 'eval-%s-%03d' % (expt_shortname, current_iter)
  message = '''To evaluate, run:
  
  scripts/deploy.sh %s smogeval ./rp metagrok/exe/smogon_eval.py %s:%s
  ''' % (tag, expt['policy_cls'], next_start_model_file)

  return dict(
    dir = iter_dir,
    iter = current_iter + 1,
    message = message,
    name = expt_shortname,
    next_start_model_file = next_start_model_file,
    params = expt,
    subject = subject,
  )

def divine_current_iteration(base_dir):
  prefix = os.path.join(base_dir, 'iter')
  iter_dirs = glob.glob(prefix + '*')
  if not iter_dirs:
    current_iter = 0
  else:
    current_iter = max(int(iter_dir[len(prefix):]) for iter_dir in iter_dirs)
    iter_dir = '%s%06d' % (prefix, current_iter)
    if os.path.isfile(os.path.join(iter_dir, 'end.pytorch')):
      current_iter += 1
  return current_iter

def divine_current_policy_tag(expt, iter_dir, current_iter):
  start_model_file = os.path.join(iter_dir, 'start.pytorch')
  if not os.path.isfile(start_model_file):
    assert current_iter == 0
    if expt.get('start_model'):
      tag = '%s:%s' % (expt['policy_cls'], expt['start_model'])
      policy = torch_policy.load(tag)
    else:
      policy = torch_policy.load(expt['policy_cls'])
    with open(start_model_file, 'wb') as fd:
      torch.save(policy.state_dict(), fd)
    del policy
  return '%s:%s' % (expt['policy_cls'], start_model_file)

def perform_rollup(expt, iter_dir, policy_tag, parallelism, rollup_fname):
  policy = torch_policy.load(policy_tag)
  rew = expt['reward_args']
  shaper = reward_shaper.create(**rew['shaping'])

  iter_dir_arg = iter_dir
  if expt.get('player'):
    iter_dir_arg = list(utils.find(iter_dir, '%s.jsons.gz' % expt['player']))

  extras = learner.rollup(
      policy, iter_dir_arg, rew['gamma'], rew['lam'], shaper,
      num_workers = parallelism,
      progress_type = 'log')
  tmp_rollup_name = '/tmp/rollup.npz'
  np.savez_compressed(tmp_rollup_name, **extras)
  shutil.move(tmp_rollup_name, rollup_fname)

  # 4b. zip up battle files
  subprocess.check_call(['zip', '-q', '-r', '/tmp/battles', 'battles'], cwd = iter_dir)
  shutil.move('/tmp/battles.zip', os.path.join(iter_dir, 'battles.zip'))
  shutil.rmtree(os.path.join(iter_dir, 'battles'))
  return list(extras.values())[0].shape[0]

_name_to_prog = dict(
  run_one_iteration = run_one_iteration,
  simulate_and_rollup = simulate_and_rollup,
  perform_policy_update = perform_policy_update,
)

def main():
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('expt_name')
  parser.add_argument('base_dir')
  parser.add_argument('--cuda', action = 'store_true')
  parser.add_argument('--parallelism', type = int, default = mp.cpu_count())
  parser.add_argument('--prog', choices = list(_name_to_prog.keys()), default = 'run_one_iteration')

  args = parser.parse_args()

  from metagrok import remote_debug
  remote_debug.listen()

  config.set_cuda(args.cuda)

  utils.mkdir_p('/tmp')

  logger = utils.default_logger_setup()
  fhandler = logging.FileHandler('/tmp/iteration.log')
  fhandler.setFormatter(logging.Formatter(constants.LOG_FORMAT))
  fhandler.setLevel(logging.INFO)
  logger.addHandler(fhandler)

  prog = _name_to_prog[args.prog]

  time_begin = utils.iso_ts()
  result = prog(
    expt_name = args.expt_name,
    base_dir = args.base_dir,
    parallelism = args.parallelism,
    cuda = args.cuda,
  )
  time_end = utils.iso_ts()

  result['time_begin'] = time_begin
  result['time_end'] = time_end

  fhandler.close()

  if args.prog != 'simulate_and_rollup' and result['iter'] % 5 == 0:
    mail.send(
      result['subject'],
      json.dumps(result, indent = 2, sort_keys = True),
      attachments = ['/tmp/iteration.log'])
  os.remove('/tmp/iteration.log')

if __name__ == '__main__':
  main()