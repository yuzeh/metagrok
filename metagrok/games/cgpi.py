import random

import numpy as np

import gevent.event

class BasePlayer(object):
  '''
  A Common Game Player Interface

  For simple games, it's useful to define a common interface by which games communicate
  to agents, so that implementing a player for testing is simpler.

  Game calls to `player.update`:
    - opcode == 'state' ==> data describes the whole state of the game for the next turn
    - opcode == 'candidates' ==> data describes a 1d list of valid candidates for the game
        next turn
    - opcode == 'end' ==> data is 'winner', 'loser', or 'tie'

  A valid action is an integer index of the candidates list where the value is truthy.
  '''
  def update(self, opcode, data):
    if opcode == 'state':
      self.state = data
    elif opcode == 'candidates':
      self.candidates = data
    elif opcode == 'end':
      self.result = data

  def create_player(self, gid):
    return PlayerDelegate(self)

  def destroy_player(self, player):
    assert player.underlying is self

  def batch_act(self):
    pass

class RandomBasePlayer(BasePlayer):
  def action(self):
    nonzeros = [i for i, z in enumerate(self.candidates) if z]
    rv = gevent.event.AsyncResult()
    rv.set(random.choice(nonzeros))
    return rv

class TorchBasePlayer(BasePlayer):
  '''
  For players that require a torch policy to make actions, we already have a well-established
  way of interacting with the environment which we can integrate here.

  The TorchPolicy#act takes in state and candidates, and returns a dictionary containing
    - probs
    - log_probs
    - value_pred
  Where the dimensionality of the variables is determined by the dimensionality of the
  candidates object.
  '''
  def __init__(self, policy, gid):
    self.gid = gid
    self.policy = policy
    self.blocks = []

  def action(self):
    rv = gevent.event.AsyncResult()

    def fn():
      result = self.policy.act(self.state, self.candidates)
      if isinstance(result, gevent.event.AsyncResult):
        result = result.get()
      action = np.random.choice(len(self.candidates), p = result['probs'])
      result['candidates'] = self.candidates
      result['state'] = self.state
      result['action'] = action
      self.blocks.append(result)
      rv.set(action)

    gevent.spawn(fn)

    return rv

class PlayerDelegate(object):
  def __init__(self, underlying):
    self.underlying = underlying

  def update(self, opcode, data):
    return self.underlying.update(opcode, data)

  def action(self):
    return self.underlying.action()
