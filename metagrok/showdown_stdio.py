import atexit
import copy
import json
import logging
import os
import select
import signal
import subprocess
import sys
import threading


DEFAULT_OPTIONS = {
  'formatid': 'gen7randombattle',
  'p1': {
    'name': 'p1',
  },
  'p2': {
    'name': 'p2',
  },
}

def _timeout():
  sys.stderr.write('Timeout occurred while reading from child process\n')
  sys.exit(1)

_all_pids = set()

@atexit.register
def shutdown():
  for pid in _all_pids:
    os.kill(pid, signal.SIGKILL)

class Battle(object):
  def __init__(self, options = DEFAULT_OPTIONS, prog = None, timeout_ok = False):
    self.logger = logging.getLogger(__name__)
    self.proc = subprocess.Popen(
      (prog, 'simulate-battle'),
      stdin = subprocess.PIPE,
      stdout = subprocess.PIPE,
      bufsize = 0,  # otherwise this doesn't play nicely with select
    )
    _all_pids.add(self.proc.pid)

    options = copy.deepcopy(options)
    p1 = options.pop('p1')
    p2 = options.pop('p2')

    self._send('>start {}'.format(json.dumps(options)))
    self._send('>player p1 {}'.format(json.dumps(p1)))
    self._send('>player p2 {}'.format(json.dumps(p2)))

    self._closed = False
    self._timeout_ok = timeout_ok

  def close(self):
    if not self._closed:
      os.kill(self.proc.pid, signal.SIGINT)
      self.proc.communicate()
      _all_pids.remove(self.proc.pid)
      self._closed = True

  def send(self, p1, p2):
    if p1:
      self._send('>p1 %s' % p1)
    if p2:
      self._send('>p2 %s' % p2)

  def _send(self, msg):
    self.logger.debug(msg)
    
    self.proc.stdin.write(msg.encode('utf-8'))
    self.proc.stdin.write(b'\n')

  def recv(self):
    '''
    Output: {
      "p1log": [ <logs that happened since last action> ]
      "p1req": [ "|request|..." ],
      "p2log": [ <logs that happened since last action> ],
      "p2req": [ "|request|..." ],
      "spectator": [ ... ],
      "omniscient": [ ... ],
      "winner": "p1" | "p2" | "tie" | "",
      "seed": None | [seed],
    }
    '''
    # Perform blocking reads until we've received either of the following:
    # - update, sideupdate, sideupdate, update
    # - sideupdate, sideupdate, update
    # - update, end
    messages = []
    block = dict(
        p1log = [],
        p1req = [],
        p2log = [],
        p2req = [],
        spectator = [],
        omniscient = [],
        winner = '',
        seed = None)

    while True:
      message = self._recv_message()
      if message[0] == 'update':
        messages.append(message[0])
        update = _parse_update(message[1:])
        block['p1log'].extend(update['p1'])
        block['p2log'].extend(update['p2'])
        block['spectator'].extend(update['spectator'])
        block['omniscient'].extend(update['omniscient'])
      elif message[0] == 'sideupdate':
        assert message[1] in {'p1', 'p2'}
        messages.append((message[0], message[1]))
        block[message[1] + 'req'].append(message[2])
      elif message[0] == 'end':
        messages.append(message[0])
        end = json.loads(message[1])
        p1 = end['p1']
        p2 = end['p2']
        winner_name = end['winner']
        if winner_name == p1:
          winner = 'p1'
        elif winner_name == p2:
          winner = 'p2'
        else:
          winner = winner_name
        block['winner'] = winner
        block['seed'] = end['seed']
      else:
        raise ValueError('Unknown message:\n---\n%s\n---' % '\n'.join(message))

      found = False
      self.logger.debug(messages)
      for term_seq in _TERM_SEQS:
        if messages[-len(term_seq):] == term_seq:
          found = True
          break

      if found:
        break

    return block

  def _recv_message(self):
    rv = []
    timeout = 3.0 if self._timeout_ok else 60.

    while True:
      r, _, _ = select.select([self.proc.stdout.fileno()], [], [], timeout)
      if self.proc.stdout.fileno() not in r:
        if not self._timeout_ok:
          _timeout()
        else:
          raise BattleInputIncomplete()

      line = self.proc.stdout.readline().decode('utf-8')
      self.logger.debug(repr(line))
      line = line.strip()
      if not line:
        break
      if not line.startswith('>') and not line.startswith('[slow battle]'):
        rv.append(line)

    return rv

  def _flush(self):
    self.proc.stdout.flush()

def _parse_update(update):
  logs = {k: [] for k in ['spectator', 'p1', 'p2', 'omniscient']}
  itr = iter(update)
  while True:
    try:
      line = next(itr)
      if line.startswith('|split|'):
        player = line[len('|split|'):]
        private = next(itr)
        public = next(itr)

        logs['omniscient'].append(private)
        logs['spectator'].append(public)
        for p in ['p1', 'p2']:
          if p == player:
            logs[p].append(private)
          else:
            logs[p].append(public)
      else:
        for k in logs:
          logs[k].append(line)
    except StopIteration:
      break
  return logs

_TERM_SEQS = [
  ['update', 'end'],
  [('sideupdate', 'p1'), ('sideupdate', 'p2'), 'update'],
  [('sideupdate', 'p2'), ('sideupdate', 'p1'), 'update'],
  [('sideupdate', 'p1'), ('sideupdate', 'p1')],
  [('sideupdate', 'p2'), ('sideupdate', 'p2')],
]

class BattleInputIncomplete(Exception): pass