import collections
import six

import numpy as np

import torch
import torch.autograd as ag
import torch.nn as nn
import torch.nn.functional as F

from metagrok import utils, config
from metagrok.torch_policy import TorchPolicy
from metagrok.torch_utils import masked_softmax, zeros

from metagrok.pkmn import parser
from metagrok.pkmn.engine.navigation import extract_players
from metagrok.pkmn.features import spec, gen7rb_stats
from metagrok.pkmn.formulae import CONST_HIDDEN, CONST_NONE

EMBED_SIZE = object()

class Policy(TorchPolicy):
  '''
  This class is designed to be backwards compatible with previous versions of itself, so PLEASE
  do not change the names of the variables.
  '''
  def __init__(self, **kwargs):
    super(Policy, self).__init__(**kwargs)
    self.pkmn_size      = kwargs.get('pkmn_size', 256)
    self.move_size      = kwargs.get('embed_size', 128)
    self.depth          = kwargs.get('depth', 1)
    self.embed_depth    = kwargs.get('embed_depth', self.depth)

    self.poke_features  = kwargs.get('poke_features', _default_poke_features)

    total_poke_size = 0
    for f in self.poke_features:
      if isinstance(f.size, (int, long)):
        assert f.size > 0
        total_poke_size += f.size
      elif f.size is EMBED_SIZE:
        total_poke_size += self.move_size
      else:
        raise ValueError('Invalid feature size: %s' % f.size)

    self.shared_size = (
      2 * (self.pkmn_size + SideConditions.size)
      + Weathers.size
      + 2
      + 2 * self.pkmn_size)
    self.decision_size = self.shared_size + self.pkmn_size + self.move_size

    self.species    = nn.Embedding(Species.size,    self.move_size, padding_idx = 0, max_norm = 1.)
    self.abilities  = nn.Embedding(Abilities.size,  self.move_size, padding_idx = 0, max_norm = 1.)
    self.items      = nn.Embedding(Items.size,      self.move_size, padding_idx = 0, max_norm = 1.)
    self.moves      = nn.Embedding(Moves.size,      self.move_size, padding_idx = 0, max_norm = 1.)

    self.species_more = nn.ModuleList([
      nn.Linear(self.move_size, self.move_size) for _ in range(self.embed_depth - 1)])
    self.abilities_more = nn.ModuleList([
      nn.Linear(self.move_size, self.move_size) for _ in range(self.embed_depth - 1)])
    self.items_more = nn.ModuleList([
      nn.Linear(self.move_size, self.move_size) for _ in range(self.embed_depth - 1)])
    self.moves_more = nn.ModuleList([
      nn.Linear(self.move_size, self.move_size) for _ in range(self.embed_depth - 1)])

    self.pkmn_affine = nn.Linear(total_poke_size, self.pkmn_size)
    self.group_affine = nn.Linear(self.pkmn_size, self.pkmn_size)

    self.pkmn_affine_more = nn.ModuleList([
      nn.Linear(self.pkmn_size, self.pkmn_size) for _ in range(self.depth - 1)])
    self.group_affine_more = nn.ModuleList([
      nn.Linear(self.pkmn_size, self.pkmn_size) for _ in range(self.depth - 1)])

    # decision layer = shared_size + pkmn_size + move_size
    self.policy_fc1 = nn.Linear(self.decision_size, self.pkmn_size)

    # 2018-02-12: Add variables for megaEvo and zMove
    self.policy_mega  = nn.Linear(1, self.pkmn_size, bias = False)
    self.policy_zmove = nn.Linear(1, self.pkmn_size, bias = False)
    self.policy_ultra = nn.Linear(1, self.pkmn_size, bias = False)

    self.policy_fc2 = nn.Linear(self.pkmn_size, 1)

    self.value_fc1 = nn.Linear(self.shared_size, self.pkmn_size)
    self.value_fc2 = nn.Linear(self.pkmn_size, 1)

  def extract(self, state, candidates):
    rv = extract(state, self.poke_features)
    candidates = list(candidates)

    while len(candidates) < len(parser.all_actions_singles()):
      candidates.append(None)

    rv['mask'] = np.asarray([float(bool(c)) for c in candidates]).astype(config.nt())

    return rv

  def forward_common(self, s):
    player, pkmn, moves = self._forward_side(s['player'])
    opponent, _, _ = self._forward_side(s['opponent'])

    xs = (player, opponent, s['weather'], s['weatherMinTimeLeft'], s['weatherTimeLeft'])
    xs = torch.cat(xs, 1)
    return xs, (pkmn, moves)

  def forward_value(self, xs):
    v = xs
    v = F.relu(self.value_fc1(v))
    v = self.value_fc2(v)
    return v

  def forward_policy(self, xs, extras, mask):
    N = mask.size()[0]
    cuda = mask.is_cuda

    pkmn, moves = extras

    zero4 = ag.Variable(zeros(N, 4, self.pkmn_size, cuda = cuda))
    zero6 = ag.Variable(zeros(N, 6, self.move_size, cuda = cuda))

    moves =    [moves, zero6, moves,         moves,         moves]
    switches = [zero4, pkmn,  zero4.clone(), zero4.clone(), zero4.clone()]

    moves = torch.cat(moves, 1)
    switches = torch.cat(switches, 1)

    # (batch_size, num_actions, num_features)
    p = torch.cat([xs.unsqueeze(1).expand(-1, moves.shape[1], -1), moves, switches], -1)
    p = F.relu(self.policy_fc1(p) + self._action_extra(N))
    p = self.policy_fc2(p).squeeze(-1)

    ps, lps = masked_softmax.apply(p, mask)
    return ps, lps

  def _action_extra(self, n):
    actions = parser.all_actions_singles()
    mega_mask = ag.Variable(
        torch.ByteTensor([a.endswith(' mega') for a in actions])
        .type(config.tt())
        .unsqueeze(0).unsqueeze(-1))

    zmove_mask = ag.Variable(
        torch.ByteTensor([a.endswith(' zmove') for a in actions])
        .type(config.tt())
        .unsqueeze(0).unsqueeze(-1))

    ultra_mask = ag.Variable(
        torch.ByteTensor([a.endswith(' ultra') for a in actions])
        .type(config.tt())
        .unsqueeze(0).unsqueeze(-1))

    return (self.policy_mega(mega_mask.expand(n, -1, -1))
        + self.policy_zmove(zmove_mask.expand(n, -1, -1))
        + self.policy_ultra(ultra_mask.expand(n, -1, -1)))

  def forward(self, **kwargs):
    kwargs = dict(kwargs)
    mask = kwargs['mask']

    del kwargs['mask']
    s = utils.unflatten_dict(kwargs)

    xs, extras = self.forward_common(s)
    v = self.forward_value(xs)
    ps, lps = self.forward_policy(xs, extras, mask)

    return v, ps, lps

  def _forward_pkmn(self, pkmn):
    out = dict(pkmn)

    # Abilities
    out['abilities']    = self.abilities(out['abilities'])
    out['ability']      = self.abilities(out['ability'])
    out['baseAbility']  = self.abilities(out['baseAbility'])

    for layer in self.abilities_more:
      out['abilities']    = layer(F.relu(out['abilities']))
      out['ability']      = layer(F.relu(out['ability']))
      out['baseAbility']  = layer(F.relu(out['baseAbility']))

    out['abilities']    = out['abilities'].mean(-2)
    out['ability']      = out['ability'].squeeze(-2)
    out['baseAbility']  = out['baseAbility'].squeeze(-2)

    # Species
    out['species']      = self.species(out['species'])
    out['baseSpecies']  = self.species(out['baseSpecies'])

    for layer in self.species_more:
      out['species']      = layer(F.relu(out['species']))
      out['baseSpecies']  = layer(F.relu(out['baseSpecies']))

    out['species']      = out['species'].squeeze(-2)
    out['baseSpecies']  = out['baseSpecies'].squeeze(-2)

    # Items
    out['item']         = self.items(out['item'])
    out['prevItem']     = self.items(out['prevItem'])

    for layer in self.items_more:
      out['item']         = layer(F.relu(out['item']))
      out['prevItem']     = layer(F.relu(out['prevItem']))

    out['item']         = out['item'].squeeze(-2)
    out['prevItem']     = out['prevItem'].squeeze(-2)

    # Moves
    moves = self.moves(out['moves'])
    lastmove = self.moves(out['lastmove'])

    for layer in self.moves_more:
      moves = layer(F.relu(moves))
      lastmove = layer(F.relu(lastmove))

    out['lastmove']     = lastmove.squeeze(-2)
    out['moves']        = moves.sum(-2)

    ms = [v for k, v in sorted(out.items())]
    ms = torch.cat(ms, -1)

    pkmn_out = F.relu(self.pkmn_affine(ms))
    for layer in self.pkmn_affine_more:
      pkmn_out = F.relu(layer(pkmn_out))

    return pkmn_out, moves

  def _forward_side(self, side):
    '''
    - (?, side_size) side data
    - (?, 6, poke_size) poke data
    - (?, 4, move_size) active move data
    '''

    pkmns, moves = self._forward_pkmn(side['pokemon'])

    group = F.relu(self.group_affine(pkmns))
    for layer in self.group_affine_more:
      group = F.relu(layer(group))
    group = group.max(1)[0]

    active_idx = side['activeIdx']
    has_active = (active_idx >= 0).type(config.tt())
    active_idx = torch.clamp(active_idx, min = 0)

    idx = torch.arange(active_idx.shape[0]).long()
    if active_idx.is_cuda:
      idx = idx.cuda()

    active = pkmns[idx, active_idx.squeeze(), :] * has_active
    moves = moves[idx, active_idx.squeeze(), :] * has_active.unsqueeze(-1)

    return torch.cat([active, group, side['sideConditions']], 1), pkmns, moves

