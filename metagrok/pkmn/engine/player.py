import random
import six

import gevent

import numpy as np

from metagrok import config

from metagrok.pkmn import parser
from metagrok.pkmn.engine.core import Engine

class EnginePkmnPlayer(object):
  def __init__(self, policy, gid, epsilon = 0., play_best_move = False):
    self.gid = gid
    self.policy = policy
    self.blocks = []
    self.request = None
    self.updates = []

    self.engine = _engine
    self.engine.start(self.gid)

    self._epsilon = epsilon
    self._play_best_move = play_best_move
    assert self._epsilon >= 0. and self._epsilon <= 1.

  def update(self, opcode, data):
    if opcode == 'update':
      self.updates.append(data)
      self.engine.update(self.gid, data)
    elif opcode == 'request':
      self.request = data
    elif opcode == 'candidates':
      self.candidates = data
    elif opcode == 'end':
      self.blocks.append(dict(result = data, _updates = self.updates))
      self.result = data
      self.engine.stop(self.gid)
      del self.engine
    else:
      raise ValueError('Unknown opcode: ' + opcode)

  def action(self):
    block_updates = self.updates
    self.updates = []

    rv = gevent.event.AsyncResult()
    def fn():
      state = self.engine.fetch(self.gid, self.request)
      if self.request.get('teamPreview') and self.candidates == 'teampreview':
        order = [str(i + 1) for i in range(self.request['maxTeamSize'])]
        random.shuffle(order)
        action_string = 'team ' + ','.join(order)
        result = dict(
          state = state,
          actionString = action_string,
          _updates = block_updates)
      else:
        result = self.policy.act(state, self.candidates)
        mask = np.asarray([1. if c else 0. for c in self.candidates])
        if isinstance(result, gevent.event.AsyncResult):
          result = result.get()
        probs = result['probs']
        probs = (1. - self._epsilon) * probs + (self._epsilon * mask / sum(mask)).astype(config.nt())
        if self._play_best_move:
          action = np.argmax(probs)
        else:
          action = np.random.choice(len(self.candidates), p = probs)

        # TODO: why not just use self.candidates?
        if self.request.get('teamPreview'):
          all_actions = _teampreview_actions
        else:
          all_actions = _singles_actions

        action_string = all_actions[action]
        result['candidates'] = self.candidates
        result['state'] = state
        result['action'] = action
        result['actionString'] = action_string
        result['_updates'] = block_updates
      self.blocks.append(result)
      rv.set(action_string)
    gevent.spawn(fn)
    return rv

_engine = Engine()
_singles_actions = parser.all_actions_singles()
_teampreview_actions = parser.team_preview_actions_singles()