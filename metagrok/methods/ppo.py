import argparse
import logging
import math
import sys
import unittest

import numpy as np

import torch

from metagrok import config, constants, utils
from metagrok.battlelogs import BattleLogger
from metagrok.games.tictactoe import Policy
from metagrok.games import cgpi
from metagrok.methods import learner
from metagrok.methods.updater import PolicyUpdater
from metagrok.torch_utils.data import TTensorDictDataset

class PPOUpdater(PolicyUpdater):
  'Implements Proximal Policy Optimization, as described in: https://arxiv.org/abs/1707.06347'
  logger = logging.getLogger('PPOUpdater')

  def __init__(self, **kwargs):
    super(PPOUpdater, self).__init__(**kwargs)

    self._clip_param = kwargs['clip_param']
    self._max_grad_norm = kwargs.get('max_grad_norm')

    self._eb_keys = {'value', 'action_log_prob'}
    if self._entropy_coef is not None:
      self._eb_keys.add('dist_entropy')

  def batch_update(self, policy,
      features, advantages, actions, action_log_probs, value_preds, returns, **kwargs):
    clip_param = self._clip_param
    res = policy.evaluate_batch(features, actions, keys = self._eb_keys)
    values = res['value']
    alps = res['action_log_prob']

    ratio = torch.exp(alps - action_log_probs)
    surr1 = ratio * advantages
    surr2 = torch.clamp(ratio, 1.0 - clip_param, 1.0 + clip_param) * advantages
    action_loss = -torch.min(surr1, surr2).mean()

    vp2 = value_preds + torch.clamp(values - value_preds, -clip_param, clip_param)
    vl1 = (values - returns).pow(2)
    vl2 = (vp2 - returns).pow(2)
    value_loss = self._value_coef * torch.max(vl1, vl2).mean()
    rv = dict(action_loss = action_loss, value_loss = value_loss)
    if self._entropy_coef is not None:
      rv['entropy_loss'] = -self._entropy_coef * res['dist_entropy'].mean()
    return rv

def main():
  args = parse_args()
  demo(args)

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--game', default = 'metagrok.games.tictactoe.DangerousGame')
  parser.add_argument('--policy', default = 'metagrok.games.tictactoe.Policy')
  parser.add_argument('--player', default = 'metagrok.games.cgpi.TorchBasePlayer')

  parser.add_argument('--start-dir')
  parser.add_argument('--parallelism', type = int, default = 1)
  parser.add_argument('--vbatch-size', type = int, default = 64)
  parser.add_argument('--clip-param', type = float, default = 0.2)
  parser.add_argument('--max-grad-norm', type = float)
  parser.add_argument('--delete-logs', action = 'store_true')
  parser.add_argument('--cuda', action = 'store_true')
  parser.add_argument('--entropy-coef', type = float)
  parser.add_argument('--gamma', type = float, default = 0.75)
  parser.add_argument('--lam', type = float, default = 0.7)
  parser.add_argument('--num-epochs', type = int, default = 4)
  parser.add_argument('--num-iters', type = int, default = 100)
  parser.add_argument('--num-matches', type = int, default = 256)
  parser.add_argument('--opt-lr', type = float, default = 7e-4)
  return parser.parse_args()

def demo(args):
  logger = logging.getLogger()
  logger.setLevel(logging.INFO)
  handler = logging.StreamHandler()
  handler.setFormatter(logging.Formatter(constants.LOG_FORMAT))
  logger.addHandler(handler)

  config.set_cuda(args.cuda)
  torch.manual_seed(0)

  game = utils.hydrate(args.game)()
  policy = utils.hydrate(args.policy)()
  player_cls = utils.hydrate(args.player)
  opponent = cgpi.RandomBasePlayer()

  updater = PPOUpdater(
      random_access = True,
      opt_lr = args.opt_lr,
      policy = policy,
      vbatch_size = args.vbatch_size,
      max_grad_norm = args.max_grad_norm,
      num_epochs = args.num_epochs,
      clip_param = args.clip_param,
      entropy_coef = args.entropy_coef,
      weight_decay = 0.001,
  )

  start_dir = args.start_dir or utils.ts()
  out_dir = 'data/v1-ppo/%s/%s' % (args.game, start_dir)
  print(out_dir)

  def simulate(iter_dir):
    policy.eval()
    for i in range(args.num_matches):
      player = player_cls(policy, str(i))
      game.play(player, opponent)

      blogger = BattleLogger(player.gid, iter_dir)
      for block in player.blocks:
        blogger.log(block)
      blogger.result(player.result)
      blogger.close()

  learner.run(
      num_iters = args.num_iters,
      out_dir = out_dir,
      policy = policy,
      updater = updater,
      gamma = args.gamma,
      lam = args.lam,
      delete_logs = args.delete_logs,
      simulate_fn = simulate,
  )

  print(out_dir)

'''
./rp metagrok/methods/ppo.py --game metagrok.games.tictactoe.Game \
    --num-matches 1024 \
    --num-iters 100 \
    --gamma 0.75 \
    --lam 0.75 \
    --delete-logs \
    --num-epochs 4 \
    --vbatch-size 256
'''

if __name__ == '__main__':
  main()
