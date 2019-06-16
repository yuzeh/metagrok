from metagrok.battlelogs import BattleLogger
from metagrok.showdown import actor
from metagrok.pkmn import parser

'''
A battler is an actor that responds to these three messages:
  - update: an update to the state of the battle
  - request-action: a request for an action to be sent
  - end: signifies the end of a battle

The on_start() method should handle the start of the game.
'''

class BattleLoggingMixin(object):
  def _start_logging(self):
    self._s.logger = BattleLogger(self._gid, self._log_dir)

  def _stop_logging(self):
    self._s.logger.close()
    del self._s.logger

  def _battlelog(self, blob, **kwargs):
    self._s.logger.log(blob, **kwargs)

  def _result(self, opcode):
    self._s.logger.result(opcode)

class APIPlayerBattler(actor.Actor, BattleLoggingMixin):
  '''
  args:
    - [kwargs] roomid
    - [kwargs] player_ctor
    - [conf] log_dir
    - [conf] username
  '''
  def __init__(self, parent, roomid, player_ctor, conf):
    super(APIPlayerBattler, self).__init__(parent)
    self._gid = '%s.%s' % (conf.username, roomid)
    self._player = player_ctor(self._gid)
    self._log_dir = conf.log_dir

  def on_start(self):
    self._start_logging()
    self._s.ended = False
    self._s.updates = []

  def on_stop(self):
    self._stop_logging()
    del self._player

  def receive(self, msg):
    if msg.opcode == 'update':
      self._s.updates.append(msg.data)
      if not self._s.ended:
        self._player.update('update', msg.data)
    elif msg.opcode == 'request-action':
      if self._s.ended:
        self.warn('recv request-for-action for [%s] but battle ended', self._gid)
        return

      candidates, req = msg.data
      self._player.update('candidates', candidates)
      self._player.update('request', req)
      action = self._player.action().get()

      self._battlelog(self._player.blocks[-1])
      self._parent.send('forward-action', action)
    elif msg.opcode == 'end':
      self._player.update('end', msg.data)
      self._battlelog(self._player.blocks[-1])
      self._s.ended = True
    else:
      self.die('got unexpected message: %s', msg)

  def __repr__(self):
    return 'APIPlayerBattler(%s)' % self._gid
