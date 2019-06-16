import random

_FIXED_SEED_PKMN = ']'.join([
  'Volbeat||leftovers|H|tailwind,substitute,thunderwave,bugbuzz||81,,85,85,85,85||,0,,,,||83|',
  'Pangoro||choiceband|1|gunkshot,superpower,knockoff,icepunch||85,85,85,85,85,85||||79|',
  'Serperior||leftovers|H|substitute,hiddenpowerfire,leafstorm,leechseed||85,,85,85,85,85||,0,,,,||77|',
  'Conkeldurr||flameorb||bulkup,icepunch,machpunch,drainpunch||85,85,85,85,85,85||||76|',
  'Starmie||leftovers|1|thunderbolt,rapidspin,recover,scald||85,85,85,85,85,85||||77|',
  'Carbink||custapberry|H|stealthrock,explosion,lightscreen,powergem||85,85,85,85,85,85||||83|',
])

_ZOROARKS_PKMN = ']'.join([
  'Zoroark||leftovers|0|nastyplot,knockoff,focusblast,flamethrower||85,85,85,85,85,85||||78|',
  'Pangoro||choiceband|1|gunkshot,superpower,knockoff,icepunch||85,85,85,85,85,85||||79|',
  'Serperior||leftovers|H|substitute,hiddenpowerfire,leafstorm,leechseed||85,,85,85,85,85||,0,,,,||77|',
  'Conkeldurr||flameorb||bulkup,icepunch,machpunch,drainpunch||85,85,85,85,85,85||||76|',
  'Starmie||leftovers|1|thunderbolt,rapidspin,recover,scald||85,85,85,85,85,85||||77|',
  'Carbink||custapberry|H|stealthrock,explosion,lightscreen,powergem||85,85,85,85,85,85||||83|',
])

def _1_coverage(level = ''):
  return ']'.join([
    'Mimikyu||lifeorb||swordsdance,shadowclaw,shadowsneak,playrough|Jolly|,252,,,4,252||||%s|' % level,
    'Medicham-Mega||medichamite||icepunch,firepunch,poweruppunch,zenheadbutt|Jolly|,252,,,4,252||||%s|' % level,
    'Garchomp||leftovers|H|crunch,dragonclaw,firefang,earthquake|Jolly|,252,,,4,252||||%s|' % level,
    'Volcarona||buginiumz||quiverdance,bugbuzz,fierydance,uturn|Modest|,,,252,4,252||||%s|' % level,
    'Toxapex||leftovers||toxicspikes,recover,scald,poisonjab|Impish|252,4,252,,,||||%s|' % level,
    'Magnezone||airballoon||flashcannon,thunderbolt,hiddenpowerfire,toxic|Bold|248,,252,8,,||,0,,,,||%s|' % level,
  ])

def _2_psyspam(level = ''):
  return ']'.join([
    'Alakazam-Mega||alakazite|magicguard|psychic,focusblast,shadowball,hiddenpowerfire|Timid|,,,252,4,252||,0,,,,||%s|' % level,
    'Tapu Lele||psychiumz||calmmind,psyshock,moonblast,hiddenpowerfire|Timid|,,,252,4,252||,0,,,,||%s|' % level,
    'Kartana||choicescarf||leafblade,knockoff,sacredsword,defog|Jolly|,252,4,,,252||||%s|' % level,
    'Greninja-Ash||choicespecs||spikes,watershuriken,hydropump,darkpulse|Timid|,,,252,4,252||||%s|' % level,
    'Landorus-Therian||rockyhelmet||stealthrock,earthquake,hiddenpowerice,uturn|Impish|248,,200,,,60||,30,30,,,||%s|' % level,
    'Magearna||assaultvest||fleurcannon,ironhead,hiddenpowerfire,voltswitch|Sassy|248,,52,,208,||,,,,,20||%s|' % level,
  ])

