import gevent.event
import gevent.util

from metagrok import utils
from metagrok.games import api

import actor
from client import Client, wait

assert wait
assert Client

class MatchmakingGame(actor.Actor, api.BaseGame):
  '''
  Note: This api.Game API operates on Player constructors, i.e. functions that create
  player objects when called with a single argument.

  As such, this game cannot be batch run (i.e. does not work with the batch API).
  '''
  def __init__(self, conf, fmt = 'gen7randombattle', team = None):
    actor.Actor.__init__(self, actor.ROOT_SENTINEL)
    assert not conf.accept_challenges, 'Cannot run matchmaking player that accepts challenges'
    self._conf = conf
    self._fmt = fmt
    self._team = team
  
  def on_start(self):
    self._s.client = self.spawn(Client, self._conf)
    self._s.counter = 0
    self._s.id_to_result = {}

  def receive(self, msg):
    if msg.opcode == 'battle-ended':
      id = msg.data['id']
      result = self._s.id_to_result.pop(id)
      result.set(msg.data)
    else:
      self.die('got unexpected message: %s', msg)

  @property
  def batch_playable(self):
    return False

  @property
  def num_players(self):
    return 1

  def play(self, player_ctor):
    id = self._s.counter
    self._s.counter += 1
    msg = dict(fmt = self._fmt, player_ctor = player_ctor, id = id, team = self._team)
    result = gevent.event.AsyncResult()
    self._s.id_to_result[id] = result
    self._s.client.send('matchmaking', msg)
    return result.get()
