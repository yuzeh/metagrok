import time
import logging
import numpy as np

import torch
import torch.nn as nn
import torch.autograd as ag

from metagrok import config
from metagrok import utils

_STRICT_DEFAULT_FALSE = object()

logger = logging.getLogger(__name__)

class TorchPolicy(nn.Module):
  @staticmethod
  def unpkl(arg):
    typ, args, kwargs = arg
    return typ(*args, **kwargs)

  def pkl(self):
    return (type(self), self._mg_args, self._mg_kwargs)

  def __init__(self, *args, **kwargs):
    super(TorchPolicy, self).__init__()
    self._mg_args = args
    self._mg_kwargs = kwargs

  def extract(self, state, candidates):
    raise NotImplementedError

  def forward(self, **kwargs):
    raise NotImplementedError

  def act(self, state, candidates):
    features = self.extract(state, candidates)

    torch_features = {}
    for k, v in features.items():
      v = ag.Variable(torch.from_numpy(np.expand_dims(v, axis = 0)))
      if config.use_cuda():
        v = v.cuda()
      torch_features[k] = v

    value_pred, probs, log_probs = self(**torch_features)

    vp = value_pred.data
    p = probs.data
    lp = log_probs.data

    if config.use_cuda():
      vp = vp.cpu()
      p = p.cpu()
      lp = lp.cpu()

    vp = np.asscalar(vp.numpy())
    p = p.numpy().flatten()
    lp = lp.numpy().flatten()

    return dict(
        value_pred = vp,
        probs = p,
        log_probs = lp,
    )

  def evaluate_batch(self, features, actions, keys = None):
    rv = {}
    keys = keys or {'value', 'probs', 'log_probs', 'action_log_prob', 'dist_entropy'}
    value, probs, log_probs = self(**features)

    if 'value' in keys: rv['value'] = value.squeeze(-1)
    if 'probs' in keys: rv['probs'] = probs
    if 'log_probs' in keys: rv['log_probs'] = log_probs

    if 'action_log_prob' in keys:
      rv['action_log_prob'] = log_probs.gather(1, actions.unsqueeze(-1)).squeeze(-1)

    if 'dist_entropy' in keys:
      rv['dist_entropy'] = -(log_probs * probs).sum(-1)
    return rv

  def compute_diagnostics(self, features):
    value, probs, log_probs = self(**features)
    entropy = -(log_probs * probs).sum(-1)
    return dict(
        value = value.data.squeeze(-1),
        probs = probs.data,
        log_probs = log_probs.data,
        entropy = entropy.data,
    )

  def load_state_dict(self, state_dict, strict = _STRICT_DEFAULT_FALSE):
    if strict is _STRICT_DEFAULT_FALSE:
      strict = False
    return super(TorchPolicy, self).load_state_dict(state_dict, strict)

def load(arg):
  if arg.startswith(','):
    class_name = arg[1:]
    return utils.hydrate(class_name)()

  parts = arg.split(':', 1)
  assert len(parts) <= 2
  if len(parts) == 2:
    class_name, model_file = parts
  else:
    class_name, = parts
    model_file = ''

  policy = utils.hydrate(class_name)()
  if model_file:
    state_dict = torch.load(model_file)
    policy.load_state_dict(state_dict)
  
  return policy
