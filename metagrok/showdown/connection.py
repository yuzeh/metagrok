import logging

import gevent

import websocket

from metagrok.showdown import actor

OPCODE_DATA = (websocket.ABNF.OPCODE_TEXT, websocket.ABNF.OPCODE_BINARY)
TIMEOUT_SECONDS = 5. # 5 seconds

class ShowdownConnection(actor.Actor):
  '''
  Handles websocket communication to a PS server.

  args:
    - [conf] host (default: 'localhost')
    - [conf] port (default: '8000')
  '''
  def __init__(self, parent, conf):
    super(ShowdownConnection, self).__init__(parent)
    self._url = 'ws://%s:%s/showdown/websocket' % (conf.host, conf.port)

  def on_start(self):
    self._s.ws = websocket.create_connection(self._url, timeout = TIMEOUT_SECONDS)
    self._s.closed = False
    self.send(('ping', None))

  def on_stop(self):
    self._s.closed = True
    self._s.ws.close()
    del self._s.ws

  def receive(self, message):
    opcode, data = message
    if opcode == 'ping':
      self.ping()
    elif opcode == 'pong':
      self._pong(*data)
    elif opcode == 'send':
      self._s.ws.send(data)
    else:
      raise ValueError('Unknown message: ' + repr(message))

  def ping(self):
    def func():
      if not self._finalized:
        try:
          result = self._recv()
          self.send(('pong', result))
        except websocket.WebSocketTimeoutException:
          self.send(('ping', None))
        except IOError:
          if not self._s.closed:
            raise
      else:
        self.log('Trying to ping while finalized', loglevel = logging.WARN)
    gevent.spawn(func)

  def _pong(self, opcode, data):
    if opcode in OPCODE_DATA and data is not None:
      self._parent.send(('command-from-server', data))

    if opcode == websocket.ABNF.OPCODE_CLOSE:
      self._parent.send('forced-socket-close', None)
    else:
      self.send(('ping', None))

  def _recv(self):
    try:
      frame = self._s.ws.recv_frame()
    except websocket.WebSocketException as e:
      if isinstance(e, websocket.WebSocketTimeoutException):
        raise
      else:
        return websocket.ABNF.OPCODE_CLOSE, None

    if not frame:
      self.die('Not a valid frame: %s', frame)
    elif frame.opcode in OPCODE_DATA:
      return frame.opcode, frame.data
    elif frame.opcode == websocket.ABNF.OPCODE_CLOSE:
      self._s.ws.send_close()
      return frame.opcode, None
    elif frame.opcode == websocket.ABNF.OPCODE_PING:
      self._s.ws.pong(frame.data)
      return frame.opcode, frame.data
    return frame.opcode, frame.data