# -----------------------------------------------------------------------------
# Extraction code below this line

Moves = spec('BattleMovedex')
Species = spec('BattlePokedex')
Types = spec('BattleTypeChart')
Statuses = spec('BattleStatuses')
Abilities = spec('BattleAbilities')
Items = spec('BattleItems')
Volatiles = spec('BattleVolatiles')
SideConditions = spec('BattleSideConditionsNew')
Weathers = spec('BattleWeathers')

Stats = ['atk', 'def', 'spa', 'spd', 'spe']
Boosts = ['accuracy', 'atk', 'def', 'evasion', 'spa', 'spd', 'spe']

# TODO: sample these based off of seen randombattles and not uniformly over species
MeanStats = gen7rb_stats().mean()[Stats].to_dict()
StdStats = gen7rb_stats().std()[Stats].to_dict()

MaxHp = gen7rb_stats()['hp'].max()
MeanHp = gen7rb_stats().mean()['hp']
StdHp = gen7rb_stats().std()['hp']

def whiten_stats(stats):
  return {k: (v - MeanStats[k]) / StdStats[k] / 3. for k, v in stats.iteritems()}

def whiten_hp(hp):
  return (hp - MeanHp) / StdHp

def extract(state, poke_features):
  player, opponent = extract_players(state)
  rv = dict(
      player = side2feat(player, poke_features),
      opponent = side2feat(opponent, poke_features),
      weather = Weathers.nhot(state['weather']),
      weatherMinTimeLeft = box(float(state.get('weatherMinTimeLeft', 0.))),
      weatherTimeLeft = box(float(state.get('weatherTimeLeft', 0.))),
  )
  return utils.flatten_dict(rv)

