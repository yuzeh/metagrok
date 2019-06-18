import collections
import logging
import sys

import gevent
import gevent.event
import gevent.queue

Message = collections.namedtuple('Message', 'opcode data')

_STOP_SENTINEL = object()
ROOT_SENTINEL = object()

_NO_ARG = object()

class State(object): pass

class Actor(object):
  def __init__(self, parent):
    assert isinstance(parent, Actor) or parent is ROOT_SENTINEL, 'Invalid parent'
    self._parent = parent
    self._inbox = gevent.queue.Queue()
    self._running = False
    self._stopped = False
    self._finalized = False
    self._logger = None
    self._s = State()

  def receive(self, message):
    raise NotImplementedError

  def stop(self):
    if not self._stopped:
      self._stopped = True
      self._inbox.put(_STOP_SENTINEL)
    else:
      self.log('stop called more than once', loglevel = logging.ERROR)

  def _on_stop(self):
    'Finalizes everything'
    self.on_stop()
    del self._parent
    del self._logger
    del self._s
    self._finalized = True

  def on_stop(self):
    pass

  def on_start(self):
    pass

  def send(self, message, data = _NO_ARG):
    '''
    - actor.send(opcode, data)
    - actor.send((opcode, data))
    '''
    if data is not _NO_ARG:
      opcode = message
    else:
      opcode, data = message

    if not isinstance(opcode, str):
      self.die('opcode [%r] is not a string', message)

    message = Message(opcode, data)
    self._inbox.put(message)

  @property
  def name(self):
    return repr(self)

  @property
  def is_root(self):
    return self._parent is ROOT_SENTINEL

  def main(self):
    assert self.is_root, 'main() can only be called from a root Actor'
    return self._start()

  def log(self, msg, *args, **kwargs):
    if 'loglevel' in kwargs:
      loglevel = kwargs['loglevel']
      del kwargs['loglevel']
    else:
      loglevel = logging.DEBUG

    if self._logger is None:
      self._logger = logging.getLogger(self.name)

    if self._logger.isEnabledFor(loglevel):
      self._logger.log(loglevel, msg, *args, **kwargs)

  def warn(self, msg, *args, **kwargs):
    kwargs['loglevel'] = logging.WARN
    return self.log(msg, *args, **kwargs)

  def error(self, msg, *args, **kwargs):
    kwargs['loglevel'] = logging.ERROR
    return self.log(msg, *args, **kwargs)

  def info(self, msg, *args, **kwargs):
    kwargs['loglevel'] = logging.INFO
    return self.log(msg, *args, **kwargs)

  def debug(self, msg, *args, **kwargs):
    kwargs['loglevel'] = logging.DEBUG
    return self.log(msg, *args, **kwargs)

  def trace(self, msg, *args, **kwargs):
    kwargs['loglevel'] = 5
    return self.log(msg, *args, **kwargs)

  def die(self, msg, *args, **kwargs):
    self.error(msg, *args, **kwargs)
    sys.exit(1)

  def spawn(self, cls, *args, **kwargs):
    actor = cls(self, *args, **kwargs)
    actor._start()
    return actor

  def join(self):
    self._greenlet.join()

  def _start(self):
    greenlet = gevent.spawn(_run, self)
    greenlet.link_exception(_handle_exc(self))
    self._greenlet = greenlet

def _run(actor):
  try:
    actor._running = True
    actor.log('entering on_start()', loglevel = 5)
    actor.on_start()
    actor.log('exiting on_start()', loglevel = 5)
    while actor._running:
      message = actor._inbox.get()
      if message is _STOP_SENTINEL:
        actor._running = False
      else:
        actor.log('received >> %s', message, loglevel = 5)
        actor.receive(message)
    actor.log('entering on_stop()')
    actor.on_stop()
    actor.log('exiting on_stop()')
  except:
    actor.die('Fuck this shit, I am outta here', exc_info = True)

def _handle_exc(actor):
  def rv(greenlet):
    try:
      greenlet.get()
    except:
      actor.die('Encountered error, quitting', exc_info = True)
  return rv
