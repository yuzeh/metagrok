import torch

from metagrok import config

def _ctor(nt, cuda):
  base = torch
  if cuda:
    base = torch.cuda

  if nt == 'float16':
    return base.HalfTensor
  elif nt == 'float32':
    return base.FloatTensor
  elif nt == 'float64':
    return base.DoubleTensor

  raise ValueError('Unknown nt: ' + nt)

def zeros(*args, **kwargs):
  cuda = kwargs.get('cuda')
  return _ctor(config.nt(), cuda)(*args).fill_(0)
