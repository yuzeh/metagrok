import numpy as np

import torch.nn as nn

import gevent

from metagrok import config
from metagrok.torch_policy import TorchPolicy
from metagrok.torch_utils import masked_softmax

from metagrok.games import api

ACTIONS = ['left', 'right']

class Game(api.BaseGame):
  @property
  def num_players(self):
    return 1

  def play(self, player):
    state = 0
    history = [state]
    actions = []
    while abs(state) < 3:
      player.update('candidates', ACTIONS)
      player.update('state', state)
      action = self.action(player)
      action = ACTIONS[action]
      if action == 'left':
        state -= 1
      else:
        state += 1
      actions.append(action)
      history.append(state)

    result = 'winner' if state > 0 else 'loser'
    player.update('end', result)

    return dict(result = result, history = history, actions = actions)

class Policy(TorchPolicy):
  def __init__(self):
    super(Policy, self).__init__()
    self.fc1 = nn.Linear(1, 10)
    self.fc2 = nn.Linear(10, 2)
    self.value1 = nn.Linear(1, 1)

  def extract(self, state, candidates):
    mask = np.asarray([float(bool(c)) for c in candidates]).astype(config.nt())
    state = np.asarray([state]).astype(config.nt())
    return dict(state = state, mask = mask)

  def forward(self, state, mask):
    vp = self.value1(state)
    xs = self.fc1(state)
    xs = self.fc2(xs)

    p, lp = masked_softmax.apply(xs, mask)
    return vp, p, lp

def main():
  import pprint
  from metagrok.games.cgpi import TorchBasePlayer

  config.set_cuda(False)

  game = Game()
  policy = Policy()

  for i in range(4):
    player = TorchBasePlayer(policy, str(i))
    pprint.pprint(game.play(player))

if __name__ == '__main__':
  main()
