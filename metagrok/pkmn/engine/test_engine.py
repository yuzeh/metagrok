import copy
import json
import unittest

from metagrok.pkmn.engine import core

update_with_request = core._update_with_request
get_side = core._get_side
postproc = core._postprocess_engine_state

class UpdateWithRequestTest(unittest.TestCase):
  def test_begin(self):
    state = copy.deepcopy(state_begin)
    postproc(state)
    update_with_request(state, req_begin)
    side = get_side(state, state['whoami'])

    poke = side['pokemon'][0]

    self.assertEqual('p2: Primeape', poke['ident'])
    self.assertEqual(244., poke['maxhp'])
    self.assertEqual(244., poke['hp'])
    self.assertEqual(
        [('icepunch', 0), ('uturn', 0), ('encore', 0), ('closecombat', 0)],
        map(tuple, poke['moveTrack']))
    self.assertEqual('lifeorb', poke['item'])
    self.assertEqual('vitalspirit', poke['ability'])
    self.assertEqual('vitalspirit', poke['baseAbility'])
    self.assertEqual(True, poke['active'])
    self.assertEqual(False, poke['fainted'])

    poke = side['pokemon'][1]

    self.assertEqual('p2: Zoroark', poke['ident'])
    self.assertEqual(222., poke['maxhp'])
    self.assertEqual(222., poke['hp'])
    self.assertEqual(
        [('flamethrower', 0), ('nastyplot', 0), ('suckerpunch', 0), ('darkpulse', 0)],
        map(tuple, poke['moveTrack']))
    self.assertEqual('lifeorb', poke['item'])
    self.assertEqual('illusion', poke['ability'])
    self.assertEqual('illusion', poke['baseAbility'])
    self.assertEqual(False, poke['active'])
    self.assertEqual(False, poke['fainted'])

  def test_zoroark_switchin(self):
    state = copy.deepcopy(state_zoroark_switch)
    postproc(state)
    update_with_request(state, req_zoroark_switch)

