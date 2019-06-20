from functools import lru_cache
import glob
import logging
import os
import re

import numpy as np
import pandas as pd

from metagrok import config
from metagrok import np_json as json
from metagrok.utils import to_id

import metagrok.pkmn.formulae as F

logger = logging.getLogger(__name__)

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

HP_REGEX = re.compile(r'hiddenpower([^\d]+)(\d+)')
RETURN_REGEX = re.compile(r'return(\d+)')

_cache_miss = object()

class Dex(object):
  @classmethod
  def create(cls, dirname):
    return cls(glob.glob('{}/*'.format(dirname)), dirname)

  def __init__(self, filenames, dirname):
    self._filenames = filenames
    self._dirname = dirname

    self._json_base_to_full_path = {}
    self._json_cache = {}

    for fname in filenames:
      base = os.path.basename(fname)
      base, ext = os.path.splitext(base)
      if ext == '.json':
        self._json_base_to_full_path[base] = fname
        self._json_cache[base] = _cache_miss
    
    self.data = lru_cache(maxsize = None)(self.data)
    self.spec = lru_cache(maxsize = None)(self.spec)
    self.gen7rb_stats = lru_cache(maxsize = None)(self.gen7rb_stats)
  
  def data(self, key):
    full_path = self._json_base_to_full_path[key]
    rv = json.load(full_path)

    if key == 'BattleStatuses':
      rv = {k: v for k, v in rv.items() if v.get('effectType') == 'Status'}
    
    return rv
  
  def gen7rb_stats(self):
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

    def gen7_base_stats():
      df = pd.read_csv(os.path.join(self._dirname, 'base-stats.tsv'), sep = '\t')
      del df['Pokemon']
      return df.astype(config.nt())

    df = gen7_base_stats()
    level = gen7rb_level(df)
    return F.estimate_stats(df, level)

  def spec(self, key):
    return CategoricalFeature(key, self.data(key))
  
  def info(self, key, id):
    return self.data(key)[id]


class CategoricalFeature(object):
  def __init__(self, feature_key, dt):
    keys = list(dt.keys())
    keys.extend(_key_to_extras[feature_key])
    keys = list(set(keys))
    keys.sort()

    self.names = keys
    self.feature_key = feature_key
    self.name_to_index = {to_id(k): i for i, k in enumerate(keys)}

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
    elif name.startswith('return') and RETURN_REGEX.match(name):
      name = 'return'

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

DEX = Dex.create(config.get('dex_root'))

if __name__ == '__main__':
  print(DEX.gen7rb_stats().describe())