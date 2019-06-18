import collections
import itertools

from metagrok.utils import to_id

from metagrok.pkmn import actions

_ALL_ACTIONS = tuple(str(v) for v in actions.GEN7SINGLES)

def all_actions_singles():
  return _ALL_ACTIONS

def team_preview_actions_singles():
  rv = []
  for action in actions.GEN7SINGLES:
    if action.type == 'switch':
      slots = [int(action.slot)]
      for i in range(1, 7):
        if i not in slots:
          slots.append(i)
      rv.append('team ' + ','.join(str(i) for i in slots))
    else:
      rv.append(None)
  return rv

def make_permutation(ordering):
  return [ordering.index(v) for v in all_actions_singles()]

def parse_valid_actions(req, is_trapped = False):
  if 'forceSwitch' in req:
    num_actives = len(req['forceSwitch'])
  else:
    num_actives = len(req['active'])

  num_alive = len([poke for poke in req['side']['pokemon'] if poke.get('condition') != '0 fnt'])

  # assert num_actives == 1 or num_actives == 2
  assert num_actives == 1

  if num_actives == 1:
    candidates = all_actions_singles()
  else:
    #candidates = all_actions_doubles()
    pass

  mask = [{} for i in range(num_actives)]

  def rv():
    rv = []
    for c in candidates:
      vs = c.split(',')
      mvs = list(zip(mask, vs))
      all_valid = all(m.get(v) for m, v in mvs)
      no_double_switch = not any(
        k.startswith('switch') and v > 1
        for k, v in collections.Counter(vs).items())
      if all_valid and no_double_switch and c != 'pass,pass':
        rv.append(','.join(m.get(v) for m, v in mvs))
      else:
        rv.append(None)
    return rv

  if req.get('wait'):
    return rv()

  def get_switches():
    rv = {}
    for i, poke in enumerate(req['side']['pokemon']):
      if poke.get('active'):
        continue
      if poke.get('condition') == '0 fnt':
        continue

      rv['switch %d' % (i + 1)] = poke['ident']
    return rv

  if 'forceSwitch' not in req:
    for active_idx, active in enumerate(req['active']):
      mask_i = mask[active_idx]
      is_trapped = is_trapped or active.get('trapped')
      mega = active.get('canMegaEvo')
      ultra = active.get('canUltraBurst')

      for i, move in enumerate(active['moves']):
        if move.get('disabled'):
          continue
        if 'pp' in move and move['pp'] == 0:
          continue

        name = move['id']

        move_idx = i + 1
        mask_i['move %d' % move_idx] = name

        if mega:
          mask_i['move %d mega' % move_idx] = name + ' mega'

        if ultra:
          mask_i['move %d ultra' % move_idx] = name + ' ultra'

      if active.get('canZMove'):
        for i, move in enumerate(active['canZMove']):
          if move:
            name = move['move']
            mask_i['move %d zmove' % (i + 1)] = name

      if not is_trapped:
        mask_i.update(get_switches())
  else:
    for needs_switch, mask_i in zip(req['forceSwitch'], mask):
      if needs_switch:
        mask_i.update(get_switches())
        if num_actives > num_alive:
          mask_i['pass'] = 'pass'
      else:
        mask_i['pass'] = 'pass'

  return rv()

def parse_poke_id(poke):
  '''
  >>> parse_poke_id('p1: marcopopopo')
  ('p1', 'marcopopopo')
  >>> parse_poke_id('p2a: Tapu Bulu')
  ('p2', 'Tapu Bulu')
  '''
  pos, pname = poke.split(':')
  return pos.strip()[:2], pname.strip()

def parse_poke_details(spec):
  parts = [v.strip() for v in spec.split(',')]
  rv = dict(
      species = to_id(parts[0]),
      shiny = False,
      level = 100,
      gender = '*',
  )

  for part in parts[1:]:
    if part.startswith('L'):
      rv['level'] = int(part[1:])
    if part == 'shiny':
      rv['shiny'] = True
    if part in 'MF':
      rv['gender'] = part
  return rv

def parse_hp_status(hp):
  '''
  >>> parse_hp_status('100/100') == {'hp': 100, 'maxhp': 100, 'status': ''}
  True
  >>> parse_hp_status('75/350 psn') == {'hp': 75, 'maxhp': 350, 'status': 'psn'}
  True
  >>> parse_hp_status('0 fnt') == {'hp': 0, 'status': 'fnt'}
  True
  >>> parse_hp_status('brn')
  {'status': 'brn'}
  '''
  parts = hp.split()
  if len(parts) > 1:
    hp, status = parts
  else:
    if parts[0][0].isdigit():
      hp = parts[0]
      status = ''
    else:
      hp = None
      status = parts[0]

  if hp is None:
    return dict(status = status)
  elif hp == '0':
    return dict(hp = 0, status = status)

  hp, maxhp = [int(v) for v in hp.split('/')]
  return dict(hp = hp, maxhp = maxhp, status = status)
