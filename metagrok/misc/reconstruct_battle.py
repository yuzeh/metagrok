import difflib
import json
import io
import os
import subprocess
import time

from metagrok import jsons
from metagrok import showdown_stdio
from metagrok import utils

PS_DIR = os.path.join(os.path.abspath('./tmp-showdown'))

logger = utils.default_logger_setup()

def parse_args():
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('input')
  parser.add_argument('output')
  return parser.parse_args()

def main():
  args = parse_args()
  return reconstruct(args.input, args.output)

def reconstruct(input, output):
  with io.open(input) as fd:
    data = json.load(fd)
  original_spectator = preprocess_spectator(data['log'].splitlines())

  inputlog = data['inputlog'].splitlines()
  assert inputlog[0].startswith('>version')
  assert inputlog[1].startswith('>start')

  version_command = inputlog.pop(0)
  start_command = inputlog.pop(0)

  ps_sha = version_command[len('>version '):]
  options = json.loads(start_command[len('>start '):])

  try:
    subprocess.check_call(['git', 'checkout', ps_sha], cwd = PS_DIR)
  except subprocess.CalledProcessError:
    raise GitShaDoesNotExist(ps_sha)

  subprocess.check_call(['rm', '-rf', 'node_modules'], cwd = PS_DIR)
  subprocess.check_call(['npm', 'install'], cwd = PS_DIR)
  if os.path.isfile(os.path.join(PS_DIR, 'build')):
    subprocess.check_call(['node', 'build'], cwd = PS_DIR)

  blocks = try_reconstruct(options, inputlog, original_spectator, data)
  jsons.dump(output, blocks)

def try_reconstruct(options, inputlog, original_spectator, data):
  battle = showdown_stdio.Battle(
    options = options,
    prog = PS_DIR + '/pokemon-showdown',
    timeout_ok = True)
  blocks = []

  battle._send(inputlog[0]) # >p1 ...
  battle._send(inputlog[1]) # >p2 ...

  blocks.append(battle.recv())

  for log in inputlog[2:]:
    battle._send(log)
  
    try:
      block = battle.recv()
      blocks.append(block)
      if block['winner']:
        break
    except showdown_stdio.BattleInputIncomplete:
      pass
  
  battle.close()

  if not all(b['omniscient'] for b in blocks):
    raise ValueError('We skipped a beat in parsing the battle logs')

  reconstructed_spectator = [
    line 
    for block in blocks
    for line in block['omniscient']]

  if not original_spectator[:len(reconstructed_spectator)] == reconstructed_spectator:
    diff = list(difflib.unified_diff(original_spectator, reconstructed_spectator))
    raise ReconstructionMismatch(diff)
  
  if not blocks[-1]['winner']:
    for i, winner_log in enumerate(original_spectator):
      if winner_log.startswith('|win|'):
        break
    assert winner_log.startswith('|win|')

    winner = winner_log.split('|')[2]
    if winner == data['p1']:
      winner_position = 'p1'
    elif winner == data['p2']:
      winner_position = 'p2'
    else:
      raise ValueError('Unknown winner! ' + winner)

    blocks.append(dict(
      p1log = original_spectator[i:],
      p2log = original_spectator[i:],
      omniscient = original_spectator[i:],
      spectator = original_spectator[i:],
      winner = winner_position,
      seed = options['seed'],
      p1req = [],
      p2req = [],
    ))

  return blocks

def ignore_log(line):
  if not line:
    return True

  for prefix in ['|j|', '|c|', '|l|', '|inactive|', '|raw|', '|inactiveoff|', '|n|', '|html|']:
    if line.startswith(prefix):
      return True
  return False

def preprocess_spectator(lines):
  rv = []
  num_player_logs = 0
  for line in lines:
    if ignore_log(line):
      continue
    if line.startswith('|-mustrecharge|') and line == rv[-1]:
      continue

    if line.startswith('|player|'):
      if num_player_logs >= 2:
        continue
      num_player_logs += 1
    rv.append(line)
  return rv

class GitShaDoesNotExist(Exception): pass
class ReconstructionMismatch(Exception):
  def __init__(self, diff):
    super(ReconstructionMismatch, self).__init__('Mismatch between reconstructed and original')
    self._diff = diff
  
  @property
  def diff(self):
    return self._diff

if __name__ == '__main__':
  main()