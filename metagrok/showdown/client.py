import collections
import json
import logging

import gevent.queue
import requests

from metagrok import utils
from metagrok.showdown import actor
from metagrok.showdown.room import BattleRoom
from metagrok.showdown.battle_queue import BattleQueue
from metagrok.showdown.connection import ShowdownConnection

class Client(actor.Actor):
  '''Contains primitives to communicate with a Pokemon Showdown server.

  Features:
    - Username challenge-response handling (of non-registered users so far)
    - Battle challenge management
    - Battle room management

  args:
    - [conf] username
  '''
  def __init__(self, parent, conf):
    super(Client, self).__init__(parent)
    self._conf     = conf
    self._username = conf.username
    self._player_ctor = getattr(conf, 'player_ctor', None) # hack for accepting battles

    if self.is_root:
      self._battle_results_queue = gevent.queue.Queue()
    else:
      self._battle_results_queue = None

  def on_start(self):
    self._s.cxn = self.spawn(ShowdownConnection, conf = self._conf)
    self._s.bq = self.spawn(BattleQueue, conf = self._conf)
    self._s.battles = {}
    self._s.authed = False
    self._s.started_auth_attempt = False
    self._s.initialized = False
    self._s.pre_init_queue = []

    self._s.mm_queue = collections.deque()
    self._s.roomids = {}

    # Not strictly necessary but makes it easier to challenge
    self._send_to_server('/autojoin')

  def on_stop(self):
    for roomid in self._s.battles:
      self._battle_finalized(roomid)
    del self._s.battles

    self._s.bq.stop()
    self._s.bq.join()
    del self._s.bq

    self._s.cxn.stop()
    self._s.cxn.join()
    del self._s.cxn

  def receive(self, msg):
    if msg.opcode == 'command-from-server':
      for roomid, chunk in _parse_command(msg.data):
        self.debug('> %s%s', roomid, chunk)
        self._route_to_room(roomid, chunk)
    elif msg.opcode == 'ps-message':
      self._handle_ps_message(msg.data)
    elif msg.opcode == 'battle-ended':
      roomid = msg.data['roomid']
      result = msg.data['result']
      room = self._s.battles[roomid]
      msg = dict(
        username = self.username,
        roomid = roomid,
        id = room.extra['id'],
        result = result,
      )
      if self.is_root:
        self.queue.put(('battle-ended', msg))
      else:
        self._parent.send('battle-ended', msg)
    elif msg.opcode == 'send-to-room':
      payload, roomid = msg.data
      self._send_to_server(payload, roomid = roomid)
    elif msg.opcode == 'check-init':
      self._check_init()
    elif msg.opcode == 'challenge':
      self._bq_send(msg)
    elif msg.opcode == 'matchmaking':
      assert not self._conf.accept_challenges, 'Cannot accept challenges while in MM'
      self._s.mm_queue.append(msg.data)
      self._bq_send('matchmaking', msg.data)
    elif msg.opcode == 'forced-socket-close':
      msg = 'Forced socket close from websocket'
      self.log(msg, loglevel = logging.ERROR)
      if self.is_root:
        self.queue.put(('error', msg))
      else:
        self._parent.send('error', msg)
      self.stop()
    else:
      self.die('got unexpected message: %s', msg)

  @property
  def conf(self):
    return self._conf

  @property
  def username(self):
    return self._username

  @property
  def queue(self):
    assert self.is_root
    return self._battle_results_queue

  def _battle_finalized(self, roomid):
    'Called when a battle is finalized (fully finished).'
    self.log('closing battle [%s]', roomid)
    self._s.battles[roomid].stop()
    self._s.battles[roomid].join()
    del self._s.battles[roomid]
    self.log('closed battle [%s]', roomid)
    self._bq_send('battle-ended', None)

  def _battle_accepted(self, roomid):
    'Called when a battle has started between two players.'
    self._bq_send('battle-started', None)
    if self._s.mm_queue:
      data = self._s.mm_queue.popleft()
    else:
      data = {
        'player_ctor': self._player_ctor,
        'id': roomid,
      }
    room = self.spawn(BattleRoom,
      roomid = roomid,
      player_ctor = data['player_ctor'],
      conf = self._conf,
      extra = data,
    )
    self._s.battles[roomid] = room
    return room

  def _ready(self):
    return self._s.authed

  def _bq_send(self, *args):
    if self._s.initialized:
      self._s.bq.send(*args)
    else:
      self._s.pre_init_queue.append(args)

  def _check_init(self):
    if not self._s.initialized:
      self._s.initialized = True
      for args in self._s.pre_init_queue:
        self._bq_send(*args)
      self._s.pre_init_queue[:] = []

  def _route_to_room(self, roomid, chunk):
    if not roomid:
      handler = self
    elif roomid in self._s.battles:
      handler = self._s.battles[roomid]
    elif roomid.startswith('battle-') and chunk == '|init|battle':
      handler = self._battle_accepted(roomid)
    else:
      self.warn('recv msg [%s] for [%s] but room not initialized', chunk, roomid)
      handler = None

    if handler:
      handler.send('ps-message', chunk)

    if chunk == '|deinit':
      self._battle_finalized(roomid)

  def _handle_ps_message(self, message):
    if message.startswith('|nametaken'):
      self.die('name [%s] already exists, exitting', self._username)
    elif (message.startswith('|popup|Error: You need to make a move in')
      or message.startswith('|popup|Error: You need to wait until after making a move')):
      self._bq_send('search-cancelled-by-server', message)
    elif message.startswith('|updatechallenges'):
      self._bq_send('update-challenges', json.loads(message.split('|', 2)[2]))
    elif message.startswith('|challstr') or message.startswith('|updateuser'):
      self._handle_auth_message(message)
    elif message.startswith('|pm'):
      self.info(message)

  def _handle_auth_message(self, message):
    if message.startswith('|challstr'):
      if self._s.authed:
        self.die('received message [%s] but already authed', message)
      challstr = '|'.join(message.split('|')[2:])
      username = self._username
      assertion = _fetch_assertion_string(username, challstr)
      self._send_to_server('/trn %s,0,%s' % (username, assertion))
      self._s.started_auth_attempt = True
    elif message.startswith('|updateuser'):
      username = message.split('|')[2]
      if username.lower().startswith('guest '):
        if self._s.started_auth_attempt:
          self.die('attempted auth but received message [%s]', message)
        else:
          self._s.authed = False
      else:
        if not self._s.started_auth_attempt:
          self.die('did not attempt auth but was assigned username [%s]', username)
        elif username != self._username:
          self.die('auth succeeded but users do not match [%s, %s]', username, self._username)
        else:
          self._s.authed = True
          self.send('check-init', None)

  def _send_to_server(self, payload, roomid = ''):
    payload = '%s|%s' % (roomid, payload)
    self.debug('< %s', payload)
    self._s.cxn.send('send', payload)

  def __repr__(self):
    return 'Client(%s)' % self._username

def _parse_command(data):
  parts = [_f for _f in [part.strip() for part in data.split('\n')] if _f]
  if data.startswith('>'):
    roomid = parts[0][1:]
    chunks = parts[1:]
  else:
    roomid = ''
    chunks = parts

  for chunk in chunks:
    yield roomid, chunk.strip()

def _fetch_assertion_string(username, challstr):
  result = requests.post(
    'http://play.pokemonshowdown.com/action.php',
    data = dict(act = 'getassertion', userid = username, challstr = challstr),
  )
  return result.text

def wait(client, num_matches):
  assert client.is_root, 'Cannot wait on a non-root Client'
  for i in range(num_matches):
    yield client.queue.get()
