import unittest

from metagrok.pkmn import parser

class ParserTest(unittest.TestCase):
  def test_parse_hp_status(self):
    self.assertEqual(parser.parse_hp_status('100/100'), {'hp': 100, 'maxhp': 100, 'status': ''})
    self.assertEqual(parser.parse_hp_status('75/350 psn'), {'hp': 75, 'maxhp': 350, 'status': 'psn'})
    self.assertEqual(parser.parse_hp_status('0 fnt'), {'hp': 0, 'status': 'fnt'})
    self.assertEqual(parser.parse_hp_status('brn'), {'status': 'brn'})
  
  def test_parse_poke_id(self):
    self.assertEqual(parser.parse_poke_id('p1: marcopopopo'), ('p1', 'marcopopopo'))
    self.assertEqual(parser.parse_poke_id('p2a: Tapu Bulu'), ('p2', 'Tapu Bulu'))

  def test_parse_valid_actions_singles(self):
    actions = parser.parse_valid_actions(single())
    all_actions = parser.all_actions_singles()
    self.assertEqual(len(all_actions), len(actions))
    for expected, actual in zip(all_actions, actions):
      if is_normal_move(expected):
        self.assertIsNot(actual, None)
      else:
        self.assertIs(actual, None)

  #@unittest.skip("doubles doesn't work")
  #def test_parse_valid_actions_doubles(self):
  #  actions = parser.parse_valid_actions(double())
  #  all_actions = parser.all_actions_doubles()
  #  self.assertEqual(len(all_actions), len(actions))
  #  for expected, actual in zip(all_actions, actions):
  #    v1, v2 = expected.split(',')
  #    if is_normal_move(v1) and is_normal_move(v2):
  #      self.assertIsNot(actual, None)
  #    elif is_normal_move(v1) and is_switch(v2, exclude = [1, 2, 4, 5, 6]):
  #      self.assertIsNot(actual, None)
  #    elif is_normal_move(v2) and is_switch(v1, exclude = [1, 2, 4, 5, 6]):
  #      self.assertIsNot(actual, None)
  #    else:
  #      self.assertIs(actual, None)

  def test_parse_valid_actions_mega(self):
    actions = parser.parse_valid_actions(single_with_mega())
    all_actions = parser.all_actions_singles()
    self.assertEqual(len(all_actions), len(actions))
    for expected, actual in zip(all_actions, actions):
      if is_normal_move(expected) or is_mega_move(expected) or is_switch(expected, exclude = [1, 5]):
        self.assertIsNot(actual, None)
      else:
        self.assertIs(actual, None)

  def test_parse_valid_actions_zmove(self):
    actions = parser.parse_valid_actions(single_with_zmove())
    all_actions = parser.all_actions_singles()
    self.assertEqual(len(all_actions), len(actions))
    for expected, actual in zip(all_actions, actions):
      if is_normal_move(expected) or is_switch(expected, exclude = [1]):
        self.assertIsNot(actual, None)
      elif expected == 'move 3 zmove':
        self.assertIsNot(actual, None)
      else:
        self.assertIs(actual, None)

  #@unittest.skip("doubles doesn't work")
  #def test_parse_valid_actions_double_forceSwitch(self):
  #  actions = parser.parse_valid_actions(double_with_forceSwitch())
  #  all_actions = parser.all_actions_doubles()
  #  self.assertEqual(len(all_actions), len(actions))
  #  for expected, actual in zip(all_actions, actions):
  #    v1, v2 = expected.split(',')
  #    if is_switch(v1, exclude = [1, 2, 6]) and v2 == 'pass':
  #      self.assertIsNot(actual, None)
  #    else:
  #      self.assertIs(actual, None)

  #@unittest.skip("doubles doesn't work")
  #def test_parse_valid_actions_double_forceSwitch_last(self):
  #  actions = parser.parse_valid_actions(double_with_double_forceSwitch_last())
  #  all_actions = parser.all_actions_doubles()
  #  self.assertEqual(len(all_actions), len(actions))
  #  for expected, actual in zip(all_actions, actions):
  #    v1, v2 = expected.split(',')
  #    if is_switch(v1, exclude = [1, 2, 4, 5, 6]) and v2 == 'pass':
  #      self.assertIsNot(actual, None)
  #    elif v1 == 'pass' and is_switch(v2, exclude = [1, 2, 4, 5, 6]):
  #      self.assertIsNot(actual, None)
  #    else:
  #      self.assertIs(actual, None)

