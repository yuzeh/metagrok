import collections
import logging
import glob
import os
import re

import random

import torch
import torch.cuda
import torch.autograd as ag
import torch.nn as nn
import torch.optim as optim
import torch.random

from metagrok import config
from metagrok import np_json as json
from metagrok import utils
from metagrok.torch_utils import dataloader

DEPRECATED_KEYS = [
  'l2_regularization',
  'l2_regularization_squared',
]

class PolicyUpdater(object):
  logger = logging.getLogger('PolicyUpdater')

  def __init__(self, **kwargs):
    # TODO: dataset augmentation
    for key in DEPRECATED_KEYS:
      if key in kwargs:
        raise ValueError('Deprecated PolicyUpdater option: ' + key)

    self._policy = kwargs['policy']
    self._num_epochs = kwargs['num_epochs']
    self._entropy_coef = kwargs.get('entropy_coef')
    self._value_coef = kwargs.get('value_coef', 1.)
    self._vbatch_size = kwargs['vbatch_size']
    self._pbatch_size = kwargs.get('pbatch_size', self._vbatch_size)

    assert self._vbatch_size % self._pbatch_size == 0, \
      '%s does not divide %s' % (self._pbatch_size, self._vbatch_size)

    self._weight_decay = kwargs.get('weight_decay', 0.)
    self._max_grad_norm = kwargs.get('max_grad_norm')
    self._num_workers = kwargs.get('num_workers', 0)
    self._batch_size_scaling = kwargs.get('batch_size_scaling')
    self._early_stopping = kwargs.get('early_stopping')

    self._opt_lr = kwargs['opt_lr']
    self._optimizer = None
    self._out_dir = kwargs.get('out_dir')
    self._policy.eval()

    self._hooks = []

  def add_hook(self, hook):
    self._hooks.append(hook)

  def _get_batch_iterator(self, dataset):
    if getattr(dataset, 'in_place_shuffle'):
      dataset.shuffle_()
      itr = dataloader.DataLoader(
          dataset,
          batch_sampler = dataloader.SequentialBatchSampler(
            len(dataset),
            self._pbatch_size,
            drop_last = True),
          num_workers = self._num_workers)
    else:
      itr = dataloader.DataLoader(
          dataset,
          batch_size = self._pbatch_size,
          shuffle = True,
          collate_fn = dataloader.default_collate,
          num_workers = self._num_workers,
          drop_last = True)
    return itr

  def _setup(self):
    # set lr to some dummy value
    self._optimizer = optim.Adam(
      self.policy.parameters(),
      lr = 1e-4,
      weight_decay = self._weight_decay,
    )

    if self._out_dir:
      utils.mkdir_p(self._out_dir)
      result = _load_latest(self._out_dir)

      if result:
        model_fname = result['model']
        optimizer_fname = result['optimizer']
        random_fname = result['random']
        self._current_epoch = result['epoch']

        self.logger.info('Loading random state: %s', random_fname)
        rand = torch.load(random_fname)
        torch.cuda.random.set_rng_state_all(rand['pytorch_cuda'])
        torch.random.set_rng_state(rand['pytorch_cpu'])
        random.setstate(rand['python'])

        self.logger.info('Loading optimizer: %s', optimizer_fname)
        self.optimizer.load_state_dict(torch.load(optimizer_fname))

        self.logger.info('Loading model: %s', model_fname)
        self.policy.load_state_dict(torch.load(model_fname))
      else:
        self._current_epoch = 0
        self._save_checkpoint(override = 0)
    else:
      self._current_epoch = 0

    self._prepare_learning_rate()

  def _save_checkpoint(self, override = None, diagnostics = None):
    epoch = self._current_epoch

    if override is None:
      epoch_id = str(epoch + 1)
    else:
      epoch_id = str(override)
      diagnostics = None

    epoch_id = epoch_id.zfill(len(str(self._num_epochs)))

    model_fname = os.path.join(self._out_dir, _MODEL_TEMPLATE % epoch_id)
    optimizer_fname = os.path.join(self._out_dir, _OPTIMIZER_TEMPLATE % epoch_id)
    random_fname = os.path.join(self._out_dir, _RANDOM_TEMPLATE % epoch_id)
    diag_fname = os.path.join(self._out_dir, _DIAGNOSTICS_TEMPLATE % epoch_id)

    torch.save(self.policy.state_dict(), model_fname)
    torch.save(self.optimizer.state_dict(), optimizer_fname)
    torch.save({
      'python': random.getstate(),
      'pytorch_cpu': torch.random.get_rng_state(),
      'pytorch_cuda': torch.cuda.random.get_rng_state_all(),
    }, random_fname)

    fnames = [model_fname, optimizer_fname, random_fname]
    if diagnostics:
      with open(diag_fname, 'w') as fd:
        json.dump(diagnostics, fd, indent = 2)
      fnames.append(diag_fname)

    for hook in self._hooks:
      hook.on_checkpoint(self, fnames)

  def _compute_losses_on_dataset(self, dataset, optimize = False):
    eval_batch = None

    dataset_size = len(dataset)
    rv = collections.defaultdict(float)
    count = 0
    batch_count = 0
    pbatches_per_vbatch = self._vbatch_size / self._pbatch_size

    for batch in self._get_batch_iterator(dataset):
      # `batch` is actually a dictionary
      batch_size = batch['actions'].shape[0]
      batch_count += 1

      if eval_batch is None:
        eval_batch = batch

      losses = self._compute_losses(batch)

      if optimize:
        total_loss = 0
        for name, loss in losses.iteritems():
          if not name.startswith('_'):
            total_loss += loss / pbatches_per_vbatch
        total_loss.backward()
        
        if batch_count % pbatches_per_vbatch == 0:
          if self._max_grad_norm is not None:
            nn.utils.clip_grad_norm(self.policy.parameters(), self._max_grad_norm)
          self.optimizer.step()
          self.optimizer.zero_grad()

      for name, loss in losses.iteritems():
        rv[name] = (rv[name] * (batch_count - 1) + float(loss.mean().data.item())) / batch_count

      old_count = count
      count += batch_size

      # log every 1%
      old_1pct = int(100. * old_count / dataset_size)
      new_1pct = int(100. * count / dataset_size)
      if old_1pct < new_1pct:
        new_pct = int(100. * count / dataset_size)
        self.logger.info('Processed [%d/%d (%d%%)] examples', count, dataset_size, new_pct)

    del batch
    self.optimizer.zero_grad()
    return eval_batch, rv

  def update(self, dataset, validation = None):
    self.policy.train()

    best_validation_loss = None

    # set up first epoch
    self._setup()

    while self._current_epoch < self._num_epochs:
      self._prepare_learning_rate()
      self.logger.info('Running through training set...')
      eval_batch, train_losses = self._compute_losses_on_dataset(dataset, optimize = True)

      diagnostics = {}
      diagnostics['epoch'] = self._current_epoch + 1
      diagnostics['train'] = compute_metrics(self.policy, eval_batch, train_losses)

      if validation:
        self.logger.info('Running through validation set...')
        eval_batch, val_losses = self._compute_losses_on_dataset(validation, optimize = False)
        diagnostics['val'] = compute_metrics(self.policy, eval_batch, val_losses)

        # Do early stopping check
        if self._early_stopping:
          validation_loss = diagnostics['val']['total']

          if best_validation_loss is None:
            best_validation_loss = validation_loss
          elif best_validation_loss >= validation_loss:
            best_validation_loss = validation_loss
          else:
            self.logger.info('Validation loss has stopped improving, stopping now')
            break
      del eval_batch

      self.logger.info(json.dumps(diagnostics))
      if self._out_dir:
        self._save_checkpoint(diagnostics = diagnostics)

      self._current_epoch += 1

    self.policy.eval()

  def _prepare_learning_rate(self):
    target_lr = None

    if isinstance(self._opt_lr, (float,)):
      target_lr = self._opt_lr
    else:
      assert self._opt_lr
      assert isinstance(self._opt_lr, list)
      assert all(isinstance(d, dict) for d in self._opt_lr)

      self._opt_lr.sort(key = lambda x: x['epoch'])
      assert self._opt_lr[0]['epoch'] == 0, 'First epoch in opt_lr must be 0'

      for step in self._opt_lr:
        if step['epoch'] <= self._current_epoch:
          target_lr = step['opt_lr']

    self.logger.info('Epoch %s, LR is now %s', self._current_epoch, target_lr)
    for param_group in self.optimizer.param_groups:
      param_group['lr'] = target_lr

  def _compute_losses(self, batch):
    extras = _prep(batch)
    update = self.batch_update(self.policy, **extras)
    return update

  def batch_update(self, policy, **kwargs):
    raise NotImplementedError

  @property
  def optimizer(self):
    return self._optimizer

  @property
  def policy(self):
    return self._policy

