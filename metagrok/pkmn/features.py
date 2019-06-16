import json
import logging
import os
import re

import numpy as np
import pandas as pd

from metagrok import config
from metagrok.utils import to_id, const

import metagrok.pkmn.formulae as F

_key_to_extras = dict(
    BattleStatuses = [F.CONST_NONE, F.CONST_UNKNOWN],
    BattlePokedex = [F.CONST_HIDDEN, F.CONST_UNKNOWN],
    BattleMovedex = [F.CONST_HIDDEN, F.CONST_UNKNOWN],
    BattleTypeChart = [F.CONST_HIDDEN, F.CONST_UNKNOWN],
    BattleAbilities = [F.CONST_HIDDEN, F.CONST_UNKNOWN],
    BattleItems = [F.CONST_HIDDEN, F.CONST_UNKNOWN],
    BattleVolatiles = [F.CONST_NONE, F.CONST_UNKNOWN],
    BattleSideConditions = [F.CONST_NONE, F.CONST_UNKNOWN],
    BattleSideConditionsNew = [F.CONST_NONE, F.CONST_UNKNOWN],
    BattleWeathers = [F.CONST_NONE, F.CONST_UNKNOWN],
)

_dex_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'dex')
_battle_names = _key_to_extras.keys()

logger = logging.getLogger(__name__)

@const(_battle_names)
def data(key):
  name = key

  with open(os.path.join(_dex_dir, name + '.json')) as fd:
    rv = json.load(fd)

  if key == 'BattleStatuses':
    rv = {k: v for k, v in rv.iteritems() if v.get('effectType') == 'Status'}

  return rv

@const(_battle_names)
def embeddings(key):
  fname = os.path.join(_dex_dir, key + '.embedding.npy')
  if os.path.isfile(fname):
    return np.load(fname)
  return None

def info(key, id):
  return data(key)[id]

HP_REGEX = re.compile(r'hiddenpower([^\d]+)(\d+)')
_moves = data('BattleMovedex').keys()
_hps = [m for m in _moves if m.startswith('hiddenpower') and m != 'hiddenpower']

@const(_moves + [m + '60' for m in _hps])
def moveinfo(id):
  d = data('BattleMovedex')
  if id in d:
    return d[id]

  if id.startswith('hiddenpower'):
    rv = dict(d['hiddenpower'])
    match = HP_REGEX.match(id)
    rv['basePower'] = float(match.group(2))
    rv['type'] = match.group(1)
    return rv

  raise ValueError('unknown move id: ' + id)

class CategoricalFeature(object):
  def __init__(self, feature_key):
    keys = data(feature_key).keys()
    keys.extend(_key_to_extras[feature_key])
    keys = list(set(keys))
    keys.sort()

    self.names = keys
    self.feature_key = feature_key
    self.name_to_index = {to_id(k): i for i, k in enumerate(keys)}
    self.embedding = embeddings(feature_key)

  def __call__(self, names):
    return self.nidx(names)

  @property
  def size(self):
    return len(self.name_to_index)

  def to_index(self, name):
    if not name:
      return 0

    name = to_id(name)
    if name.startswith('hiddenpower'):
      match = HP_REGEX.match(name)
      if match:
        name = 'hiddenpower' + match.group(1)
    if name not in self.name_to_index:
      logger.warn('Could not find %s in %s', name, self.feature_key)
      return 1
    return self.name_to_index[name]

  def nidx(self, names):
    if not isinstance(names, (list, tuple)):
      names = (names,)
    return [self.to_index(n) for n in names]

  def nhot(self, names):
    if not isinstance(names, (list, tuple)):
      names = (names,)
    rv = np.zeros(self.size, dtype = config.nt())
    for name in names:
      rv[self.to_index(name)] = 1
    return rv

  def nembed(self, idxes):
    if self.embedding is not None:
      return np.stack([self.embedding[idx] for idx in idxes])
    raise ValueError('Cannot call nembed on Categorical without embedding')

@const(_battle_names)
def spec(key):
  return CategoricalFeature(key)

# See: https://github.com/Zarel/Pokemon-Showdown/blob/193e948592ec281f3465d4685e68edbcb7999171/data/random-teams.js#L163
def gen7rb_level(base):
  mbst = F.mbst(base, 100.)
  mbstmin = np.min(mbst)
  level = np.floor(100 * mbstmin / mbst)
  mbst = F.mbst(base, level)
  while True:
    mbst = F.mbst(base, level)
    done = np.dtype(bool).type((mbst >= mbstmin) | (level >= 100))
    if np.all(done):
      break
    level += np.dtype(config.nt()).type(~done)

  return level

@const()
def gen7_base_stats():
  df = pd.read_csv(os.path.join(_dex_dir, 'base-stats.tsv'), sep = '\t')
  del df['Pokemon']
  return df.astype(config.nt())

@const()
def gen7rb_stats():
  df = gen7_base_stats()
  level = gen7rb_level(df)
  return F.estimate_stats(df, level)

if __name__ == '__main__':
  stats = gen7rb_stats()
  print stats.describe()