def is_normal_move(v):
  return v in {'move 1', 'move 2', 'move 3', 'move 4'}

def is_mega_move(v):
  return v in {'move 1 mega', 'move 2 mega', 'move 3 mega', 'move 4 mega'}

def is_switch(v, exclude = []):
  return v in {'switch %d' % i for i in range(1, 7) if i not in exclude}

def single():
  return {
    "active": [
      {
        "moves": [
          {
            "move": "Shadow Bone",
            "id": "shadowbone",
            "pp": 15,
            "maxpp": 16,
            "target": "normal",
            "disabled": False
          },
          {
            "move": "Will-O-Wisp",
            "id": "willowisp",
            "pp": 22,
            "maxpp": 24,
            "target": "normal",
            "disabled": False
          },
          {
            "move": "Stone Edge",
            "id": "stoneedge",
            "pp": 7,
            "maxpp": 8,
            "target": "normal",
            "disabled": False
          },
          {
            "move": "Flame Charge",
            "id": "flamecharge",
            "pp": 32,
            "maxpp": 32,
            "target": "normal",
            "disabled": False
          }
        ]
      }
    ],
    "side": {
      "name": "yuzeh",
      "id": "p1",
      "pokemon": [
        {
          "ident": "p1: Marowak",
          "details": "Marowak-Alola, L79, F",
          "condition": "19/223",
          "active": True,
          "stats": {
            "atk": 172,
            "def": 219,
            "spa": 125,
            "spd": 172,
            "spe": 117
          },
          "moves": [
            "shadowbone",
            "willowisp",
            "stoneedge",
            "flamecharge"
          ],
          "baseAbility": "lightningrod",
          "item": "thickclub",
          "pokeball": "pokeball",
          "ability": "lightningrod"
        },
        {
          "ident": "p1: Bewear",
          "details": "Bewear, L79, F",
          "condition": "0 fnt",
          "active": False,
          "stats": {
            "atk": 243,
            "def": 172,
            "spa": 132,
            "spd": 140,
            "spe": 140
          },
          "moves": [
            "hammerarm",
            "icepunch",
            "return",
            "shadowclaw"
          ],
          "baseAbility": "fluffy",
          "item": "choicescarf",
          "pokeball": "pokeball",
          "ability": "fluffy"
        },
        {
          "ident": "p1: Samurott",
          "details": "Samurott, L82, M",
          "condition": "0 fnt",
          "active": False,
          "stats": {
            "atk": 211,
            "def": 187,
            "spa": 224,
            "spd": 162,
            "spe": 162
          },
          "moves": [
            "grassknot",
            "icebeam",
            "hydropump",
            "megahorn"
          ],
          "baseAbility": "torrent",
          "item": "assaultvest",
          "pokeball": "pokeball",
          "ability": "torrent"
        },
        {
          "ident": "p1: Slowbro",
          "details": "Slowbro-Mega, L77, M",
          "condition": "0 fnt",
          "active": False,
          "stats": {
            "atk": 120,
            "def": 322,
            "spa": 245,
            "spd": 168,
            "spe": 91
          },
          "moves": [
            "calmmind",
            "slackoff",
            "scald",
            "icebeam"
          ],
          "baseAbility": "shellarmor",
          "item": "slowbronite",
          "pokeball": "pokeball",
          "ability": "shellarmor"
        },
        {
          "ident": "p1: Grumpig",
          "details": "Grumpig, L83, F",
          "condition": "0 fnt",
          "active": False,
          "stats": {
            "atk": 79,
            "def": 156,
            "spa": 197,
            "spd": 230,
            "spe": 180
          },
          "moves": [
            "toxic",
            "focusblast",
            "whirlwind",
            "psychic"
          ],
          "baseAbility": "thickfat",
          "item": "focussash",
          "pokeball": "pokeball",
          "ability": "thickfat"
        },
        {
          "ident": "p1: Celesteela",
          "details": "Celesteela, L75",
          "condition": "0 fnt",
          "active": False,
          "stats": {
            "atk": 195,
            "def": 198,
            "spa": 204,
            "spd": 195,
            "spe": 135
          },
          "moves": [
            "heavyslam",
            "fireblast",
            "leechseed",
            "protect"
          ],
          "baseAbility": "beastboost",
          "item": "leftovers",
          "pokeball": "pokeball",
          "ability": "beastboost"
        }
      ]
    },
    "rqid": 84
  }