def compute_metrics(policy, batch, losses):
  rv = {}

  dataset = _prep(batch)

  features = dataset['features']
  results = policy.compute_diagnostics(features)

  if 'log_probs' in dataset:
    olps = dataset['log_probs'].data
    rv['kl'] = float((results['probs'] * (results['log_probs'] - olps)).sum(-1).mean().item())
  else:
    rv['kl'] = float('inf')

  rts = dataset['returns'].data
  rv['ev_vf'] = float(1 - (results['value'] - rts).var().item() / (1e-8 + rts.var().item()))
  rv['ent'] = float(results['entropy'].mean().item())

  total = 0
  for name, loss in losses.iteritems():
    if not name.startswith('_'):
      total += loss
    rv[name] = loss
  rv['total'] = total
  return rv

def _var(batch):
  rv = {}
  for k, v in batch.iteritems():
    v = ag.Variable(v)
    rv[k] = v
  return rv

def _prep(batch):
  if config.use_cuda():
    batch = {k: v.cuda() for k, v in batch.iteritems()}

  batch = _var(batch)
  extras = {}
  features = {}
  for k, v in batch.iteritems():
    if k.startswith('features_'):
      features[k[len('features_'):]] = v
    else:
      extras[k] = v

  extras['features'] = features
  return extras

