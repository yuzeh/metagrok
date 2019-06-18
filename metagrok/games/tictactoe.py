import random
import itertools

import numpy as np

import gevent

import torch
import torch.nn as nn
import torch.nn.functional as F

from metagrok import config
from metagrok.games import api
from metagrok.torch_policy import TorchPolicy
from metagrok.torch_utils import masked_softmax

class Game(api.BaseGame):
  def __init__(self, dangerous = False, fix_ordering = False):
    'A serial tic-tac-toe simulator.'
    self._dangerous = dangerous
    self._fix_ordering = fix_ordering

  @property
  def num_players(self):
    return 2

  def play(self, first, second):
    players = {1: first, -1: second}
    for k, player in players.items():
      player.update('whoami', k)

    rv = {}
    rv['buf'] = buf = []

    state = np.zeros((3, 3), dtype = int)
    state_view = state.view()
    state_view.shape = (9,)

    order = 1, -1
    if not self._fix_ordering and random.random() > 0.5:
      order = -1, 1

    for turn, idx in enumerate(itertools.cycle(order)):
      player = players[idx]
      if self._dangerous:
        candidates = np.ones(9, dtype = bool)
      else:
        candidates = state_view == 0

      buf.append((state_view.copy().tolist(), candidates.astype(int).tolist()))
      player.update('state', state.copy() * idx)
      player.update('candidates', candidates)
      action = self.action(player)

      if state_view[action] != 0:
        assert self._dangerous
        ended = -idx
        break

      state_view[action] = idx

      # Check for winner
      ended = None # 0, -1, or 1 if game ended
      for row in _winning_positions:
        if all(state[entry] == idx for entry in row):
          # we have a winner!
          ended = idx

      if ended is None and turn == 8:
        ended = 0

      if ended is not None:
        break

    buf.append((state_view.copy().tolist(), None))
    rv['winner'] = ended

    for idx, player in players.items():
      if ended == 0:
        data = 'tie'
      elif idx == ended:
        data = 'winner'
      else:
        data = 'loser'
      player.update('end', data)

    return rv

class DangerousGame(Game):
  def __init__(self):
    super(DangerousGame, self).__init__(dangerous = True)

_winning_positions = [
    [(0, 0), (0, 1), (0, 2)],
    [(1, 0), (1, 1), (1, 2)],
    [(2, 0), (2, 1), (2, 2)],
    [(0, 0), (1, 0), (2, 0)],
    [(0, 1), (1, 1), (2, 1)],
    [(0, 2), (1, 2), (2, 2)],
    [(0, 0), (1, 1), (2, 2)],
    [(2, 0), (1, 1), (0, 2)],
]

class Policy(TorchPolicy):
  feat_size = 18

  def __init__(self):
    super(Policy, self).__init__()

    self.p_fc1 = nn.Linear(Policy.feat_size, 64)
    self.p_fc2 = nn.Linear(64, 64)
    self.p_fc3 = nn.Linear(64, 9)

    self.v_fc1 = nn.Linear(Policy.feat_size, 64)
    self.v_fc2 = nn.Linear(64, 64)
    self.v_fc3 = nn.Linear(64, 1)

  def extract(self, state, candidates):
    pp = (state == +1).flatten().astype(config.nt())
    pm = (state == -1).flatten().astype(config.nt())
    return dict(pp = pp, pm = pm, mask = np.asarray(candidates).astype(config.nt()))

  def forward(self, pp, pm, mask):
    xs = torch.cat((pp, pm), 1)

    p = xs
    p = F.relu(self.p_fc1(p))
    p = F.relu(self.p_fc2(p))
    p = self.p_fc3(p)
    p, lp = masked_softmax.apply(p, mask, dtype = config.tt())

    v = xs
    v = F.relu(self.v_fc1(v))
    v = F.relu(self.v_fc2(v))
    v = self.v_fc3(v)

    return v, p, lp

def main():
  import pprint
  from metagrok.games.cgpi import TorchBasePlayer

  config.set_cuda(False)

  game = Game(dangerous = True)
  policy = Policy()

  for i in range(4):
    p1 = TorchBasePlayer(policy, '%s-1' % i)
    p2 = TorchBasePlayer(policy, '%s-2' % i)
    pprint.pprint(game.play(p1, p2))

if __name__ == '__main__':
  main()