def double():
  return {
    "active": [
      {
        "moves": [
          {
            "move": "Fire Blast",
            "id": "fireblast",
            "pp": 8,
            "maxpp": 8,
            "target": "normal",
            "disabled": False
          },
          {
            "move": "Heat Wave",
            "id": "heatwave",
            "pp": 15,
            "maxpp": 16,
            "target": "allAdjacentFoes",
            "disabled": False
          },
          {
            "move": "Dragon Pulse",
            "id": "dragonpulse",
            "pp": 16,
            "maxpp": 16,
            "target": "any",
            "disabled": False
          },
          {
            "move": "Air Slash",
            "id": "airslash",
            "pp": 23,
            "maxpp": 24,
            "target": "any",
            "disabled": False
          }
        ]
      },
      {
        "moves": [
          {
            "move": "String Shot",
            "id": "stringshot",
            "pp": 63,
            "maxpp": 64,
            "target": "allAdjacentFoes",
            "disabled": False
          },
          {
            "move": "Rock Blast",
            "id": "rockblast",
            "pp": 16,
            "maxpp": 16,
            "target": "normal",
            "disabled": False
          },
          {
            "move": "Earthquake",
            "id": "earthquake",
            "pp": 15,
            "maxpp": 16,
            "target": "allAdjacent",
            "disabled": False
          },
          {
            "move": "Protect",
            "id": "protect",
            "pp": 15,
            "maxpp": 16,
            "target": "self",
            "disabled": False
          }
        ]
      }
    ],
    "side": {
      "name": "yuzeh",
      "id": "p2",
      "pokemon": [
        {
          "ident": "p2: Charizard",
          "details": "Charizard, L76, M",
          "condition": "34/243",
          "active": True,
          "stats": {
            "atk": 132,
            "def": 163,
            "spa": 210,
            "spd": 173,
            "spe": 196
          },
          "moves": [
            "fireblast",
            "heatwave",
            "dragonpulse",
            "airslash"
          ],
          "baseAbility": "blaze",
          "item": "lifeorb",
          "pokeball": "pokeball",
          "ability": "blaze"
        },
        {
          "ident": "p2: Wormadam",
          "details": "Wormadam-Sandy, L87, F",
          "condition": "130/246",
          "active": True,
          "stats": {
            "atk": 187,
            "def": 232,
            "spa": 152,
            "spd": 198,
            "spe": 112
          },
          "moves": [
            "stringshot",
            "rockblast",
            "earthquake",
            "protect"
          ],
          "baseAbility": "overcoat",
          "item": "sitrusberry",
          "pokeball": "pokeball",
          "ability": "overcoat"
        },
        {
          "ident": "p2: Camerupt",
          "details": "Camerupt-Mega, L73, F",
          "condition": "223/223",
          "active": False,
          "stats": {
            "atk": 180,
            "def": 188,
            "spa": 254,
            "spd": 196,
            "spe": 72
          },
          "moves": [
            "earthpower",
            "heatwave",
            "fireblast",
            "protect"
          ],
          "baseAbility": "sheerforce",
          "item": "cameruptite",
          "pokeball": "pokeball",
          "ability": "sheerforce"
        },
        {
          "ident": "p2: Virizion",
          "details": "Virizion, L71",
          "condition": "0 fnt",
          "active": False,
          "stats": {
            "atk": 169,
            "def": 144,
            "spa": 169,
            "spd": 225,
            "spe": 195
          },
          "moves": [
            "taunt",
            "closecombat",
            "synthesis",
            "protect"
          ],
          "baseAbility": "justified",
          "item": "",
          "pokeball": "pokeball",
          "ability": "justified"
        },
        {
          "ident": "p2: Donphan",
          "details": "Donphan, L79, M",
          "condition": "0 fnt",
          "active": False,
          "stats": {
            "atk": 235,
            "def": 235,
            "spa": 140,
            "spd": 140,
            "spe": 125
          },
          "moves": [
            "knockoff",
            "rockslide",
            "iceshard",
            "earthquake"
          ],
          "baseAbility": "sturdy",
          "item": "expertbelt",
          "pokeball": "pokeball",
          "ability": "sturdy"
        },
        {
          "ident": "p2: Cinccino",
          "details": "Cinccino, L82, M",
          "condition": "0 fnt",
          "active": False,
          "stats": {
            "atk": 203,
            "def": 146,
            "spa": 154,
            "spd": 146,
            "spe": 236
          },
          "moves": [
            "uturn",
            "rockblast",
            "knockoff",
            "tailslap"
          ],
          "baseAbility": "skilllink",
          "item": "lifeorb",
          "pokeball": "pokeball",
          "ability": "skilllink"
        }
      ]
    },
    "rqid": 29
  }

