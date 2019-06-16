import collections
import functools
import six

import numpy as np

from metagrok import config

class Extractor(object):
  def __init__(self, _fn = None, **kwargs):
    self._data = {}
    self._fn = _fn
    for k, v in kwargs.iteritems():
      assert '_' not in k
      assert isinstance(v, (Feature, Extractor))
      self._data[k] = v
  
  def extract(self, input):
    if self._fn:
      input = self._fn(input)
    return {k: v.extract(input) for k, v in self._data.iteritems()}

  def pre_apply(self, *fns):
    fn = lambda x: apply_chain(fns, x)
    if self._fn:
      fn = lambda input: self._fn(fn(input))
    return Extractor(_fn = fn, **self._data)
  
  def shape(self):
    return {k: v.shape for k, v in self._data.iteritems()}

class Feature(object):
  '''
  An Feature is a function that takes a domain specific object and outputs a property of
  that object as a fixed shape numpy array.

  The output value of this feature is always a numpy array.
  '''
  def __init__(self, **kwargs):
    if kwargs.get('extract'):
      self._extract = kwargs['extract']
      assert callable(self._extract)
    else:
      self._extract = None

    assert self._extract

    self.is_dynamic = kwargs.get('is_dynamic', False)

    self._shape = None
    self._dtype = None

  def extract(self, input):
    rv = self._extract(input)
    
    if not self.shape:
      self._shape = rv.shape
      self._dtype = rv.dtype
    else:
      assert self.shape == rv.shape
      assert self.dtype == rv.dtype
    return rv
  
  def _expand_dims(self, dim):
    def extract(input):
      return np.expand_dims(self.extract(input), dim)

    return Feature(extract = extract, is_dynamic = self.is_dynamic)

  def expand_dims(self, dim):
    assert dim >= 0
    return self._expand_dims(dim)
  
  def array(self):
    def extract(input):
      return np.asarray([self.extract(i) for i in input])
    return Feature(extract = extract, is_dynamic = True)

  @property
  def shape(self):
    return self._shape

  @property
  def dtype(self):
    return self._dtype

  def pre_apply(self, *fns):
    kwargs = {'is_dynamic': self.is_dynamic}
    kwargs['extract'] = lambda input: self._extract(apply_chain(fns, input))
    return Feature(**kwargs)

def make_feature(chain):
  def func(input):
    return box(apply_chain(chain, input))
  return Feature(extract = func)

def apply_chain(fns, arg):
  for fn in fns:
    arg = fn(arg)
  return arg

def concatenate(features, dim):
  assert len(features) > 0
  assert all(isinstance(f, Feature) for f in features)
  assert isinstance(dim, six.integer_types)
  assert dim >= 0, 'Cannot concat along feature dimension'

  def extract(input):
    if all(f.shape for f in features):
      shape = list(features[0].shape)
      shape[dim] = sum(f.shape[dim] for f in features)
      shape = tuple(shape)
      dtype = features[0].dtype

      rv = np.empty(shape, dtype)
      current = 0
      for f in features:
        index = [slice(None)] * len(shape)
        index[dim] = slice(current, current + f.shape[dim])
        index = tuple(index)
        rv[index] = f.extract(input)
        current = current + f.shape[dim]
      return rv
    return np.concatenate([f.extract(input) for f in features], dim)

  return Feature(
    extract = extract,
    is_dynamic = any(f.is_dynamic for f in features))

def box(s):
  if not isinstance(s, (list, tuple, np.ndarray)):
    s = (s,)
  arr = np.asarray(s)
  if not np.issubdtype(arr.dtype, np.integer):
    arr = arr.astype(config.nt())
  return arr

def shape(arg):
  if hasattr(arg, 'shape'):
    return arg.shape
  return {k: shape(v) for k, v in arg.iteritems()}