def _load_latest(path):
  def load_filenames(template):
    regex = template.replace('.', '\\.') % '(\d+)'
    fnames = glob.glob(os.path.join(path, template % '*'))
    rv = []
    for fname in fnames:
      bname = os.path.basename(fname)
      epoch = int(re.match(regex, bname).group(1), base = 10)
      rv.append((epoch, fname))
    return sorted(rv, reverse = True)

  models = load_filenames(_MODEL_TEMPLATE)
  optimizers = load_filenames(_OPTIMIZER_TEMPLATE)
  randoms = load_filenames(_RANDOM_TEMPLATE)

  if not models and not optimizers and not randoms:
    return None

  if not (models and optimizers and randoms):
    error_msg = '''Something went wrong!
      models: %s
      optimizers: %s
      randoms: %s''' % (models, optimizers, randoms)
    raise ValueError(error_msg)

  m_epoch, model = models[0]
  o_epoch, optimizer = optimizers[0]
  r_epoch, rand = randoms[0]

  if not (m_epoch == o_epoch and m_epoch == r_epoch):
    error_msg = '''Mismatch in latest epoch for model and optimizer:
      models: %s
      optimizers: %s
      randoms: %s''' % (models, optimizers, randoms)
    raise ValueError(error_msg)

  return dict(epoch = m_epoch, model = model, optimizer = optimizer, random = rand)

_MODEL_TEMPLATE = 'model.%s.pytorch'
_OPTIMIZER_TEMPLATE = 'optimizer.%s.pytorch'
_RANDOM_TEMPLATE = 'random.%s.pytorch'
_DIAGNOSTICS_TEMPLATE = 'diagnostics.%s.json'