def side2feat(side, poke_features):
  pokes = _pad_pokes(side['pokemon'])

  pokemons = {}
  active_idx = -1
  for i, poke in enumerate(pokes):
    for k, v in poke2feat(poke, poke_features).iteritems():
      if k not in pokemons:
        pokemons[k] = np.zeros((len(pokes),) + v.shape, dtype = v.dtype)
      pokemons[k][i] = v

    if poke['active']:
      active_idx = i
  
  #pokemon = {k: np.stack(v, 0) for k, v in pokemons.iteritems()}
  pokemon = pokemons

  sideConditions = SideConditions.nhot(side['sideConditions'].keys())

  rv = dict(
      sideConditions = sideConditions,
      activeIdx = box([active_idx]),
  )
  rv['pokemon'] = pokemon

  return rv

def poke2feat(poke, poke_features):
  rv = {}
  compressed_idx = 0
  total_idx = 0
  for feature in poke_features:
    v = poke
    for fn in feature.pipeline:
      v = fn(v)
    v = box(v)

    rv[feature.name] = v

  return rv

# -----------------------------------------------------------------------------
# Small DSL for defining extraction

_nodefault = object()
def sort(key): return lambda d: sorted(d, key = key)
def dictkeys(d): return d.keys()
def dictvalues(d): return d.values()
def div(v): return lambda d: d / v
def seqmap(f): return lambda seq: map(f, seq)

def get(key, default = _nodefault):
  def func(d):
    if isinstance(d, dict):
      cond = key in d
    else:
      cond = isinstance(key, six.integer_types) and len(d) > key
    if not cond:
      if default is _nodefault:
        raise ValueError('Could not find %r in %r' % (key, d))
      return default
    return d[key]
  return func

def clip(size, drop = 'first'):
  assert drop in {'first', 'last'}
  def func(vs):
    vs = list(vs)
    if len(vs) > size:
      if drop == 'first':
        return vs[-size:]
      return vs[:size]
    return vs
  return func

