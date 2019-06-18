from metagrok import predef as _; assert _

import argparse
import json
import logging
import logging.handlers
import os
import textwrap

import gevent
import requests

from metagrok import config
from metagrok import constants
from metagrok import mail
from metagrok import showdown
from metagrok import utils
from metagrok import torch_policy
from metagrok.pkmn.engine.player import EnginePkmnPlayer

def main():
  args = parse_args()

  import metagrok.remote_debug
  metagrok.remote_debug.listen()

  params = gevent.spawn(start, args).get()
  root_dir = params['root_dir']
  username = params['username']

  rating_fname = os.path.join(root_dir, 'rating.json')
  ps_profile_url = 'https://pokemonshowdown.com/user/%s.json' % username
  rating_struct = requests.get(ps_profile_url).json()
  rating_string = json.dumps(rating_struct, indent = 2)

  with open(rating_fname, 'w') as fd:
    fd.write(rating_string)
    fd.write('\n')

  subject = 'Evaluation finished for [%s]' % params['spec']
  text = textwrap.dedent('''\
  Check out the final rating here: %s
  
  Rating:
  %s

  Config:
  %s''') % (ps_profile_url, rating_string, json.dumps(params, indent = 2))

  mail.send(subject, text)

def start(args):
  config.set_cuda(False)
  num_matches = args.num_matches
  username = args.username or utils.random_name()

  policy = torch_policy.load(args.spec)

  root_dir        = args.root_dir or ('data/evals/%s' % utils.ts())
  proc_log_fname  = os.path.join(root_dir, 'debug.log')
  player_log_dir  = None
  if args.debug_mode:
    player_log_dir = os.path.join(root_dir, 'player-logs')

  utils.mkdir_p(root_dir)
  if player_log_dir:
    utils.mkdir_p(player_log_dir)

  params = vars(args)
  params['username'] = username
  params['root_dir'] = root_dir
  with open(os.path.join(root_dir, 'config.json'), 'w') as fd:
    json.dump(params, fd)

  logger = utils.default_logger_setup(logging.DEBUG)
  fhandler = logging.handlers.RotatingFileHandler(
      proc_log_fname,
      maxBytes = 16 * 1024 * 1024,
      backupCount = 5)
  fhandler.setFormatter(logging.Formatter(constants.LOG_FORMAT))
  if args.debug_mode:
    fhandler.setLevel(logging.DEBUG)
  else:
    fhandler.setLevel(logging.INFO)
  logger.addHandler(fhandler)

  conf = utils.Ns()
  conf.accept_challenges = False
  conf.formats = [args.format]
  conf.timer = True
  conf.username = username
  conf.host = args.host
  conf.port = args.port
  conf.max_concurrent = args.max_concurrent
  conf.pslog_dir = None
  conf.log_dir = player_log_dir
  conf.wait_time_before_requesting_move_seconds = args.wait_time_before_move

  logger.info('Setting up %s on %s:%s', conf.username, conf.host, conf.port)
  logger.info('Outputting logs to %s', root_dir)

  player_ctor = lambda gid: EnginePkmnPlayer(policy, gid, play_best_move = args.play_best_move)

  if args.team:
    with open(args.team) as fd:
      team = fd.read().strip()
  else:
    team = ''

  game = showdown.MatchmakingGame(conf, fmt = args.format, team = team)
  game.main()

  matches = dict((i, game([player_ctor])) for i in range(num_matches))

  count = 0
  record = {'winner': 0, 'loser': 0, 'tie': 0}
  while matches:
    found = False
    for i, msg in matches.items():
      if msg.ready():
        result = msg.get()
        logger.info('Finished %d/%d matches: %s', count + 1, num_matches, result)
        record[result['result']] += 1
        count += 1
        found = True
        break

    if found:
      del matches[i]

    gevent.sleep(1.)

  logger.info('Battles completed! Quitting...')
  params['record'] = record
  logger.info(params['record'])

  game.stop()
  game.join()
  return params

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('spec')
  parser.add_argument('--root-dir')
  parser.add_argument('--username')
  parser.add_argument('--wait-time-before-move', type = float, default = 3.0)
  parser.add_argument('--num-matches', type = int, default = 1000)
  parser.add_argument('--max-concurrent', type = int, default = 4)
  parser.add_argument('--host', default = 'sim.smogon.com')
  parser.add_argument('--port', default = '80')
  parser.add_argument('--debug-mode', action = 'store_true')
  parser.add_argument('--play-best-move', action = 'store_true')
  parser.add_argument('--format', default = 'gen7randombattle')
  parser.add_argument('--team')
  return parser.parse_args()

if __name__ == '__main__':
  main()
