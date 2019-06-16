import gevent

import json
import os

from metagrok import utils
from metagrok.pkmn import parser
from metagrok.showdown import actor
from metagrok.showdown import battler

class BattleRoom(actor.Actor):
  '''
  Handles the operation of a battle room:
    - relays ps-messages to the battler
    - contains minimal logic that determines when an action is required
    - forwards actions from the battler to the server
    - performs cleanup when the battle has ended

  args:
    - [kwargs] roomid
    - [kwargs] player_ctor
    - [kwargs] extra
    - [conf] username
    - [conf] pslog_dir (default: None)
    - [conf] timer     (default: False)
  '''
  def __init__(self, parent, roomid, player_ctor, extra, conf):
    super(BattleRoom, self).__init__(parent)
    self._roomid      = roomid
    self._player_ctor = player_ctor
    self.extra        = extra
    self._conf        = conf

    self._username    = conf.username
    self._pslog_dir   = conf.pslog_dir
    self._timer       = conf.timer
    self._wait_time_before_requesting_move_seconds = conf.wait_time_before_requesting_move_seconds

  def on_start(self):
    self._s.req  = None

    self._s.battler = self.spawn(battler.APIPlayerBattler,
      roomid = self._roomid,
      player_ctor = self._player_ctor,
      conf = self._conf,
    )
    if self._pslog_dir:
      utils.mkdir_p(self._pslog_dir)
      self._s.log_file = open(os.path.join(self._pslog_dir, '%s.pslog' % self._bid), 'w')
    else:
      self._s.log_file = None

    if self._timer:
      self._parent.send('send-to-room', ('/timer on', self._roomid))

  def on_stop(self):
    self._s.battler.stop()
    self._s.battler.join()
    del self._s.battler

    if self._s.log_file:
      self._s.log_file.close()
    del self._s.log_file

  def receive(self, msg):
    if msg.opcode == 'ps-message':
      self._handle_ps_message(msg.data)
    elif msg.opcode == 'forward-action':
      action = '/%s' % msg.data
      self._parent.send('send-to-room', (action, self._roomid))
    else:
      self.die('got unexpected message: %s', msg)

  @property
  def _bid(self):
    return '%s.%s' % (self._username, self._roomid)

  def _handle_ps_message(self, message):
    if self._s.log_file:
      self._s.log_file.write(message)
      self._s.log_file.write('\n')
      self._s.log_file.flush()

    self._s.battler.send('update', message)

    self._check_requires_action(message)
    self._check_battle_end(message)

  def _check_battle_end(self, message):
    result = None
    if message.startswith('|win'):
      winner = message.split('|', 2)[2]
      if self._username == winner:
        result = 'winner'
      else:
        result = 'loser'
    elif message == '|tie':
      result = 'tie'

    if result is not None:
      self.__leave(result)

  def __leave(self, result):
    self._parent.send('send-to-room', ('/leave ' + self._roomid, ''))
    self._parent.send('battle-ended', dict(roomid = self._roomid, result = result))
    self._s.battler.send('end', result)

  def _request_action(self, is_trapped = False):
    req = json.loads(self._s.req)
    if req.get('teamPreview'):
      candidates = parser.team_preview_actions_singles()
    else:
      candidates = parser.parse_valid_actions(req, is_trapped)

    def fn():
      if hasattr(self._s, 'battler'):
        self._s.battler.send('request-action', (candidates, req))
      else:
        self.warn('about to send request-action for [%s] but battle ended', self._roomid)

    gevent.spawn_later(self._wait_time_before_requesting_move_seconds, fn)

  def _check_requires_action(self, message):
    if message.startswith('|request') or message.startswith('|error'):
      _, cmd, arg = message.split('|', 2)
      if cmd == 'request':
        req = arg.strip()
        if req:
          parsed_req = json.loads(req)
          if not parsed_req.get('wait'):
            if parsed_req.get('teamPreview') or filter(None, parser.parse_valid_actions(parsed_req)):
              # This is a huge hack. We are expected to make a move on each request.
              # Unfortunately the state update messages come in after the request,
              # so we don't have access to the full state at the exact point the request
              # comes in.
              #
              # There's also no clear signal of when all the info for that turn has come in,
              # so we need to improvise. What we'll do wait a few seconds before actually making the
              # request for an action.
              self._s.req = req
              self._request_action()
      else: # cmd == 'error'
        is_trapped = 'trapped' in arg
        # Is this message telling us we are trapped?
        if is_trapped:
          self._request_action(is_trapped)
        else:
          self.error('I do not know how to process this: %s', message)