def pad(size, obj = None, overflow = 'error'):
  def func(vs):
    vs = list(vs)
    if len(vs) > size:
      if overflow == 'error':
        raise ValueError('Found more than %s els in %s' % (size, vs))
      elif overflow == 'head':
        vs = vs[:size]
      else:
        raise ValueError('Unknown value for overflow: ' + overflow)
    while len(vs) < size:
      vs.append(obj)
    return vs
  return func

def mget(ks, default = _nodefault):
  def func(d):
    if default is _nodefault:
      assert all(k in d for k in ks)
    return [d.get(k, default) for k in ks]
  return func

def box(s):
  if not isinstance(s, (list, tuple, np.ndarray)):
    s = (s,)
  arr = np.asarray(s)
  if not np.issubdtype(arr.dtype, np.integer):
    arr = arr.astype(config.nt())
  return arr

@utils.const()
def default_statusData():
  return dict(sleepTurns = 0., toxicTurns = 0.)

@utils.const()
def default_poke():
  return dict(
      types = [],
      moveTrack = [],
      abilities = {},
      ability = CONST_HIDDEN,
      baseAbility = CONST_HIDDEN,
      species = CONST_HIDDEN,
      baseSpecies = CONST_HIDDEN,
      stats = MeanStats,
      item = CONST_HIDDEN,
      prevItem = CONST_HIDDEN,
      hp = MeanHp,
      maxhp = MeanHp,
      boosts = {},
      active = False,
      fainted = False,
      statusData = default_statusData(),
      status = CONST_NONE,
      lastmove = CONST_HIDDEN,
      volatiles = {},
  )

PokeFeature = collections.namedtuple('PokeFeature', 'name size embed pipeline')
Embed = collections.namedtuple('Embed', 'key combine')

# DO NOT CHANGE THE ORDERING HERE
_default_poke_features = [
    PokeFeature('abilities'  , EMBED_SIZE,     Embed('BattleAbilities', 'mean'), [get('abilities'), dictvalues, pad(3), Abilities]),
    PokeFeature('ability'    , EMBED_SIZE,     Embed('BattleAbilities', 'sum'),  [get('ability'), Abilities]),
    PokeFeature('baseAbility', EMBED_SIZE,     Embed('BattleAbilities', 'sum'),  [get('baseAbility'), Abilities]),
    PokeFeature('baseSpecies', EMBED_SIZE,     Embed('BattlePokedex', 'sum'),    [get('baseSpecies', None), Species]),
    PokeFeature('boosts'     , len(Boosts),    None,                             [get('boosts'), mget(Boosts, 0.), np.asarray, div(6.)]),
    PokeFeature('hp'         , 1,              None,                             [get('hp'), div(MaxHp)]),
    PokeFeature('isActive'   , 1,              None,                             [get('active'), float]),
    PokeFeature('isFainted'  , 1,              None,                             [get('fainted'), float]),
    PokeFeature('item'       , EMBED_SIZE,     Embed('BattleItems', 'sum'),      [get('item'), Items]),
    PokeFeature('lastmove'   , EMBED_SIZE,     Embed('BattleMovedex', 'sum'),    [get('lastmove', None), Moves]),
    PokeFeature('maxhp'      , 1,              None,                             [get('maxhp'), whiten_hp]),
    PokeFeature('moves'      , EMBED_SIZE,     Embed('BattleMovedex', 'sum'),    [get('moveTrack'), clip(4), seqmap(get(0)), pad(4), Moves]),
    PokeFeature('ppUsed'     , 4,              None,                             [get('moveTrack'), clip(4), seqmap(get(1)), pad(4, 0.), np.asarray, div(1.)]),
    PokeFeature('prevItem'   , EMBED_SIZE,     Embed('BattleItems', 'sum'),      [get('prevItem', None), Items]),
    PokeFeature('species'    , EMBED_SIZE,     Embed('BattlePokedex', 'sum'),    [get('species'), Species]),
    PokeFeature('stats'      , len(Stats),     None,                             [get('stats'), whiten_stats, mget(Stats)]),
    PokeFeature('status'     , Statuses.size,  None,                             [get('status'), Statuses.nhot]),
    PokeFeature('types'      , Types.size,     None,                             [get('types'), pad(2), Types.nhot]),
    PokeFeature('volatiles'  , Volatiles.size, None,                             [get('volatiles', {}), dictkeys, Volatiles.nhot]),
]

# TODO: Fix this for zoroarks.
_pad_pokes = pad(6, default_poke(), 'head')
