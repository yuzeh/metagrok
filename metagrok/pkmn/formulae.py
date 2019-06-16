import numpy as np

from metagrok import config

CONST_NONE = u'+none'
CONST_HIDDEN = u'+hidden'
CONST_UNKNOWN = u'+unknown'

EV = 510 / 6
IV = 15

def estimate_stats(base, level):
  level = config.nptype(level)
  rv = base.copy()
  for k, b in base.iteritems():
    val = np.floor((2 * b + IV + np.floor(EV / 4.)) * level / 100.)
    if k == 'hp':
      rv[k] = val + level + 10
    else:
      rv[k] = val + 5
  return rv

def mbst(base, level):
  rv =  np.floor((2 * base['hp']  + IV + np.floor(EV / 4.)) * level / 100. + 10.)
  rv += np.floor((2 * base['atk'] + IV + np.floor(EV / 4.)) * level / 100. + 5.) * level / 100.
  rv += np.floor((2 * base['def'] + IV + np.floor(EV / 4.)) * level / 100. + 5.)
  rv += np.floor((2 * base['spa'] + IV + np.floor(EV / 4.)) * level / 100. + 5.) * level / 100.
  rv += np.floor((2 * base['spd'] + IV + np.floor(EV / 4.)) * level / 100. + 5.)
  rv += np.floor((2 * base['spe'] + IV + np.floor(EV / 4.)) * level / 100. + 5.)
  return rv

def apply_boosts(stats, boosts):
  for k in stats:
    stats[k] *= stat_multiplier(boosts.get(k, 0))

def stat_multiplier(boost):
  num = den = 2.
  if boost > 0:
    num += boost
  else:
    den -= boost
  return num / den
