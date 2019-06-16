import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F

from metagrok import config
from metagrok import utils
from metagrok.pkmn import parser
from metagrok.pkmn.models import psc
from metagrok.torch_utils import masked_softmax, zeros
from metagrok.torch_policy import TorchPolicy

from metagrok import np_json as json

_test_features = json.load('static/v1_repro.features.json')

class Policy(TorchPolicy):
  '''A reproduction of the CompactPkmnPolicy network.'''
  permutation = parser.make_permutation([
      'move 1', 'move 2', 'move 3', 'move 4',
      'move 1 mega', 'move 2 mega', 'move 3 mega', 'move 4 mega',
      'move 1 ultra', 'move 2 ultra', 'move 3 ultra', 'move 4 ultra',
      'move 1 zmove', 'move 2 zmove', 'move 3 zmove', 'move 4 zmove',
      'switch 1', 'switch 2', 'switch 3', 'switch 4', 'switch 5', 'switch 6',
  ])
  extractor = psc.make_basic_extractor()

  def __init__(self, dense_width = 64):
    super(Policy, self).__init__()
    example = self.extractor.extract(_test_features)

    pokemon_size = example['player']['pokemon'].shape[1]
    sideConditions_size = example['player']['sideConditions'].shape[0]
    weather_size = example['weather'].shape[0]
    weatherTimeLeft_size = example['weatherTimeLeft'].shape[0]

    self.n_teammates = 6
    self.n_active, self.n_moves, move_size = example['moves'].shape

    self.pokemon_fc1 = nn.Linear(pokemon_size, dense_width)
    self.pokemon_fc2 = nn.Linear(dense_width, dense_width)
    self.active_fc2 = nn.Linear(dense_width, dense_width)

    self.team_fc1 = nn.Linear(2 * dense_width + sideConditions_size, dense_width)
    self.player_fc2 = nn.Linear(dense_width, dense_width)
    self.opponent_fc2 = nn.Linear(dense_width, dense_width)

    self.common_fc1 = nn.Linear(2 * dense_width + weather_size + weatherTimeLeft_size, dense_width)

    self.policy_move_fc1 = nn.Linear(dense_width + move_size, dense_width)
    self.policy_zmove_fc1 = nn.Linear(dense_width + move_size, dense_width)
    self.policy_switch_fc1 = nn.Linear(dense_width + dense_width, dense_width)
    self.policy_move_mod_fc1 = nn.Linear(dense_width, dense_width)

    self.policy_move_fc2 = nn.Linear(dense_width, 1)
    self.policy_zmove_fc2 = nn.Linear(dense_width, 1)
    self.policy_switch_fc2 = nn.Linear(dense_width, 1)

    # 0 - no mod
    # 1 - mega
    # 2 - ultra
    self.policy_move_mod_fc2 = nn.Linear(dense_width, 3)

    self.value_fc1 = nn.Linear(dense_width, dense_width)
    self.value_fc2 = nn.Linear(dense_width, 1)

  def extract(self, state, candidates):
    rv = self.extractor.extract(state)
    mask = np.asarray([float(bool(c)) for c in candidates])
    rv['mask'] = mask.astype(config.nt())

    return utils.flatten_dict(rv)

  def forward(self, **kwargs):
    kwargs = dict(kwargs)
    mask = kwargs['mask']

    del kwargs['mask']
    s = utils.unflatten_dict(kwargs)

    sides = []

    teammates = None
    opponents = None

    for pk in ['player', 'opponent']:
      p = s[pk]

      poke_array = p['pokemon']
      poke_array = self.pokemon_fc1(poke_array)
      poke_array = F.relu(poke_array)
      poke_array = self.pokemon_fc2(poke_array)
      poke_array = F.relu(poke_array)
      if pk == 'player':
        teammates = poke_array
      else:
        opponents = poke_array
      poke_array = poke_array.max(1)[0]

      active_array = p['activePokemon']
      active_array = self.pokemon_fc1(active_array)
      active_array = F.relu(active_array)
      active_array = self.active_fc2(active_array)
      active_array = F.relu(active_array)
      active_array = active_array.max(1)[0]

      combined = torch.cat([poke_array, active_array, p['sideConditions']], 1)
      combined = self.team_fc1(combined)
      combined = F.relu(combined)
      if pk == 'player':
        combined = self.player_fc2(combined)
      else:
        combined = self.opponent_fc2(combined)
      combined = F.relu(combined)
      sides.append(combined)

    sides.append(s['weather'])
    sides.append(s['weatherTimeLeft'])

    common = torch.cat(sides, 1)
    common = self.common_fc1(common)
    common = F.relu(common)

    # This section: compute policy
    move_common = torch.unsqueeze(torch.unsqueeze(common, 1), 1)
    move_common = move_common.expand(-1, self.n_active, self.n_moves, -1)

    move = torch.cat([move_common, s['moves']], 3)

    switch_common = torch.unsqueeze(common, 1).expand(-1, self.n_teammates, -1)
    switch = torch.cat([switch_common, teammates[:, :self.n_teammates, :]], 2)

    n_move = move
    n_move = F.relu(self.policy_move_fc1(n_move))
    n_move = self.policy_move_fc2(n_move)

    z_move = move
    z_move = F.relu(self.policy_zmove_fc1(z_move))
    z_move = self.policy_zmove_fc2(z_move)

    move_mods = common
    move_mods = F.relu(self.policy_move_mod_fc1(move_mods))
    move_mods = self.policy_move_mod_fc2(move_mods)

    switch = F.relu(self.policy_switch_fc1(switch))
    switch = self.policy_switch_fc2(switch)
    switch = switch.squeeze(-1)

    n_move = n_move.permute(0, 1, 3, 2)
    move_mods = move_mods.unsqueeze(-1)

    # TODO support doubles
    n_move = n_move[:, 0, :]
    z_move = z_move[:, 0, :].squeeze(-1)

    move_with_mod = n_move + move_mods
    move_with_mod = move_with_mod.reshape(move_with_mod.shape[0], -1)

    policy = torch.cat([move_with_mod, z_move, switch], 1)
    policy = policy[:, self.permutation]

    ps, lps = masked_softmax.apply(policy, mask)

    # This section: compute value
    v = common
    v = F.relu(self.value_fc1(v))
    v = self.value_fc2(v)

    return v, ps, lps
