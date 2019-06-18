import collections
import logging
import six

from metagrok import config
from metagrok import fileio
from metagrok.utils import retrocycle, walk, to_id, const

from metagrok.pkmn.parser import parse_hp_status, parse_poke_details

from metagrok.pkmn import formulae as F
from metagrok.pkmn.dex import DEX

from py_mini_racer import py_mini_racer

logger = logging.getLogger(__name__)

@const()
def script():
  return fileio.read('{}/engine.js'.format(config.get('metagrok_client_root')))

def mk_ctx():
  rv = py_mini_racer.MiniRacer()
  rv.eval(script())
  return rv

def postprocess(state, req):
  _postprocess_engine_state(state)
  if req:
    _update_with_request(state, req)
    _remove_illusions(state)

class Engine(object):
  def __init__(self, id = None):
    self.id = id
    self._ctx = mk_ctx()

  def start(self, gid):
    logger.debug('engine.start(%s)', gid)
    return self._ctx.call('engine.start', gid)

  def fetch(self, gid, req = None):
    state = self._fetch(gid)
    postprocess(state, req)
    if logger.isEnabledFor(3):
      logger.log(3, 'fetch(%s) = %s', gid, state)
    return state

  def stop(self, gid):
    logger.debug('engine.stop(%s)', gid)
    return self._ctx.call('engine.stop', gid)

  def update(self, gid, changes):
    logger.debug('engine.transition(%s, %s)', gid, changes)
    return self._ctx.call('engine.transition', gid, changes)

  def _fetch(self, gid):
    logger.debug('engine.fetch(%s)', gid)
    return self._ctx.call('engine.fetch', gid)

def _postprocess_engine_state(state):
  retrocycle(state)
  _strip_cycles(state)
  _process(state)

def _remove_illusions(state):
  if not state.get('speciesClause'):
    return
  
  side = _get_opponent(state, state['whoami'])
  new_pokes = []
  seen_species = set()
  for poke in side['pokemon']:
    if poke['baseSpecies'] in seen_species:
      continue
    new_pokes.append(poke)
    seen_species.add(poke['baseSpecies'])
  side['pokemon'] = new_pokes

def _update_with_request(state, req):
  side_name = req['side']['name']
  state['whoami'] = side_name
  state_side = _get_side(state, side_name)
  new_state_pokes = []
  actives = []

  for rp in req['side']['pokemon']:
    if 'ability' not in rp:
      rp['ability'] = rp['baseAbility']
    moves = rp['moves']
    cond = parse_hp_status(rp['condition'])

    matching_state_pokes = [sp for sp in state_side['pokemon'] if _is_same_poke(sp, rp)]
    if matching_state_pokes:
      # In the case of illusion, the latter pokemon is not the zoroark
      sp = matching_state_pokes[-1]
    else:
      sp = dict(rp)
      sp.update(parse_poke_details(sp['details']))
      sp.update(DEX.info('BattlePokedex', sp['species']))
      sp['moveTrack'] = []
      sp['boosts'] = {}

      # fainted zoroark
      if 'maxhp' not in sp:
        sp['maxhp'] = F.estimate_stats(sp['baseStats'], sp['level'])['hp']

    if cond['status'] == 'fnt':
      cond['status'] = F.CONST_NONE
      sp['fainted'] = True
    else:
      sp['fainted'] = False
    sp.update(cond)
    sp.update(rp)

    sp['active'] = rp.get('active', False)

    del sp['moves']
    del sp['condition']

    if rp.get('active'):
      actives.append(sp)

    movesdict = dict(sp['moveTrack'])
    sp['moveTrack'] = [[m, movesdict.get(m, 0)] for m in moves]

    new_state_pokes.append(sp)
  state_side['pokemon'] = new_state_pokes

  if req.get('active'):
    for active_spec, active in zip(req['active'], actives):
      active['moveTrack'] = _reorder_movetrack(active['moveTrack'], active_spec['moves'])

def _get_side(state, name):
  for side in state['sides']:
    if side['name'] == name:
      return side
  raise ValueError('Could not find side with name: ' + name)

def _get_opponent(state, name):
  for side in state['sides']:
    if side['name'] != name:
      return side
  raise ValueError('Could not find side without name: ' + name)

def _strip_cycles(rv):
  if isinstance(rv, list):
    for el in rv:
      _strip_cycles(el)
  elif isinstance(rv, dict):
    for key in list(rv.keys()):
      if key in {'side', 'battle', 'p1', 'p2', 'foe', 'mySide', 'yourSide'}:
        del rv[key]
      else:
        _strip_cycles(rv[key])

def _process(rv):
  '''
  - Replace any poke references with ident where they are not in the array.
  - Replace blank statuses and blank weather with CONST_NONE.
  - Normalize types, species, items, abilities
  '''
  def fn(path, val, root):
    if val is root:
      val['weather'] = to_id(val['weather'] or F.CONST_NONE)
    if len(path) == 2 and 'sides' == path[0]:
      # mark the first pokemon as that has the ident in active as active
      actives = set([_f for _f in [_to_ident(p) for p in val['active']] if _f])
      for p in val['pokemon']:
        if p['ident'] in actives:
          actives.remove(p['ident'])
          p['active'] = True
        else:
          p['active'] = False
    if isinstance(val, dict) and 'ident' in val:
      if not (len(path) == 4 and path[0] == 'sides' and path[2] == 'pokemon'):
        return val['ident']
      else:
        # TODO: only update hp estimate if this is an opponent pokemon.
        # This works because the hp data comes back for the player with the request object
        stats = F.estimate_stats(val['baseStats'], val['level'])
        hp_pct = float(val['hp']) / val['maxhp']
        val['maxhp'] = stats['hp']
        val['hp'] = stats['hp'] * hp_pct
        del stats['hp']
        val['stats'] = stats
        val['moveTrack'] = [(to_id(m), p) for m, p in val['moveTrack']]
        val['status'] = to_id(val['status'] or F.CONST_NONE)

        for key in ['ability', 'baseAbility', 'item', 'prevItem', 'species', 'baseSpecies']:
          val[key] = to_id(val[key] or F.CONST_HIDDEN)
        val['types'] = [to_id(t) for t in val['types']]
        val['abilities'] = {k: to_id(v) for k, v in val['abilities'].items()}

  walk(rv, fn)

def _reorder_movetrack(move_track, moves):
  rv = []
  idx = []
  for move in moves:
    moveid = move['id']
    for i, (m, p) in enumerate(move_track):
      if m == moveid:
        rv.append((m, p))
        idx.append(i)
        break
  for i, (m, p) in enumerate(move_track):
    if i not in idx:
      rv.append((m, p))
  return rv

def _to_ident(p):
  if isinstance(p, dict):
    return p.get('ident')
  elif isinstance(p, six.string_types):
    return p
  return None

def _is_same_poke(a, b):
  a = _to_ident(a)
  b = _to_ident(b)

  if not a or not b:
    return False

  return a == b