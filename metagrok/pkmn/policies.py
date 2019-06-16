import numpy as np
import torch

from metagrok import config

from metagrok.torch_policy import TorchPolicy

class FirstAvailableActionPolicy(TorchPolicy):
  def extract(self, state, candidates):
    rv = {}
    rv['mask'] = np.asarray([float(bool(c)) for c in candidates]).astype(config.nt())
    return rv

  def forward(self, **kwargs):
    mask = kwargs['mask']
    num_players, num_choices = mask.shape
    v = torch.zeros((num_players, 1))
    ps = torch.zeros((num_players, num_choices))
    lps = torch.zeros((num_players, num_choices))
    for i in range(num_players):
      for j in range(num_choices):
        if mask[i, j].item() > 0:
          ps[i, j] = 1
          break
    return v, ps, lps
