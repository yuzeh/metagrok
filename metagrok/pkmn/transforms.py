# coding=utf-8
'Transforms for dataset augmentation on .example.json objects.'
import random

from metagrok.pkmn.engine.navigation import extract_players

def scramble(item):
  player_moves = [_random_permutation(4) for _ in range(6)]
  player_pkmns = [0] + _shuffle(list(range(1, 6)))
  opponent_moves = [_random_permutation(4) for _ in range(6)]
  opponent_pkmns = [0] + _shuffle(list(range(1, 6)))

  reorder(item, player_moves, player_pkmns, opponent_moves, opponent_pkmns)
  return item

def reorder(item,
    player_moves,
    player_pkmns,
    opponent_moves,
    opponent_pkmns):
  '''Shuffles move orders and pokemon orders.
  - item: the struct to reorder.
  - player_moves, opponent_moves: a list of 6 permutations of the values range(4)
  - player_pkmns, opponent_pkmns: a permutation of the values range(6) with v[0] == 0 '''

  assert len(player_moves) == 6
  for i, perm in enumerate(player_moves):
    assert is_perm(perm, 4), 'player_moves[%s] is not a permutation: %s' % (i, perm)
  assert is_perm(player_pkmns, 6), 'player_pkmns is not a permutation: %s' % player_pkmns
  assert player_pkmns[0] == 0
  # TODO: for doubles and triples, player_pkmns[:2] or player_pkmns[:3] need to be fixed

  assert len(opponent_moves) == 6
  for i, perm in enumerate(opponent_moves):
    assert is_perm(perm, 4), 'opponent_moves[%s] is not a permutation: %s' % (i, perm)
  assert is_perm(opponent_pkmns, 6), 'opponent_pkmns is not a permutation: %s' % opponent_pkmns
  assert opponent_pkmns[0] == 0

  state = item['state']
  candidates = item['candidates']
  probs = item['probs']

  player, opponent = extract_players(state)

  # Shuffle opponent
  for perm, pkmn in zip(opponent_moves, opponent['pokemon']):
    pkmn['moveTrack'] = _apply_perm(pkmn['moveTrack'], perm)
  opponent['pokemon'] = _apply_perm(opponent['pokemon'], opponent_pkmns)

  # Shuffle self
  for perm, pkmn in zip(player_moves, player['pokemon']):
    pkmn['moveTrack'] = _apply_perm(pkmn['moveTrack'], perm)
  player['pokemon'] = _apply_perm(player['pokemon'], player_pkmns)

  # check requests
  if 'request' in item:
    req = item['request']
    if 'active' in req and len(req['active']) > 1:
      active = req['active'][0]
      active['moves'] = _apply_perm(active['moves'], player_moves[0])
    if 'side' in req and 'pokemon' in req['side']:
      side = req['side']
      side['pokemon'] = _apply_perm(side['pokemon'], player_pkmns)

  candidate_perm = player_moves[0] + [4 + pp for pp in player_pkmns]
  while len(candidate_perm) < len(candidates):
    last = len(candidate_perm)
    candidate_perm.extend([last + mp for mp in player_moves[0]])

  candidates = [candidates[i] for i in candidate_perm]
  for i in range(4, 10):
    if candidates[i]:
      candidates[i] = 'switch %d' % (i - 3)

  item['candidates'] = candidates
  item['probs'] = probs[candidate_perm]
  item['action'] = candidate_perm.index(item['action'])

def _apply_perm(old, perm):
  new = []
  for i in perm:
    if len(old) > i:
      new.append(old[i])
  return new

def _random_permutation(n):
  return _shuffle(list(range(n)))

def _shuffle(vs):
  rv = list(vs)
  random.shuffle(rv)
  return rv

def is_perm(vs, length = None):
  if length is None:
    length = len(vs)
  seen = [False for _ in range(length)]
  for v in vs:
    if v >= length:
      return False
    seen[v] = True
  return all(seen)

def main():
  import argparse

  from metagrok import np_json as json

  parser = argparse.ArgumentParser()
  parser.add_argument('input_file', type = argparse.FileType('r'))

  args = parser.parse_args()
  data = json.load(args.input_file)

  player_moves = [list(range(4)) for _ in range(6)]
  player_pkmns = list(range(6))
  opponent_moves = [list(range(4)) for _ in range(6)]
  opponent_pkmns = list(range(6))

  player_pkmns = [0, 1, 2, 3, 5, 4]
  # opponent_moves[1] = [2, 0, 3, 1]

  reorder(data, player_moves, player_pkmns, opponent_moves, opponent_pkmns)
  print(json.dumps(data, indent = 2))

if __name__ == '__main__':
  main()