def single_with_mega():
  return {
    "active": [
      {
        "moves": [
          {
            "move": "Calm Mind",
            "id": "calmmind",
            "pp": 32,
            "maxpp": 32,
            "target": "self",
            "disabled": False
          },
          {
            "move": "Slack Off",
            "id": "slackoff",
            "pp": 16,
            "maxpp": 16,
            "target": "self",
            "disabled": False
          },
          {
            "move": "Scald",
            "id": "scald",
            "pp": 24,
            "maxpp": 24,
            "target": "normal",
            "disabled": False
          },
          {
            "move": "Ice Beam",
            "id": "icebeam",
            "pp": 16,
            "maxpp": 16,
            "target": "normal",
            "disabled": False
          }
        ],
        "canMegaEvo": True
      }
    ],
    "side": {
      "name": "yuzeh",
      "id": "p1",
      "pokemon": [
        {
          "ident": "p1: Slowbro",
          "details": "Slowbro, L77, M",
          "condition": "256/273 brn",
          "active": True,
          "stats": {
            "atk": 120,
            "def": 214,
            "spa": 199,
            "spd": 168,
            "spe": 91
          },
          "moves": [
            "calmmind",
            "slackoff",
            "scald",
            "icebeam"
          ],
          "baseAbility": "regenerator",
          "item": "slowbronite",
          "pokeball": "pokeball",
          "ability": "regenerator"
        },
        {
          "ident": "p1: Samurott",
          "details": "Samurott, L82, M",
          "condition": "290/290",
          "active": False,
          "stats": {
            "atk": 211,
            "def": 187,
            "spa": 224,
            "spd": 162,
            "spe": 162
          },
          "moves": [
            "grassknot",
            "icebeam",
            "hydropump",
            "megahorn"
          ],
          "baseAbility": "torrent",
          "item": "assaultvest",
          "pokeball": "pokeball",
          "ability": "torrent"
        },
        {
          "ident": "p1: Celesteela",
          "details": "Celesteela, L75",
          "condition": "268/269",
          "active": False,
          "stats": {
            "atk": 195,
            "def": 198,
            "spa": 204,
            "spd": 195,
            "spe": 135
          },
          "moves": [
            "heavyslam",
            "fireblast",
            "leechseed",
            "protect"
          ],
          "baseAbility": "beastboost",
          "item": "leftovers",
          "pokeball": "pokeball",
          "ability": "beastboost"
        },
        {
          "ident": "p1: Bewear",
          "details": "Bewear, L79, F",
          "condition": "17/319",
          "active": False,
          "stats": {
            "atk": 243,
            "def": 172,
            "spa": 132,
            "spd": 140,
            "spe": 140
          },
          "moves": [
            "hammerarm",
            "icepunch",
            "return",
            "shadowclaw"
          ],
          "baseAbility": "fluffy",
          "item": "choicescarf",
          "pokeball": "pokeball",
          "ability": "fluffy"
        },
        {
          "ident": "p1: Grumpig",
          "details": "Grumpig, L83, F",
          "condition": "0 fnt",
          "active": False,
          "stats": {
            "atk": 79,
            "def": 156,
            "spa": 197,
            "spd": 230,
            "spe": 180
          },
          "moves": [
            "toxic",
            "focusblast",
            "whirlwind",
            "psychic"
          ],
          "baseAbility": "thickfat",
          "item": "focussash",
          "pokeball": "pokeball",
          "ability": "thickfat"
        },
        {
          "ident": "p1: Marowak",
          "details": "Marowak-Alola, L79, F",
          "condition": "223/223",
          "active": False,
          "stats": {
            "atk": 172,
            "def": 219,
            "spa": 125,
            "spd": 172,
            "spe": 117
          },
          "moves": [
            "shadowbone",
            "willowisp",
            "stoneedge",
            "flamecharge"
          ],
          "baseAbility": "lightningrod",
          "item": "thickclub",
          "pokeball": "pokeball",
          "ability": "lightningrod"
        }
      ]
    },
    "rqid": 26
  }

