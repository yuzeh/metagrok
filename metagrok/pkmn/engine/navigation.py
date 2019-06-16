'''
Utilities for navigating the state object returned by the engine.

This module should be format agnostic (i.e. not have code specific to singles)
'''

def extract_players(state):
  sides = state['sides']
  assert len(sides) == 2, sides

  me = state['whoami']
  if sides[0]['name'] == me:
    return sides[0], sides[1]

  assert sides[1]['name'] == me, 'Did not find %s in %s' % (me, [s['name'] for s in sides])
  return sides[1], sides[0]

def get_player_side(state):
  return extract_players(state)[0]

def get_opponent_side(state):
  return extract_players(state)[1]

def get_active_pokes(side):
  return [p for p in side['pokemon'] if p.get('active')]