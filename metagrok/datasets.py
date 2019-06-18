import bisect
import logging

import tqdm
import numpy as np

from torch.utils.data.dataset import Dataset

from metagrok import config
from metagrok import jsons
from metagrok import np_json as json
from metagrok import utils

logger = logging.getLogger(__name__)

class ExampleDataset(Dataset):
  def __init__(self, policy, transform = None):
    self.policy = policy
    self.transform = transform

  def _get(self, index):
    raise NotImplementedError

  def _convert(self, item):
    if self.transform:
      item = self.transform(item)

    fs = self.policy.extract(item['state'], item['candidates'])
    rv = {
        'actions': np.asarray([item['action']], dtype = config.nt()),
        'advantages': np.asarray([item['advantage']], dtype = config.nt()),
        'value_preds': np.asarray([item['value_pred']], dtype = config.nt()),
        'returns': np.asarray([item['return']], dtype = config.nt()),
    }

    for k in ['probs', 'log_probs']:
      if k in item:
        rv[k] = item[k]

    for k, v in fs.items():
      rv['features_' + k] = v

    return rv

  def __getitem__(self, idx):
    item = self._get(idx)
    return self._convert(item)

class InMemoryStringExampleJsonsDataset(ExampleDataset):
  def __init__(self, examples, policy, transform = None):
    super(InMemoryStringExampleJsonsDataset, self).__init__(policy, transform)
    self.examples = examples

  def __len__(self):
    return len(self.examples)

  def _get(self, index):
    return json.loads(self.examples[index])

class ExampleJsonsDataset(Dataset):
  def __init__(self, fnames, policy, in_memory = False, transform = None):
    """
    Args:
        fnames (string): list of all the file names
        policy (TorchPolicy): transforms the data.
        transform (callable, optional): Optional transform to be applied on a sample.
    """
    self.policy = policy
    self.transform = transform

    current = 0
    self.fnames = fnames

    self.examples = []
    self.file_offsets = []
    for i, fname in enumerate(tqdm.tqdm(self.fnames)):
      if in_memory:
        with open(fname) as fd:
          self.examples.extend(fd)
      else:
        self.file_offsets.append((current, i))
        current += utils.linecount(fname)

    if in_memory:
      self.total = len(self.examples)
    else:
      self.total = current

  def __len__(self):
    return self.total

  def __getitem__(self, idx):
    if self.examples:
      item = json.loads(self.examples[idx])
    else:
      result = bisect.bisect_left(self.file_offsets, (idx, len(self.fnames))) - 1
      offset, fnames_idx = self.file_offsets[result]
      fname = self.fnames[fnames_idx]
      to_go = idx - offset
      for i, item in enumerate(jsons.stream(fname)):
        if i == to_go:
          break
      else:
        raise ValueError('offset too high: %s, %s, %s' % (idx, offset, fname))

    if self.transform:
      item = self.transform(item)

    fs = self.policy.extract(item['state'], item['candidates'])
    rv = {
        'actions': np.asarray([item['action']], dtype = config.nt()),
        'advantages': np.asarray([item['advantage']], dtype = config.nt()),
        'value_preds': np.asarray([item['value_pred']], dtype = config.nt()),
        'returns': np.asarray([item['return']], dtype = config.nt()),
    }

    for k in ['probs', 'log_probs']:
      if k in item:
        rv[k] = item[k]

    for k, v in fs.items():
      rv['features_' + k] = v

    return rv