state_begin = json.loads(r'''{
  "turn": 1,
  "ended": false,
  "usesUpkeep": false,
  "weather": "",
  "pseudoWeather": [],
  "weatherTimeLeft": 0,
  "weatherMinTimeLeft": 0,
  "mySide": {
    "battle": {
      "$ref": "$"
    },
    "name": "metagrok-random",
    "id": "metagrokrandom",
    "initialized": true,
    "n": 0,
    "foe": {
      "battle": {
        "$ref": "$"
      },
      "name": "borrel-ahorse",
      "id": "borrelahorse",
      "initialized": true,
      "n": 1,
      "foe": {
        "$ref": "$[\"mySide\"]"
      },
      "totalPokemon": 6,
      "sideConditions": {},
      "wisher": null,
      "active": [
        {
          "name": "Primeape",
          "species": "Primeape",
          "searchid": "p2: Primeape|Primeape, L83, M",
          "side": {
            "$ref": "$[\"mySide\"][\"foe\"]"
          },
          "fainted": false,
          "hp": 244,
          "maxhp": 244,
          "ability": "",
          "baseAbility": "",
          "item": "",
          "itemEffect": "",
          "prevItem": "",
          "prevItemEffect": "",
          "boosts": {},
          "status": "",
          "volatiles": {},
          "turnstatuses": {},
          "movestatuses": {},
          "lastmove": "",
          "moveTrack": [],
          "statusData": {
            "sleepTurns": 0,
            "toxicTurns": 0
          },
          "num": 57,
          "types": [
            "Fighting"
          ],
          "baseStats": {
            "hp": 65,
            "atk": 105,
            "def": 60,
            "spa": 60,
            "spd": 70,
            "spe": 95
          },
          "abilities": {
            "0": "Vital Spirit",
            "1": "Anger Point",
            "H": "Defiant"
          },
          "heightm": 1,
          "weightkg": 32,
          "color": "Brown",
          "prevo": "mankey",
          "evoLevel": 28,
          "eggGroups": [
            "Field"
          ],
          "exists": true,
          "id": "primeape",
          "speciesid": "primeape",
          "baseSpecies": "Primeape",
          "forme": "",
          "formeLetter": "",
          "formeid": "",
          "spriteid": "primeape",
          "effectType": "Template",
          "gen": 1,
          "slot": 0,
          "details": "Primeape, L83, M",
          "ident": "p2: Primeape",
          "level": 83,
          "gender": "M",
          "shiny": false
        }
      ],
      "lastPokemon": null,
      "pokemon": [
        {
          "$ref": "$[\"mySide\"][\"foe\"][\"active\"][0]"
        }
      ]
    },
    "totalPokemon": 6,
    "sideConditions": {},
    "wisher": null,
    "active": [
      {
        "name": "Reshiram",
        "species": "Reshiram",
        "searchid": "p1: Reshiram|Reshiram, L73",
        "side": {
          "$ref": "$[\"mySide\"]"
        },
        "fainted": false,
        "hp": 100,
        "maxhp": 100,
        "ability": "Turboblaze",
        "baseAbility": "Turboblaze",
        "item": "",
        "itemEffect": "",
        "prevItem": "",
        "prevItemEffect": "",
        "boosts": {},
        "status": "",
        "volatiles": {},
        "turnstatuses": {},
        "movestatuses": {},
        "lastmove": "",
        "moveTrack": [],
        "statusData": {
          "sleepTurns": 0,
          "toxicTurns": 0
        },
        "num": 643,
        "types": [
          "Dragon",
          "Fire"
        ],
        "gender": "",
        "baseStats": {
          "hp": 100,
          "atk": 120,
          "def": 100,
          "spa": 150,
          "spd": 120,
          "spe": 90
        },
        "abilities": {
          "0": "Turboblaze"
        },
        "heightm": 3.2,
        "weightkg": 330,
        "color": "White",
        "eggGroups": [
          "Undiscovered"
        ],
        "exists": true,
        "id": "reshiram",
        "speciesid": "reshiram",
        "baseSpecies": "Reshiram",
        "forme": "",
        "formeLetter": "",
        "formeid": "",
        "spriteid": "reshiram",
        "effectType": "Template",
        "gen": 5,
        "slot": 0,
        "details": "Reshiram, L73",
        "ident": "p1: Reshiram",
        "level": 73,
        "shiny": false
      }
    ],
    "lastPokemon": null,
    "pokemon": [
      {
        "$ref": "$[\"mySide\"][\"active\"][0]"
      }
    ]
  },
  "yourSide": {
    "$ref": "$[\"mySide\"][\"foe\"]"
  },
  "p1": {
    "$ref": "$[\"mySide\"]"
  },
  "p2": {
    "$ref": "$[\"mySide\"][\"foe\"]"
  },
  "sides": [
    {
      "$ref": "$[\"mySide\"]"
    },
    {
      "$ref": "$[\"mySide\"][\"foe\"]"
    }
  ],
  "lastMove": "",
  "gen": 7,
  "speciesClause": true,
  "gameType": "singles",
  "tier": "[Gen 7] Random Battle",
  "lastmove": "switch-in"
}''')

