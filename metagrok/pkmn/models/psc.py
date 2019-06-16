import functools
import six
import numpy as np

from metagrok.pkmn.engine.navigation import extract_players
from metagrok.pkmn.features import spec, gen7rb_stats
from metagrok.pkmn.formulae import CONST_HIDDEN, CONST_NONE
from metagrok.pkmn.models import extractors as E

def default_statusData():
  return dict(sleepTurns = 0., toxicTurns = 0.)

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

# -- General purpose utility functions

def dictkeys(d): return d.keys()
def dictvalues(d): return d.values()
def div(v): return lambda d: d / v
def seqmap(f): return lambda seq: map(f, seq)

# A no-default sentinel (to detect when a default value is not passed in.)
_nodefault = object()

def mean(ls): return sum(ls) / float(len(ls))

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

# -- Below this line is the Features and Extractors

def make_basic_extractor():
  abilities = [get('abilities'), dictvalues, pad(3), Abilities]
  ability = [get('ability'), Abilities]
  baseAbility = [get('baseAbility'), Abilities]
  baseSpecies = [get('baseSpecies', None), Species]
  boosts = [get('boosts'), mget(Boosts, 0.), np.asarray, div(6.)]
  hp = [get('hp'), div(MaxHp)]
  isActive = [get('active'), float]
  isFainted = [get('fainted'), float]
  item = [get('item'), Items]
  lastmove = [get('lastmove', None), Moves]
  maxhp = [get('maxhp'), whiten_hp]
  moves = [get('moveTrack'), seqmap(get(0)), pad(9), Moves]
  ppUsed = [get('moveTrack'), seqmap(get(1)), pad(9, 0.), np.asarray, div(1.)]
  prevItem = [get('prevItem', None), Items]
  species = [get('species'), Species]
  stats = [get('stats'), whiten_stats, mget(Stats)]
  status = [get('status'), Statuses.nhot]
  types = [get('types'), pad(2), Types.nhot]
  volatiles = [get('volatiles', {}), dictkeys, Volatiles.nhot]

  # DO NOT CHANGE THE ORDERING HERE
  PokeExtractor = E.concatenate([
    E.make_feature(abilities + [Abilities.nembed, mean]),
    E.make_feature(ability + [Abilities.nembed, sum]),
    E.make_feature(baseAbility + [Abilities.nembed, sum]),
    E.make_feature(baseSpecies + [Species.nembed, sum]),
    E.make_feature(boosts),
    E.make_feature(hp),
    E.make_feature(isActive),
    E.make_feature(isFainted),
    E.make_feature(item + [Items.nembed, sum]),
    E.make_feature(lastmove + [Moves.nembed, sum]),
    E.make_feature(maxhp),
    E.make_feature(moves + [Moves.nembed, mean]),
    E.make_feature(ppUsed),
    E.make_feature(prevItem + [Items.nembed, sum]),
    E.make_feature(species + [Species.nembed, sum]),
    E.make_feature(stats),
    E.make_feature(status),
    E.make_feature(types),
    E.make_feature(volatiles),
  ], 0)

  PokeArrayExtractor = PokeExtractor.array()

  get_active_pokemon = [
    get('pokemon'),
    functools.partial(filter, lambda x: x['active']),
    pad(2, default_poke()),
  ]

  SideExtractor = E.Extractor(
    sideConditions = E.make_feature([get('sideConditions'), dictkeys, SideConditions.nhot]),
    pokemon = PokeArrayExtractor.pre_apply(
      get('pokemon'),
      pad(6, default_poke())
    ),
    activePokemon = PokeArrayExtractor.pre_apply(*get_active_pokemon),
  )

  get_player = [extract_players, get(0)]
  get_opponent = [extract_players, get(1)]

  return E.Extractor(
    player = SideExtractor.pre_apply(*get_player),
    opponent = SideExtractor.pre_apply(*get_opponent),
    weather = E.make_feature([get('weather'), Weathers.nhot]),
    weatherTimeLeft = E.concatenate([
      E.make_feature([get('weatherTimeLeft', 0.), float]),
      E.make_feature([get('weatherMinTimeLeft', 0.), float]),
    ], 0),
    moves = (E.make_feature(moves + [clip(4, drop = 'last'), Moves.nembed])
      .array()
      .pre_apply(*(get_player + get_active_pokemon))),
  )

def main():
  import pprint
  from metagrok import jsons

  test_file = 'test-data/reward-shaper-tests.jsons'
  jsons = jsons.load(test_file)
  Extractor = make_basic_extractor() 
  for line in jsons[:-1]:
    feats = Extractor.extract(line['state'])
    pprint.pprint(E.shape(feats))
    six.moves.input()

if __name__ == '__main__':
  main()