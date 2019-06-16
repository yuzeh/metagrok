import json

import numpy as np

from metagrok import config
from metagrok import fileio
from metagrok.pkmn import parser

from metagrok.pkmn.engine.core import Engine

engine = Engine(__name__)

def convert(replay):
  '''Returns two sequences of Blocks, one for p1 and one for p2.
  Each Block (that is not the last) contains:
    - _updates: The sequence of log messages that that user sees on that turn
    - request: The request object that is associated with this block.
    - state: The current state.
    - action: an integer in [0, N) (now N = 10, soon N = 10 + 12 for mega/zmove/ultra)
      representing the action that was actually taken
    - candidates: a list of N action names (directly sent to PS)
      - the name in the slot will be None if action is not allowed
  The last block contains the winner of the battle, and the logs that lead up until that log.

  The two sequences of blocks may not be of equal length; there are some turns where only
  one player is required to make a decision.
  '''
  raise ValueError('Deprecated')
  blocks = replay['blocks']

  out_blocks = dict(
      p1 = dict(name = replay['p1'][0], blocks = [{'_updates': []}]),
      p2 = dict(name = replay['p2'][0], blocks = [{'_updates': []}]),
  )

  engine.start('p1')
  engine.start('p2')

  for i in range(len(blocks) - 1):
    cur = blocks[i]
    nex = blocks[i + 1]

    _1, _2, p1_action, p2_action = nex['choice'].split('|')

    actions = dict(p1 = p1_action, p2 = p2_action)

    for p in ['p1', 'p2']:
      request, updates = extract(cur[p])
      #candidates = parser.parse_valid_actions(request, replay_names = True)
      candidates = parser.parse_valid_actions(request)

      for update in updates:
        engine.update(p, update)

      blks = out_blocks[p]['blocks']
      blk = blks[-1]
      blk['_updates'].extend(updates)

      if actions[p]:
        blk['candidates'] = candidates
        blk['action'] = candidates.index(actions[p])
        blk['request'] = request
        blk['state'] = engine.fetch(p, request)
        blk['probs'] = np.zeros(len(candidates), dtype = config.nt())
        blk['probs'][blk['action']] = 1.0

        blks.append({'_updates': []})

  last = blocks[-1]['logs']
  assert last[-1].startswith('|win|')
  _1, _2, winner = last[-1].split('|')

  for p in ['p1', 'p2']:
    blk = out_blocks[p]['blocks'][-1]
    blk['_updates'].extend([l for l in blocks[-1][p] if not l.startswith('|request|')])
    blk['result'] = 'winner' if winner == out_blocks[p]['name'] else 'loser'

  engine.stop('p1')
  engine.stop('p2')

  return out_blocks['p1']['blocks'], out_blocks['p2']['blocks']

def extract(log):
  updates = list(log)
  request = [r for r in updates if r.startswith('|request|')]
  assert len(request) == 1
  request = request[0]
  updates.remove(request)
  return json.loads(request[9:]), updates

def main():
  import os

  from metagrok import utils
  from metagrok.battlelogs import BattleLogger

  args = parse_args()
  in_dir = args.in_dir
  out_dir = args.out_dir

  for in_subdir in sorted(os.listdir(in_dir)):
    in_subdir_path = os.path.join(in_dir, in_subdir)
    out_subdir_path = os.path.join(out_dir, in_subdir)
    utils.mkdir_p(out_subdir_path)
    for fname in sorted(os.listdir(in_subdir_path)):
      basename, ext = os.path.splitext(fname)
      in_path = os.path.join(in_subdir_path, fname)

      if not fname.endswith('.json'):
        print('Skipping: ' + in_path)
        continue

      p1_base = basename + '.p1'
      p2_base = basename + '.p2'

      if (os.path.isfile(os.path.join(out_subdir_path, p1_base + '.jsons.gz')) and
          os.path.isfile(os.path.join(out_subdir_path, p2_base + '.jsons.gz'))):
        print('Already processed: ' + in_path)
        continue
      print('Processing: ' + in_path)

      with fileio.open(in_path) as fd:
        replay = json.load(fd)
        p1s, p2s = convert(replay)

      blogger = BattleLogger(p1_base, log_dir = out_subdir_path)
      for block in p1s:
        blogger.log(block)
      blogger.close()

      blogger = BattleLogger(p2_base, log_dir = out_subdir_path)
      for block in p2s:
        blogger.log(block)
      blogger.close()

def parse_args():
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('in_dir')
  parser.add_argument('out_dir')
  return parser.parse_args()


if __name__ == '__main__':
  main()