def double_with_forceSwitch():
  return {
    "side": {
      "name": "yuzeh",
      "id": "p2",
      "pokemon": [
        {
          "ident": "p2: Donphan",
          "details": "Donphan, L79, M",
          "condition": "0 fnt",
          "active": True,
          "stats": {
            "atk": 235,
            "def": 235,
            "spa": 140,
            "spd": 140,
            "spe": 125
          },
          "moves": [
            "knockoff",
            "rockslide",
            "iceshard",
            "earthquake"
          ],
          "baseAbility": "sturdy",
          "item": "expertbelt",
          "pokeball": "pokeball",
          "ability": "sturdy"
        },
        {
          "ident": "p2: Wormadam",
          "details": "Wormadam-Sandy, L87, F",
          "condition": "246/246",
          "active": True,
          "stats": {
            "atk": 187,
            "def": 232,
            "spa": 152,
            "spd": 198,
            "spe": 112
          },
          "moves": [
            "stringshot",
            "rockblast",
            "earthquake",
            "protect"
          ],
          "baseAbility": "overcoat",
          "item": "sitrusberry",
          "pokeball": "pokeball",
          "ability": "overcoat"
        },
        {
          "ident": "p2: Camerupt",
          "details": "Camerupt-Mega, L73, F",
          "condition": "223/223",
          "active": False,
          "stats": {
            "atk": 180,
            "def": 188,
            "spa": 254,
            "spd": 196,
            "spe": 72
          },
          "moves": [
            "earthpower",
            "heatwave",
            "fireblast",
            "protect"
          ],
          "baseAbility": "sheerforce",
          "item": "cameruptite",
          "pokeball": "pokeball",
          "ability": "sheerforce"
        },
        {
          "ident": "p2: Charizard",
          "details": "Charizard, L76, M",
          "condition": "204/243",
          "active": False,
          "stats": {
            "atk": 132,
            "def": 163,
            "spa": 210,
            "spd": 173,
            "spe": 196
          },
          "moves": [
            "fireblast",
            "heatwave",
            "dragonpulse",
            "airslash"
          ],
          "baseAbility": "blaze",
          "item": "lifeorb",
          "pokeball": "pokeball",
          "ability": "blaze"
        },
        {
          "ident": "p2: Virizion",
          "details": "Virizion, L71",
          "condition": "247/247",
          "active": False,
          "stats": {
            "atk": 169,
            "def": 144,
            "spa": 169,
            "spd": 225,
            "spe": 195
          },
          "moves": [
            "taunt",
            "closecombat",
            "synthesis",
            "protect"
          ],
          "baseAbility": "justified",
          "item": "",
          "pokeball": "pokeball",
          "ability": "justified"
        },
        {
          "ident": "p2: Cinccino",
          "details": "Cinccino, L82, M",
          "condition": "0 fnt",
          "active": False,
          "stats": {
            "atk": 203,
            "def": 146,
            "spa": 154,
            "spd": 146,
            "spe": 236
          },
          "moves": [
            "uturn",
            "rockblast",
            "knockoff",
            "tailslap"
          ],
          "baseAbility": "skilllink",
          "item": "lifeorb",
          "pokeball": "pokeball",
          "ability": "skilllink"
        }
      ]
    },
    "rqid": 19,
    "forceSwitch": [
      True,
      False
    ],
    "noCancel": True
  }

