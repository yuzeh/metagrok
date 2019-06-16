import numpy as np
import torch

from metagrok.constants import DTYPE
from metagrok import np_json as json

# Load the project config. This contains directories for everything
try:
  _config = json.load('config.json')
except IOError:
  raise Exception('`config.json` file not found')
except ValueError:
  raise Exception('`config.json` file is malformed')

_use_cuda = []

def use_cuda():
  assert len(_use_cuda) == 1, 'please call set_cuda first'
  return _use_cuda[0]

def set_cuda(cuda):
  assert len(_use_cuda) == 0, 'set_cuda already called'

  if cuda and not torch.cuda.is_available():
    raise ValueError('Cannot use cuda, not available')
  _use_cuda.append(cuda)

def nt():
  return DTYPE

_nt_to_tt = {
  'float16': 'HalfTensor',
  'float32': 'FloatTensor',
  'float64': 'DoubleTensor',
}

def tt():
  tt = _nt_to_tt[nt()]
  if use_cuda():
    return '.'.join(['torch', 'cuda', tt])
  return '.'.join(['torch', tt])

def nptype(v):
  return np.dtype(nt()).type(v)

def get(key):
  return _config[key]
    