req_begin = json.loads('''{
  "active": [
    {
      "moves": [
        {
          "move": "Ice Punch",
          "id": "icepunch",
          "pp": 24,
          "maxpp": 24,
          "target": "normal",
          "disabled": false
        },
        {
          "move": "U-turn",
          "id": "uturn",
          "pp": 32,
          "maxpp": 32,
          "target": "normal",
          "disabled": false
        },
        {
          "move": "Encore",
          "id": "encore",
          "pp": 8,
          "maxpp": 8,
          "target": "normal",
          "disabled": false
        },
        {
          "move": "Close Combat",
          "id": "closecombat",
          "pp": 8,
          "maxpp": 8,
          "target": "normal",
          "disabled": false
        }
      ]
    }
  ],
  "side": {
    "name": "borrel-ahorse",
    "id": "p2",
    "pokemon": [
      {
        "ident": "p2: Primeape",
        "details": "Primeape, L83, M",
        "condition": "244/244",
        "active": true,
        "stats": {
          "atk": 222,
          "def": 147,
          "spa": 147,
          "spd": 164,
          "spe": 205
        },
        "moves": [
          "icepunch",
          "uturn",
          "encore",
          "closecombat"
        ],
        "baseAbility": "vitalspirit",
        "item": "lifeorb",
        "pokeball": "pokeball",
        "ability": "vitalspirit"
      },
      {
        "ident": "p2: Zoroark",
        "details": "Zoroark, L78, F",
        "condition": "222/222",
        "active": false,
        "stats": {
          "atk": 209,
          "def": 139,
          "spa": 232,
          "spd": 139,
          "spe": 209
        },
        "moves": [
          "flamethrower",
          "nastyplot",
          "suckerpunch",
          "darkpulse"
        ],
        "baseAbility": "illusion",
        "item": "lifeorb",
        "pokeball": "pokeball",
        "ability": "illusion"
      },
      {
        "ident": "p2: Shiftry",
        "details": "Shiftry, L83, M",
        "condition": "285/285",
        "active": false,
        "stats": {
          "atk": 214,
          "def": 147,
          "spa": 197,
          "spd": 147,
          "spe": 180
        },
        "moves": [
          "swordsdance",
          "leafblade",
          "lowkick",
          "suckerpunch"
        ],
        "baseAbility": "earlybird",
        "item": "lifeorb",
        "pokeball": "pokeball",
        "ability": "earlybird"
      },
      {
        "ident": "p2: Tornadus",
        "details": "Tornadus, L78, M",
        "condition": "251/251",
        "active": false,
        "stats": {
          "atk": 184,
          "def": 154,
          "spa": 240,
          "spd": 170,
          "spe": 218
        },
        "moves": [
          "tailwind",
          "heatwave",
          "taunt",
          "hurricane"
        ],
        "baseAbility": "prankster",
        "item": "leftovers",
        "pokeball": "pokeball",
        "ability": "prankster"
      },
      {
        "ident": "p2: Steelix",
        "details": "Steelix, L79, F",
        "condition": "248/248",
        "active": false,
        "stats": {
          "atk": 180,
          "def": 362,
          "spa": 132,
          "spd": 148,
          "spe": 93
        },
        "moves": [
          "stealthrock",
          "earthquake",
          "toxic",
          "dragontail"
        ],
        "baseAbility": "sturdy",
        "item": "steelixite",
        "pokeball": "pokeball",
        "ability": "sturdy"
      },
      {
        "ident": "p2: Scrafty",
        "details": "Scrafty, L81, F",
        "condition": "238/238",
        "active": false,
        "stats": {
          "atk": 192,
          "def": 233,
          "spa": 120,
          "spd": 233,
          "spe": 141
        },
        "moves": [
          "rest",
          "highjumpkick",
          "dragondance",
          "icepunch"
        ],
        "baseAbility": "intimidate",
        "item": "chestoberry",
        "pokeball": "pokeball",
        "ability": "intimidate"
      }
    ]
  },
  "rqid": 3
}''')

