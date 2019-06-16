import os
import shutil
import tempfile

import numpy as np
import numpy.random as npr
import torch

from torch.utils.data.dataset import Dataset

class TTensorDictDataset(Dataset):
  def __init__(self, tensors, in_place_shuffle = True):
    super(TTensorDictDataset, self).__init__()
    self.in_place_shuffle = in_place_shuffle

    self._tensors = tensors
    self._size = next(tensors.itervalues()).shape[0]

  def __getitem__(self, index):
    return {k: self._tensors[k][index] for k in self._tensors}

  def __len__(self):
    return self._size

  def shuffle_(self):
    perm = torch.randperm(len(self))
    for k in self._tensors:
      self._tensors[k] = self._tensors[k][perm]

class NDArrayDictDataset(TTensorDictDataset):
  def __init__(self, ndarrays, in_place_shuffle = True):
    super(NDArrayDictDataset, self).__init__(
        {k: torch.from_numpy(v) for k, v in ndarrays.iteritems()}, in_place_shuffle)
    self._ndarrays = ndarrays

  def shuffle_(self):
    perm = npr.permutation(len(self))
    for v in self._ndarrays.itervalues():
      np.take(v, perm, axis = 0, out = v)

class MemmapDictDataset(Dataset):
  def __init__(self, npzfile):
    self.dirname = tempfile.mkdtemp()
    self._name2memmap = {
        k: self._load_mmap(k, v)
        for k, v in npzfile.iteritems()
    }
    self._size = next(self._name2memmap.itervalues()).shape[0]

  def __getitem__(self, index):
    rv = {}
    for k, v in self._name2memmap.iteritems():
      rv[k] = v[index]
    return rv

  def _load_mmap(self, name, np_array):
    fname = os.path.join(self.dirname, '%s.npy' % name)
    mmap_ndarray = np.memmap(fname, dtype = np_array.dtype, shape = np_array.shape, mode = 'w+')
    mmap_ndarray = np_array

    return torch.from_numpy(mmap_ndarray)

  def __len__(self):
    return self._size

  def __del__(self):
    del self._name2memmap
    shutil.rmtree(self.dirname)

