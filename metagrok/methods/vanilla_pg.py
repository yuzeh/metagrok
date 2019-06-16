import argparse
import logging

import numpy as np

import torch

from metagrok import config, constants, utils
from metagrok.battlelogs import BattleLogger
from metagrok.games.tictactoe import Policy
from metagrok.games import cgpi
from metagrok.methods import learner
from metagrok.methods.updater import PolicyUpdater

class VanillaPGUpdater(PolicyUpdater):
  'Implements the standard Policy Gradient algorithm.'
  logger = logging.getLogger('VanillaPGUpdater')

  def __init__(self, **kwargs):
    super(VanillaPGUpdater, self).__init__(**kwargs)
    self._eb_keys = {'value', 'action_log_prob'}

  def batch_update(self, policy, features, advantages, actions, **kwargs):
    res = policy.evaluate_batch(features, actions, keys = self._eb_keys)
    val = res['value']
    alps = res['action_log_prob']
    action_loss = -(alps * advantages).mean()
    value_loss = (val - advantages).pow(2).mean()
    return dict(action_loss = action_loss, value_loss = value_loss)

def main():
  args = parse_args()
  demo(args)

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--game', default = 'metagrok.games.tictactoe.DangerousGame')
  parser.add_argument('--policy', default = 'metagrok.games.tictactoe.Policy')

  parser.add_argument('--start-dir')
  parser.add_argument('--vbatch-size', type = int, default = 256)
  parser.add_argument('--gamma', type = float, default = 0.75)
  parser.add_argument('--lam', type = float, default = 0.7)
  parser.add_argument('--num-iters', type = int, default = 100)
  parser.add_argument('--num-matches', type = int, default = 256)
  parser.add_argument('--max-grad-norm', type = float)
  parser.add_argument('--opt-lr', type = float, default = 7e-4)
  parser.add_argument('--delete-logs', action = 'store_true')
  parser.add_argument('--cuda', action = 'store_true')
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
  opponent = cgpi.RandomBasePlayer()

  updater = VanillaPGUpdater(
      policy = policy,
      opt_lr = args.opt_lr,
      vbatch_size = args.vbatch_size,
      max_grad_norm = args.max_grad_norm,
      num_epochs = 1,
  )

  start_dir = args.start_dir or utils.ts()
  out_dir = 'data/test/v0-vanilla-pg/%s/%s' % (args.game, start_dir)
  print(out_dir)

  def simulate(iter_dir):
    policy.eval()
    for i in range(args.num_matches):
      player = cgpi.TorchBasePlayer(policy, '%s' % i)
      game.play(player, opponent)

      blogger = BattleLogger(player.gid, iter_dir)
      for block in player.blocks:
        blogger.log(block)
      blogger.result(player.result)
      blogger.close()

  learner.run(
      num_iters = args.num_iters,
      policy = policy,
      out_dir = out_dir,
      updater = updater,
      gamma = args.gamma,
      lam = args.lam,
      delete_logs = args.delete_logs,
      simulate_fn = simulate,
  )

  print(out_dir)

if __name__ == '__main__':
  main()
