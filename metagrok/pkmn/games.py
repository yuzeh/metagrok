import json

import gevent

from metagrok import formats

from metagrok.games import api
from metagrok.pkmn import parser
from metagrok.showdown_stdio import Battle

class Game(api.BaseGame):
  def __init__(self, options = None, prog = None):
    super(Game, self).__init__()
    self.options = options or formats.default()
    self.prog = prog

  @property
  def num_players(self):
    return 2

  def play(self, p1, p2):
    blocks = []
    p1 = GamePlayer('p1', p1)
    p2 = GamePlayer('p2', p2)
    players = {p.name: p for p in [p1, p2]}

    battle = Battle(options = self.options, prog = self.prog)

    while True:
      block = battle.recv()
      blocks.append(block)
      for name, player in players.iteritems():
        for log in block[name + 'log']:
          player.update(log)

      if block['winner']:
        for name, player in players.iteritems():
          if block['winner'] == 'tie':
            player.end('tie')
          elif block['winner'] == name:
            player.end('winner')
          else:
            player.end('loser')
        break

      actions = {}
      for name, player in players.iteritems():
        for req in block[name + 'req']:
          action = player.request(req)
          if action:
            if name in actions:
              raise ValueError('Second action formed: ' + req)
            actions[name] = action

      for name, action in actions.items():
        actions[name] = action.get()

      battle.send(actions.get('p1'), actions.get('p2'))

    battle.close()

    return blocks

def Gen7RandomBattle(): return Game(formats.get('gen7randombattle'))
def FixedSeedGame(): return Game(formats.get('gen7fixedseed01abcdef'))

class GamePlayer(object):
  def __init__(self, name, player):
    self.name = name
    self.player = player
    self.last_request = None
    self.candidates = None
    self.last_sideupdate = ''

  def update(self, log):
    self.player.update('update', log)

  def end(self, result):
    self.player.update('end', result)

  def request(self, log):
    if not log:
      return
    _, cmd, arg = log.split('|', 2)

    requires_action = False

    if cmd == 'request':
      arg = json.loads(arg)
      self.player.update('request', arg)

      if not arg.get('wait'):
        if arg.get('teamPreview'):
          self.candidates = parser.team_preview_actions_singles()
        else:
          self.candidates = parser.parse_valid_actions(arg)
        self.player.update('candidates', self.candidates)
        self.last_request = arg

        if any(self.candidates):
          requires_action = True

    elif cmd == 'callback':
      assert 'trapped' in log, log
      self.candidates = parser.parse_valid_actions(self.last_request, True)
      self.player.update('candidates', self.candidates)
      if any(self.candidates):
        requires_action = True

    elif cmd == 'error':
      assert 'trapped' in arg, 'Error log does not have trapped: ' + log
      assert 'trapped' in self.last_sideupdate, 'Last sidereq: ' + self.last_sideupdate

    else:
      raise ValueError('Unknown cmd: ' + log)

    if cmd != 'error':
      self.last_sideupdate = log

    if requires_action:
      return self.player.action()

    return None
