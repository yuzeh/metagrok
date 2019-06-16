'''
A set of baselines that follow the EnginePkmnPlayer interface but are not TorchPolicy subclasses.
'''

import random

import numpy as np

from metagrok import config
from metagrok import np_json as json
from metagrok import utils

from metagrok.pkmn import actions
from metagrok.pkmn.engine import navigation as nav

def create_type_chart():
  rv = {}
  for defender_type, type_data in json.load('dex/BattleTypeChart.json').iteritems():
    defender_type = utils.to_id(defender_type)
    attacker_data = {}
    for attacker_type, modifier in type_data['damageTaken'].iteritems():
      attacker_type = utils.to_id(attacker_type)
      if modifier == 0:
        multiplier = 1.
      elif modifier == 1:
        multiplier = 2.
      elif modifier == 2:
        multiplier = 0.5
      elif modifier == 3:
        multiplier = 0.
      else:
        raise ValueError('Unknown modifier %s' % modifier)
      attacker_data[attacker_type] = multiplier

    rv[defender_type] = attacker_data
  return rv

Movedex = json.load('dex/BattleMovedex.json')
TypeChart = create_type_chart()

class RandomPlayer(object):
  def act(self, state, candidates):
    probs = np.asarray([1. if c else 0. for c in candidates])
    probs = probs / probs.sum()
    return dict(probs = probs)

class MostDamageMovePlayer(object):
  '''
  Ranks actions in the following order:
  - damaging moves (sort by power, then move modifier)
    - zmove
    - ultra
    - mega
    - (no modifier)

  - non-damaging moves (ordered by move modifier)
    - zmove
    - ultra
    - mega
    - (no modifier)

  - switches (randomly ordered)

  Goes through the ranked list and pickes the first one that is a valid move.
  '''

  def __init__(self, **kwargs):
    self._type_aware = kwargs.get('type_aware', False)

  def act(self, state, candidates):
    move_candidates = []
    switch_candidates = []

    me = nav.get_player_side(state)
    opp = nav.get_opponent_side(state)

    active = nav.get_active_pokes(me)
    active = active and active[0]
    moves = active and [v[0] for v in active['moveTrack']]

    opp_active = nav.get_active_pokes(opp)
    opp_active = opp_active and opp_active[0]

    if not self._type_aware:
      opp_active = None

    for i, action in enumerate(actions.GEN7SINGLES):
      if candidates[i]:
        if action.type == 'move':
          move_key = moves[action.slot - 1]
          power = compute_power(move_key, opp_active)
          move_candidates.append((power, action, i))
        else:  # action.type == 'switch'
          poke = me['pokemon'][action.slot - 1]
          weakness = 0.
          if opp_active:
            for opp_type in opp_active['types']:
              weakness += compute_multiplier(opp_type, poke['types'])
          switch_candidates.append((weakness, action, i))
    
    selected = None
    if move_candidates:
      random.shuffle(move_candidates)
      move_candidates.sort(key = self._move_sort_key, reverse = True)
      selected = move_candidates[0][-1]
    else:
      random.shuffle(switch_candidates)
      switch_candidates.sort(key = self._switch_sort_key)
      selected = switch_candidates[0][-1]
    
    rv = np.zeros(len(candidates), dtype = config.nt())
    rv[selected] = 1.
    return dict(probs = rv)
  
  def _move_sort_key(self, arg):
    power, action, _ = arg
    modifier = {
      'zmove': 3,
      'ultra': 2,
      'mega': 1,
    }.get(action.modifier, 0)
    return (power, modifier)
  
  def _switch_sort_key(self, arg):
    return arg[0]

def compute_power(move_key, opponent = None):
  movedex_entry = Movedex.get(move_key)
  if not movedex_entry:
    return 0.

  move_type = movedex_entry.get('type') or ''
  power = movedex_entry.get('basePower', 0.)
  if movedex_entry.get('ohko'):
    power = 120.
  
  multiplier = 1.
  if move_type and opponent:
    multiplier = compute_multiplier(move_type, opponent['types'])
  
  return power * multiplier

def compute_multiplier(attacker_type, defender_types):
  attacker_type = utils.to_id(attacker_type)

  rv = 1.
  for def_type in defender_types:
    rv *= TypeChart[utils.to_id(def_type)][attacker_type]
  return rv

def MostDamageMovePlayerTypeAware(): return MostDamageMovePlayer(type_aware = True)