def double_with_double_forceSwitch_last():
  return {
    "forceSwitch": [
      True,
      True
    ],
    "side": {
      "name": "yuzeh",
      "id": "p2",
      "pokemon": [
        {
          "ident": "p2: Charizard",
          "details": "Charizard, L76, M",
          "condition": "0 fnt",
          "active": True,
          "stats": {
            "atk": 132,
            "def": 163,
            "spa": 210,
            "spd": 173,
            "spe": 196
          },
          "moves": [
            "fireblast",
            "heatwave",
            "dragonpulse",
            "airslash"
          ],
          "baseAbility": "blaze",
          "item": "lifeorb",
          "pokeball": "pokeball",
          "ability": "blaze"
        },
        {
          "ident": "p2: Wormadam",
          "details": "Wormadam-Sandy, L87, F",
          "condition": "0 fnt",
          "active": True,
          "stats": {
            "atk": 187,
            "def": 232,
            "spa": 152,
            "spd": 198,
            "spe": 112
          },
          "moves": [
            "stringshot",
            "rockblast",
            "earthquake",
            "protect"
          ],
          "baseAbility": "overcoat",
          "item": "sitrusberry",
          "pokeball": "pokeball",
          "ability": "overcoat"
        },
        {
          "ident": "p2: Camerupt",
          "details": "Camerupt-Mega, L73, F",
          "condition": "223/223",
          "active": False,
          "stats": {
            "atk": 180,
            "def": 188,
            "spa": 254,
            "spd": 196,
            "spe": 72
          },
          "moves": [
            "earthpower",
            "heatwave",
            "fireblast",
            "protect"
          ],
          "baseAbility": "sheerforce",
          "item": "cameruptite",
          "pokeball": "pokeball",
          "ability": "sheerforce"
        },
        {
          "ident": "p2: Virizion",
          "details": "Virizion, L71",
          "condition": "0 fnt",
          "active": False,
          "stats": {
            "atk": 169,
            "def": 144,
            "spa": 169,
            "spd": 225,
            "spe": 195
          },
          "moves": [
            "taunt",
            "closecombat",
            "synthesis",
            "protect"
          ],
          "baseAbility": "justified",
          "item": "",
          "pokeball": "pokeball",
          "ability": "justified"
        },
        {
          "ident": "p2: Donphan",
          "details": "Donphan, L79, M",
          "condition": "0 fnt",
          "active": False,
          "stats": {
            "atk": 235,
            "def": 235,
            "spa": 140,
            "spd": 140,
            "spe": 125
          },
          "moves": [
            "knockoff",
            "rockslide",
            "iceshard",
            "earthquake"
          ],
          "baseAbility": "sturdy",
          "item": "expertbelt",
          "pokeball": "pokeball",
          "ability": "sturdy"
        },
        {
          "ident": "p2: Cinccino",
          "details": "Cinccino, L82, M",
          "condition": "0 fnt",
          "active": False,
          "stats": {
            "atk": 203,
            "def": 146,
            "spa": 154,
            "spd": 146,
            "spe": 236
          },
          "moves": [
            "uturn",
            "rockblast",
            "knockoff",
            "tailslap"
          ],
          "baseAbility": "skilllink",
          "item": "lifeorb",
          "pokeball": "pokeball",
          "ability": "skilllink"
        }
      ]
    },
    "noCancel": True,
    "rqid": 31
  }