state_zoroark_switch = json.loads(r'''{"turn":9,"ended":false,"usesUpkeep":true,"weather":"","p
seudoWeather":[],"weatherTimeLeft":0,"weatherMinTimeLeft":0,"mySide":{"battle":{"$ref":"$"},"na
me":"metagrok-random","id":"metagrokrandom","initialized":true,"n":0,"foe":{"battle":{"$ref":"$
"},"name":"borrel-ahorse","id":"borrelahorse","initialized":true,"n":1,"foe":{"$ref":"$[\"mySid
e\"]"},"totalPokemon":6,"sideConditions":{},"wisher":null,"active":[{"name":"Steelix","species"
:"Steelix","searchid":"p2: Steelix|Steelix, L79, F","side":{"$ref":"$[\"mySide\"][\"foe\"]"},"f
ainted":false,"hp":222,"maxhp":222,"ability":"","baseAbility":"","item":"","itemEffect":"","pre
vItem":"","prevItemEffect":"","boosts":{},"status":"","volatiles":{},"turnstatuses":{},"movesta
tuses":{},"lastmove":"","moveTrack":[],"statusData":{"sleepTurns":0,"toxicTurns":0},"num":208,"
types":["Steel","Ground"],"baseStats":{"hp":75,"atk":85,"def":200,"spa":55,"spd":65,"spe":30},"
abilities":{"0":"Rock Head","1":"Sturdy","H":"Sheer Force"},"heightm":9.2,"weightkg":400,"color
":"Gray","prevo":"onix","evoLevel":1,"eggGroups":["Mineral"],"otherFormes":["steelixmega"],"exi
sts":true,"id":"steelix","speciesid":"steelix","baseSpecies":"Steelix","forme":"","formeLetter"
:"","formeid":"","spriteid":"steelix","effectType":"Template","gen":2,"slot":0,"details":"Steel
ix, L79, F","ident":"p2: Steelix","level":79,"gender":"F","shiny":false}],"lastPokemon":{"name"
:"Scrafty","species":"Scrafty","searchid":"p2: Scrafty|Scrafty, L81, F","side":{"$ref":"$[\"myS
ide\"][\"foe\"]"},"fainted":true,"hp":0,"maxhp":238,"ability":"","baseAbility":"","item":"","it
emEffect":"","prevItem":"","prevItemEffect":"","boosts":{},"status":"","volatiles":{},"turnstat
uses":{},"movestatuses":{},"lastmove":"highjumpkick","moveTrack":[["Rest",2],["Dragon Dance",2]
,["Ice Punch",1],["High Jump Kick",1]],"statusData":{"sleepTurns":0,"toxicTurns":0},"num":560,"
types":["Dark","Fighting"],"baseStats":{"hp":65,"atk":90,"def":115,"spa":45,"spd":115,"spe":58}
,"abilities":{"0":"Shed Skin","1":"Moxie","H":"Intimidate"},"heightm":1.1,"weightkg":30,"color"
:"Red","prevo":"scraggy","evoLevel":39,"eggGroups":["Field","Dragon"],"exists":true,"id":"scraf
ty","speciesid":"scrafty","baseSpecies":"Scrafty","forme":"","formeLetter":"","formeid":"","spr
iteid":"scrafty","effectType":"Template","gen":5,"slot":0,"details":"Scrafty, L81, F","ident":"
p2: Scrafty","level":81,"gender":"F","shiny":false},"pokemon":[{"name":"Primeape","species":"Pr
imeape","searchid":"p2: Primeape|Primeape, L83, M","side":{"$ref":"$[\"mySide\"][\"foe\"]"},"fa
inted":true,"hp":0,"maxhp":244,"ability":"","baseAbility":"","item":"Life Orb","itemEffect":"",
"prevItem":"","prevItemEffect":"","boosts":{},"status":"","volatiles":{},"turnstatuses":{},"mov
estatuses":{},"lastmove":"closecombat","moveTrack":[["Ice Punch",1],["Close Combat",1]],"status
Data":{"sleepTurns":0,"toxicTurns":0},"num":57,"types":["Fighting"],"baseStats":{"hp":65,"atk":
105,"def":60,"spa":60,"spd":70,"spe":95},"abilities":{"0":"Vital Spirit","1":"Anger Point","H":
"Defiant"},"heightm":1,"weightkg":32,"color":"Brown","prevo":"mankey","evoLevel":28,"eggGroups"
:["Field"],"exists":true,"id":"primeape","speciesid":"primeape","baseSpecies":"Primeape","forme
":"","formeLetter":"","formeid":"","spriteid":"primeape","effectType":"Template","gen":1,"slot"
:0,"details":"Primeape, L83, M","ident":"p2: Primeape","level":83,"gender":"M","shiny":false},{
"$ref":"$[\"mySide\"][\"foe\"][\"lastPokemon\"]"},{"$ref":"$[\"mySide\"][\"foe\"][\"active\"][0
]"}]},"totalPokemon":6,"sideConditions":{},"wisher":null,"active":[{"name":"Huntail","species":
"Huntail","searchid":"p1: Huntail|Huntail, L83, F","side":{"$ref":"$[\"mySide\"]"},"fainted":fa
lse,"hp":5,"maxhp":100,"ability":"","baseAbility":"","item":"","itemEffect":"","prevItem":"","p
revItemEffect":"","boosts":{},"status":"","volatiles":{},"turnstatuses":{},"movestatuses":{},"l
astmove":"waterfall","moveTrack":[["Waterfall",1]],"statusData":{"sleepTurns":0,"toxicTurns":0}
,"num":367,"types":["Water"],"baseStats":{"hp":55,"atk":104,"def":105,"spa":94,"spd":75,"spe":5
2},"abilities":{"0":"Swift Swim","H":"Water Veil"},"heightm":1.7,"weightkg":27,"color":"Blue","
prevo":"clamperl","evoLevel":1,"eggGroups":["Water 1"],"exists":true,"id":"huntail","speciesid"
:"huntail","baseSpecies":"Huntail","forme":"","formeLetter":"","formeid":"","spriteid":"huntail
","effectType":"Template","gen":3,"slot":0,"details":"Huntail, L83, F","ident":"p1: Huntail","l
evel":83,"gender":"F","shiny":false}],"lastPokemon":{"name":"Krookodile","species":"Krookodile"
,"searchid":"p1: Krookodile|Krookodile, L77, M","side":{"$ref":"$[\"mySide\"]"},"fainted":false
,"hp":91,"maxhp":100,"ability":"","baseAbility":"","item":"Life Orb","itemEffect":"","prevItem"
:"","prevItemEffect":"","boosts":{},"status":"","volatiles":{},"turnstatuses":{},"movestatuses"
:{},"lastmove":"superpower","moveTrack":[["Superpower",1]],"statusData":{"sleepTurns":0,"toxicT
urns":0},"num":553,"types":["Ground","Dark"],"baseStats":{"hp":95,"atk":117,"def":80,"spa":65,"
spd":70,"spe":92},"abilities":{"0":"Intimidate","1":"Moxie","H":"Anger Point"},"heightm":1.5,"w
eightkg":96.3,"color":"Red","prevo":"krokorok","evoLevel":40,"eggGroups":["Field"],"exists":tru
e,"id":"krookodile","speciesid":"krookodile","baseSpecies":"Krookodile","forme":"","formeLetter
":"","formeid":"","spriteid":"krookodile","effectType":"Template","gen":5,"slot":0,"details":"K
rookodile, L77, M","ident":"p1: Krookodile","level":77,"gender":"M","shiny":false},"pokemon":[{
"name":"Reshiram","species":"Reshiram","searchid":"p1: Reshiram|Reshiram, L73","side":{"$ref":"
$[\"mySide\"]"},"fainted":true,"hp":0,"maxhp":100,"ability":"Turboblaze","baseAbility":"Turbobl
aze","item":"Leftovers","itemEffect":"","prevItem":"","prevItemEffect":"","boosts":{},"status":
"","volatiles":{},"turnstatuses":{},"movestatuses":{},"lastmove":"","moveTrack":[["Blue Flare",
1],["Flame Charge",1]],"statusData":{"sleepTurns":0,"toxicTurns":0},"num":643,"types":["Dragon"
,"Fire"],"gender":"","baseStats":{"hp":100,"atk":120,"def":100,"spa":150,"spd":120,"spe":90},"a
bilities":{"0":"Turboblaze"},"heightm":3.2,"weightkg":330,"color":"White","eggGroups":["Undisco
vered"],"exists":true,"id":"reshiram","speciesid":"reshiram","baseSpecies":"Reshiram","forme":"
","formeLetter":"","formeid":"","spriteid":"reshiram","effectType":"Template","gen":5,"slot":0,
"details":"Reshiram, L73","ident":"p1: Reshiram","level":73,"shiny":false},{"name":"Grumpig","s
pecies":"Grumpig","searchid":"p1: Grumpig|Grumpig, L83, F","side":{"$ref":"$[\"mySide\"]"},"fai
nted":false,"hp":100,"maxhp":100,"ability":"","baseAbility":"","item":"","itemEffect":"","prevI
tem":"","prevItemEffect":"","boosts":{},"status":"","volatiles":{},"turnstatuses":{},"movestatu
ses":{},"lastmove":"","moveTrack":[],"statusData":{"sleepTurns":0,"toxicTurns":0},"num":326,"ty
pes":["Psychic"],"baseStats":{"hp":80,"atk":45,"def":65,"spa":90,"spd":110,"spe":80},"abilities
":{"0":"Thick Fat","1":"Own Tempo","H":"Gluttony"},"heightm":0.9,"weightkg":71.5,"color":"Purpl
e","prevo":"spoink","evoLevel":32,"eggGroups":["Field"],"exists":true,"id":"grumpig","speciesid
":"grumpig","baseSpecies":"Grumpig","forme":"","formeLetter":"","formeid":"","spriteid":"grumpi
g","effectType":"Template","gen":3,"slot":0,"details":"Grumpig, L83, F","ident":"p1: Grumpig","
level":83,"gender":"F","shiny":false},{"$ref":"$[\"mySide\"][\"lastPokemon\"]"},{"$ref":"$[\"my
Side\"][\"active\"][0]"}]},"yourSide":{"$ref":"$[\"mySide\"][\"foe\"]"},"p1":{"$ref":"$[\"mySid
e\"]"},"p2":{"$ref":"$[\"mySide\"][\"foe\"]"},"sides":[{"$ref":"$[\"mySide\"]"},{"$ref":"$[\"my
Side\"][\"foe\"]"}],"lastMove":"","gen":7,"speciesClause":true,"gameType":"singles","tier":"[Ge
n 7] Random Battle","lastmove":"switch-in"}
'''.replace('\n', '').replace('\r', ''))

