# coding=utf8
from __future__ import unicode_literals

import collections
import calendar
import datetime
import errno
import functools
import fnmatch
import importlib
import logging
import os
import random
import re
import six
import sys
import time

import functools32

from metagrok.constants import ENCODING, LOG_FORMAT
from metagrok import fileio

def cache(maxsize = None):
  return functools32.lru_cache(maxsize = maxsize)

def const(values = None):
  def rv(fn):
    if values is None:
      value = fn()
      return functools.wraps(fn)(lambda: value)

    v2v = {v: fn(v) for v in values}
    return functools.wraps(fn)(lambda v: v2v[v])
  return rv

lazy = cache(1)

def to_id(val):
  return re.sub(r'[^a-z0-9+]+', '', val.lower())

def find(_root, leaf):
  for root, dirnames, filenames in os.walk(_root):
    for filename in fnmatch.filter(filenames, leaf):
      yield os.path.join(root, filename)

def linecount(fname):
  for i, l in enumerate(slurp_lines(fname)):
    pass
  return i + 1

def slurp_lines(fname):
  with fileio.open(fname) as fd:
    for line in fd:
      yield line.strip()

def utf8_input(prompt):
  line = six.moves.input(prompt)
  if ENCODING and ENCODING != 'utf-8' and not isinstance(line, six.text_type):
    line = line.decode(ENCODING).encode('utf-8')
  elif isinstance(line, six.text_type):
    line = line.encode('utf-8')
  return line

def random_name():
  ws = random.sample(words(), 10)
  name = ws[0]
  for w in ws[1:]:
    if len(name) + 1 + len(w) > 18:
      break
    name += ('-' + w)
  return name

def ts():
  return calendar.timegm(time.gmtime())

def iso_ts():
  return datetime.datetime.utcnow().isoformat().split('.')[0] + 'Z'

@lazy
def words():
  return list(set(word.strip().lower()
    for word in slurp_lines('static/words')
    if len(word) < 8 and len(word) > 3))

def mkdir_p(path):
  try:
    os.makedirs(path)
  except OSError as exc:  # Python >2.5
    if exc.errno == errno.EEXIST and os.path.isdir(path):
      pass
    else:
      raise

_px = re.compile(r"^\$(?:\[(?:\d+|\"(?:[^\"\u0000-\u001f]|\\([\"\/bfnrt]|u[0-9a-zA-Z]{4}))*\")\])*$")
def retrocycle(obj):
  'Retrocycles a deserialized python object returned by JSON.decycle (in JavaScript).'
  def rez(value):
    if isinstance(value, list):
      for i in range(len(value)):
        item = value[i]
        if isinstance(item, dict) and '$ref' in item:
          path = item['$ref']
          if isinstance(path, six.string_types) and _px.match(path):
            value[i] = _eval(path, obj)
          else:
            rez(item)
        elif isinstance(item, (dict, list)):
          rez(item)
    elif isinstance(value, dict):
      for name in value.keys():
        item = value[name]
        if isinstance(item, dict) and '$ref' in item:
          path = item['$ref']
          if isinstance(path, six.string_types) and _px.match(path):
            value[name] = _eval(path, obj)
          else:
            rez(item)
        elif isinstance(item, (dict, list)):
          rez(item)

  def _eval(expr, ctx):
    expr = '_' + expr[1:]
    return eval(expr, dict(__builtins__ = None, _ = ctx), {})

  rez(obj)

def walk(root, fn):
  '''Walks a complex dictionary object. Applies a function to each element in the tree.

  - obj: the object to walk.
  - fn(path, val, root) - return a non-None to replace the value and skip walking children
  '''

  path = collections.deque()

  def impl(obj, parent = None):
    rv = fn(path, obj, root)
    if rv is not None and parent is not None:
      parent[path[-1]] = rv
      return

    if isinstance(obj, list):
      for i in range(len(obj)):
        path.append(i)
        impl(obj[i], obj)
        path.pop()
    elif isinstance(obj, dict):
      for i in obj.keys():
        path.append(i)
        impl(obj[i], obj)
        path.pop()

  impl(root)

def project(obj, keys):
  return {k: obj[k] for k in keys if k in obj}

def hydrate(name):
  if not isinstance(name, six.string_types):
    return name
  mod_name, obj_name = name.rsplit('.', 1)
  mod = importlib.import_module(mod_name)
  return getattr(mod, obj_name)

def clone_args(args):
  return Ns(**vars(args))

class Ns(object):
  def __init__(self, **kwargs):
    for k, v in kwargs.iteritems():
      setattr(self, k, v)

def flatten_dict(d, sep = '_'):
  rv = {}
  for k, v in d.iteritems():
    if isinstance(v, dict):
      v = flatten_dict(v, sep)
      for vk, vv in v.iteritems():
        rv[k + sep + vk] = vv
    else:
      rv[k] = v
  return rv

def unflatten_dict(d, sep = '_'):
  rv = {}
  for k, v in d.iteritems():
    parts = k.split(sep)
    cur = rv
    for part in parts[:-1]:
      if part not in cur:
        cur[part] = {}
      cur = cur[part]
    cur[parts[-1]] = v
  return rv

def update_recursive(d, u):
  for k, v in u.iteritems():
    if isinstance(v, collections.Mapping):
      d[k] = update_recursive(d.get(k, {}), v)
    else:
      d[k] = v
  return d

def default_logger_setup(level = logging.INFO):
  logger = logging.getLogger()
  logger.setLevel(0)

  shandler = logging.StreamHandler()
  shandler.setFormatter(logging.Formatter(LOG_FORMAT))
  shandler.setLevel(level)
  logger.addHandler(shandler)
  return logger

def debugger():
  import pdb
  pdb.set_trace()

def memory_dump(fname):
  import gc
  import cPickle

  with open(fname, 'w') as dump:
    for obj in gc.get_objects():
      i = id(obj)
      size = sys.getsizeof(obj, 0)
      #    referrers = [id(o) for o in gc.get_referrers(obj) if hasattr(o, '__class__')]
      referents = [id(o) for o in gc.get_referents(obj) if hasattr(o, '__class__')]
      if hasattr(obj, '__class__'):
        cls = str(obj.__class__)
        cPickle.dump({'id': i, 'class': cls, 'size': size, 'referents': referents}, dump)

def touch(path):
  with open(path, 'a'):
    os.utime(path, None)