def single_with_zmove():
  return {
    "side": {
      "name": "yuzeh",
      "id": "p1",
      "pokemon": [
        {
          "ident": "p1: A1",
          "details": "Necrozma-Ultra",
          "condition": "315/336",
          "active": True,
          "stats": {
            "atk": 305,
            "def": 230,
            "spa": 433,
            "spd": 230,
            "spe": 392
          },
          "moves": [
            "calmmind",
            "morningsun",
            "photongeyser",
            "heatwave"
          ],
          "baseAbility": "neuroforce",
          "item": "ultranecroziumz",
          "pokeball": "pokeball",
          "ability": "neuroforce"
        },
        {
          "ident": "p1: A2",
          "details": "Salamence, M, shiny",
          "condition": "331/331",
          "active": False,
          "stats": {
            "atk": 369,
            "def": 196,
            "spa": 230,
            "spd": 197,
            "spe": 328
          },
          "moves": [
            "dragondance",
            "frustration",
            "roost",
            "earthquake"
          ],
          "baseAbility": "intimidate",
          "item": "salamencite",
          "pokeball": "pokeball",
          "ability": "intimidate"
        },
        {
          "ident": "p1: A3",
          "details": "Arceus-Steel",
          "condition": "398/398",
          "active": False,
          "stats": {
            "atk": 220,
            "def": 276,
            "spa": 323,
            "spd": 276,
            "spe": 372
          },
          "moves": [
            "judgment",
            "defog",
            "icebeam",
            "recover"
          ],
          "baseAbility": "multitype",
          "item": "ironplate",
          "pokeball": "pokeball",
          "ability": "multitype"
        },
        {
          "ident": "p1: A4",
          "details": "Pheromosa, shiny",
          "condition": "283/283",
          "active": False,
          "stats": {
            "atk": 373,
            "def": 99,
            "spa": 311,
            "spd": 110,
            "spe": 441
          },
          "moves": [
            "highjumpkick",
            "bugbuzz",
            "icebeam",
            "poisonjab"
          ],
          "baseAbility": "beastboost",
          "item": "focussash",
          "pokeball": "pokeball",
          "ability": "beastboost"
        },
        {
          "ident": "p1: A5",
          "details": "Yveltal, shiny",
          "condition": "393/393",
          "active": False,
          "stats": {
            "atk": 240,
            "def": 226,
            "spa": 361,
            "spd": 233,
            "spe": 326
          },
          "moves": [
            "darkpulse",
            "taunt",
            "focusblast",
            "oblivionwing"
          ],
          "baseAbility": "darkaura",
          "item": "lifeorb",
          "pokeball": "pokeball",
          "ability": "darkaura"
        },
        {
          "ident": "p1: A6",
          "details": "Deoxys-Speed, shiny",
          "condition": "304/304",
          "active": False,
          "stats": {
            "atk": 227,
            "def": 216,
            "spa": 203,
            "spd": 216,
            "spe": 504
          },
          "moves": [
            "extremespeed",
            "spikes",
            "taunt",
            "knockoff"
          ],
          "baseAbility": "pressure",
          "item": "focussash",
          "pokeball": "pokeball",
          "ability": "pressure"
        }
      ]
    },
    "rqid": 8,
    "active": [
      {
        "moves": [
          {
            "move": "Calm Mind",
            "id": "calmmind",
            "pp": 32,
            "maxpp": 32,
            "target": "self",
            "disabled": False
          },
          {
            "move": "Morning Sun",
            "id": "morningsun",
            "pp": 8,
            "maxpp": 8,
            "target": "self",
            "disabled": False
          },
          {
            "move": "Photon Geyser",
            "id": "photongeyser",
            "pp": 8,
            "maxpp": 8,
            "target": "normal",
            "disabled": False
          },
          {
            "move": "Heat Wave",
            "id": "heatwave",
            "pp": 15,
            "maxpp": 16,
            "target": "allAdjacentFoes",
            "disabled": False
          }
        ],
        "canZMove": [
          None,
          None,
          {
            "move": "Light That Burns the Sky",
            "target": "normal"
          },
          None
        ]
      }
    ]
  }

if __name__ == '__main__':
  unittest.main()
