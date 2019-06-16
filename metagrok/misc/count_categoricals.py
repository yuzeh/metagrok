from collections import Counter

from metagrok import np_json as json
from metagrok import jsons
from metagrok import utils

logger = utils.default_logger_setup()

def main():
  args = parse_args()
  seen_categoricals = {k: Counter() for k in ['species', 'items', 'abilities', 'moves']}
  for fname in utils.find(args.dirname, '*.jsons.gz'):
    logger.info('Loading %s', fname)
    log = next(jsons.stream(fname))
    pokemon = [poke for side in log['state']['sides'] for poke in side['pokemon']]
    for poke in pokemon:
      for category, key in _stuff_to_read:
        if key in poke:
          seen_categoricals[category][poke[key]] += 1
      for move, _ in poke['moveTrack']:
        seen_categoricals['moves'][move] += 1

  json.dump(seen_categoricals, args.output, indent = 2)

_stuff_to_read = [
    ('species',   'baseSpecies'),
    ('species',   'species'),
    ('items',     'item'),
    ('abilities', 'ability'),
    ('abilities', 'baseAbility'),
]

def parse_args():
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('dirname')
  parser.add_argument('output', type = argparse.FileType('w'))
  return parser.parse_args()

if __name__ == '__main__':
  main()