req_zoroark_switch = json.loads(r'''{"active":[{"moves":[{"move":"Flamethrower","id":"flamethro
wer","pp":24,"maxpp":24,"target":"normal","disabled":false},{"move":"Nasty Plot","id":"nastyplo
t","pp":32,"maxpp":32,"target":"self","disabled":false},{"move":"Sucker Punch","id":"suckerpunc
h","pp":8,"maxpp":8,"target":"normal","disabled":false},{"move":"Dark Pulse","id":"darkpulse","
pp":24,"maxpp":24,"target":"any","disabled":false}]}],"side":{"name":"borrel-ahorse","id":"p2",
"pokemon":[{"ident":"p2: Zoroark","details":"Zoroark, L78, F","condition":"222/222","active":tr
ue,"stats":{"atk":209,"def":139,"spa":232,"spd":139,"spe":209},"moves":["flamethrower","nastypl
ot","suckerpunch","darkpulse"],"baseAbility":"illusion","item":"lifeorb","pokeball":"pokeball",
"ability":"illusion"},{"ident":"p2: Scrafty","details":"Scrafty, L81, F","condition":"0 fnt","a
ctive":false,"stats":{"atk":192,"def":233,"spa":120,"spd":233,"spe":141},"moves":["rest","highj
umpkick","dragondance","icepunch"],"baseAbility":"intimidate","item":"chestoberry","pokeball":"
pokeball","ability":"intimidate"},{"ident":"p2: Shiftry","details":"Shiftry, L83, M","condition
":"285/285","active":false,"stats":{"atk":214,"def":147,"spa":197,"spd":147,"spe":180},"moves":
["swordsdance","leafblade","lowkick","suckerpunch"],"baseAbility":"earlybird","item":"lifeorb",
"pokeball":"pokeball","ability":"earlybird"},{"ident":"p2: Tornadus","details":"Tornadus, L78, 
M","condition":"251/251","active":false,"stats":{"atk":184,"def":154,"spa":240,"spd":170,"spe":
218},"moves":["tailwind","heatwave","taunt","hurricane"],"baseAbility":"prankster","item":"left
overs","pokeball":"pokeball","ability":"prankster"},{"ident":"p2: Steelix","details":"Steelix, 
L79, F","condition":"248/248","active":false,"stats":{"atk":180,"def":362,"spa":132,"spd":148,"
spe":93},"moves":["stealthrock","earthquake","toxic","dragontail"],"baseAbility":"sturdy","item
":"steelixite","pokeball":"pokeball","ability":"sturdy"},{"ident":"p2: Primeape","details":"Pri
meape, L83, M","condition":"0 fnt","active":false,"stats":{"atk":222,"def":147,"spa":147,"spd":
164,"spe":205},"moves":["icepunch","uturn","encore","closecombat"],"baseAbility":"vitalspirit",
"item":"lifeorb","pokeball":"pokeball","ability":"vitalspirit"}]},"rqid":25}
'''.replace('\n', '').replace('\r', ''))

if __name__ == '__main__':
  unittest.main()
