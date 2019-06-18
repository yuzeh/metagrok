import contextlib
import gzip
import os
import tempfile

import numpy as np
import zipfile

def npz_headers(npz):
  """Takes a path to an .npz file, which is a Zip archive of .npy files.
  Generates a sequence of (name, shape, np.dtype).
  """
  with zipfile.ZipFile(npz) as archive:
    for name in archive.namelist():
      if not name.endswith('.npy'):
        continue

      npy = archive.open(name)
      version = np.lib.format.read_magic(npy)
      shape, fortran, dtype = np.lib.format._read_array_header(npy, version)
      yield name[:-4], shape, dtype

def npy_headers(npy):
  with open(npy) as fd:
    version = np.lib.format.read_magic(fd)
    shape, fortran, dtype = np.lib.format._read_array_header(fd, version)
    return shape, dtype

_builtin_open = open

@contextlib.contextmanager
def open(fname, mode = 'r'):
  if fname.endswith('.gz'):
    opener = gzip.GzipFile
  else:
    opener = _builtin_open

  with opener(fname, mode) as fd:
    yield fd

@contextlib.contextmanager
def to_fd(arg, mode = 'r'):
  if hasattr(arg, 'read'):
    yield arg
  else:
    with open(arg, mode = mode) as fd:
      yield fd

def read(arg):
  with to_fd(arg) as fd:
    return fd.read()

@contextlib.contextmanager
def gz(fd, mode = 'r'):
  with gzip.GzipFile(mode = mode, fileobj = fd) as gzfd:
    yield gzfd

def memmap(name2array, root_dir = None):
  dirname = tempfile.mkdtemp(dir = root_dir)
  for k, v in name2array.items():
    fname = os.path.join(dirname, k)
    np.save(fname, v)
  rv = {k: os.path.join(dirname, k + '.npy') for k in name2array}
  return dirname, rv
