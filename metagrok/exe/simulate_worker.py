import os
import sys
import time

from metagrok import battlelogs
from metagrok import config
from metagrok import formats
from metagrok import utils
from metagrok import torch_policy
from metagrok import np_json as json

from metagrok.pkmn.games import Game
from metagrok.pkmn.engine.player import EnginePkmnPlayer

def main():
  args = parse_args()
  config.set_cuda(False)

  from metagrok import remote_debug
  remote_debug.listen()

  p1_policy = torch_policy.load(args.policy_tag)
  p2_policy = p1_policy
  if args.p2_policy_tag:
    p2_policy = torch_policy.load(args.p2_policy_tag)

  fmt = formats.get(args.fmt)
  game = Game(fmt, '{}/{}/pokemon-showdown'.format(
      config.get('showdown_root'),
      config.get('showdown_server_dir')))
  count = 0
  while True:
    time.sleep(0.1)

    r = sys.stdin.readline().strip()
    if not r:
      continue

    if r == 'done':
      break

    battle_dir = os.path.join('/tmp', args.id, '%06d' % count)
    utils.mkdir_p(battle_dir)

    p1 = EnginePkmnPlayer(p1_policy, 'p1', epsilon = args.epsilon)
    p2 = EnginePkmnPlayer(p2_policy, 'p2', epsilon = args.epsilon)
    game.play(p1, p2)

    num_blocks = 0
    for i, player in enumerate([p1, p2]):
      blogger = battlelogs.BattleLogger('p%d' % (i + 1), battle_dir)
      for block in player.blocks:
        blogger.log(block)
        num_blocks += 1
      blogger.close()
    count += 1

    sys.stdout.write('%s\t%d\n' % (battle_dir, num_blocks))
    sys.stdout.flush()

def parse_args():
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('policy_tag')
  parser.add_argument('fmt')
  parser.add_argument('id')
  parser.add_argument('--p2-policy-tag')
  parser.add_argument('--epsilon', type = float, default = 0.)
  return parser.parse_args()

if __name__ == '__main__':
  main()
