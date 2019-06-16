from metagrok import predef as _; assert _

import argparse
import logging

import gevent

from metagrok import config
from metagrok import torch_policy
from metagrok import utils

from metagrok.constants import LOG_FORMAT
from metagrok.showdown import Client, actor

from metagrok.pkmn.engine.player import EnginePkmnPlayer

logger = utils.default_logger_setup(logging.DEBUG)

def main():
  args = parse_args()
  gevent.spawn(start, args)
  gevent.wait()

def start(args):
  config.set_cuda(False)

  policy = torch_policy.load(args.policy)

  conf = utils.Ns()
  conf.accept_challenges = True
  conf.formats = ['gen7randombattle', 'gen4randombattle']
  conf.timer = True
  conf.username = username = args.username or utils.random_name()
  conf.host = args.host
  conf.port = args.port
  conf.max_concurrent = 1
  conf.player_ctor = lambda gid: EnginePkmnPlayer(policy, gid)
  conf.pslog_dir = None
  conf.log_dir = 'tmp/pvp'
  conf.wait_time_before_requesting_move_seconds = 0.0

  client = Client(actor.ROOT_SENTINEL, conf)

  print('Setting up %s on %s:%s' % (username, args.host, args.port))

  client.main()
  for i in range(args.num_battles):
    logger.info(client.queue.get())
  client.join()

def parse_args():
  parser = argparse.ArgumentParser('Runs the bot.')
  parser.add_argument('policy')
  parser.add_argument('--username')
  parser.add_argument('--num-battles', type = int, default = 100)
  parser.add_argument('--host', default = 'localhost')
  parser.add_argument('--port', default = '8000')
  return parser.parse_args()

if __name__ == '__main__':
  main()