def _3_trickroom(level = ''):
  return ']'.join([
    'Marowak-Alola||thickclub|H|shadowbone,flareblitz,swordsdance,bonemerang|Adamant|248,252,,,8,||,,,,,0||%s|' % level,
    'Cresselia||mentalherb||trickroom,icebeam,moonlight,lunardance|Relaxed|248,,252,,8,||,0,,,,0||%s|' % level,
    'Mawile||mawilite||playrough,suckerpunch,thunderpunch,firefang|Adamant|248,252,,,8,||,,,,,0||%s|' % level,
    'Uxie||mentalherb||trickroom,stealthrock,memento,magiccoat|Bold|252,,116,,140,||,0,,,,0||%s|' % level,
    'Crawdaunt||lifeorb|H|knockoff,crabhammer,aquajet,swordsdance|Adamant|252,252,,,4,||,,,,,0||%s|' % level,
    'Magearna||fairiumz||trickroom,fleurcannon,focusblast,thunderbolt|Quiet|252,,,252,4,||,0,,,,0||%s|' % level,
  ])


_MATRIX_GRID_TEAMS = {1: _1_coverage(), 2: _2_psyspam(), 3: _3_trickroom()}

_NAME_TO_OPTIONS = dict(
  gen7randombattle = dict(
    formatid = 'gen7randombattle',
    p1 = {'name': 'p1'},
    p2 = {'name': 'p2'},
  ),
  gen7fixedseed01abcdef = dict(
    formatid = '',
    p1 = {'name': 'p1', 'team': _FIXED_SEED_PKMN},
    p2 = {'name': 'p2', 'team': _FIXED_SEED_PKMN},
  ),
  gen7zoroarks = dict(
    formatid = '',
    p1 = {'name': 'p1', 'team': _ZOROARKS_PKMN},
    p2 = {'name': 'p2', 'team': _ZOROARKS_PKMN},
  ),
  gen7matrix = dict(
    formatid = 'gen7ou',
    p1 = lambda: random_matrix_team('p1'),
    p2 = lambda: random_matrix_team('p2'),
  ),
)

for i in [1, 2, 3]:
  for j in [1, 2, 3]:
    _NAME_TO_OPTIONS['gen7ouc{}v{}'.format(i, j)] = dict(
      formatid = 'gen7ou',
      p1 = {'name': 'p1', 'team': _MATRIX_GRID_TEAMS[i]},
      p2 = {'name': 'p2', 'team': _MATRIX_GRID_TEAMS[j]},
    )

def _make_fixed_team_p1_meta(p1_team):
  return dict(
    formatid = 'gen7ou',
    p1 = {'name': 'p1', 'team': p1_team},
    p2 = {'name': 'p2'},
  )

_NAME_TO_OPTIONS['gen7c1'] = _make_fixed_team_p1_meta(_1_coverage(81))
_NAME_TO_OPTIONS['gen7c2'] = _make_fixed_team_p1_meta(_2_psyspam(81))
_NAME_TO_OPTIONS['gen7c3'] = _make_fixed_team_p1_meta(_3_trickroom(81))

_pfx_to_team = dict(
  gen7c1 = _1_coverage,
  gen7c2 = _2_psyspam,
  gen7c3 = _3_trickroom,
)

def get(name):
  name = name.lower()
  if ':' in name:
    pfx, level = name.split(':')
    team_ctor = _pfx_to_team[pfx]
    return _make_fixed_team_p1_meta(team_ctor(int(level)))

  fmt = _NAME_TO_OPTIONS[name]
  rv = {}
  for k, v in fmt.iteritems():
    if callable(v):
      v = v()
    rv[k] = v
  return rv

def random_matrix_team(name):
  rv = {'name': name}
  rv['team'] = random.choice(_MATRIX_GRID_TEAMS.values())
  return rv

def default():
  return get('gen7randombattle')

def all():
  return _NAME_TO_OPTIONS.keys()
