

import json as J

import numpy

from metagrok.fileio import to_fd

def load(fd_or_name, **kwargs):
  with to_fd(fd_or_name) as fd:
    return J.load(fd, **dict(kwargs, object_hook = decode_ndarray))

def loads(string, **kwargs):
  return J.loads(string, **dict(kwargs, object_hook = decode_ndarray))

def dump(obj, fd_or_name, **kwargs):
  with to_fd(fd_or_name, mode = 'w') as fd:
    return J.dump(obj, fd, **dict(kwargs, cls = NumpyEncoder))

def dumps(obj, **kwargs):
  return J.dumps(obj, **dict(kwargs, cls = NumpyEncoder))

def decode_ndarray(obj):
  if isinstance(obj, dict) and obj.get('__type') == 'numpy.ndarray':
    return numpy.asarray(obj['data'], dtype = obj['dtype'])
  return obj

class NumpyEncoder(J.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, numpy.integer):
      return int(obj)
    elif isinstance(obj, numpy.floating):
      return float(obj)
    elif isinstance(obj, numpy.ndarray):
      return dict(
          __type = 'numpy.ndarray',
          data = obj.tolist(),
          dtype = obj.dtype.name)
    else:
      return super(NumpyEncoder, self).default(obj)
