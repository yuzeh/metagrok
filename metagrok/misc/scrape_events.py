from glob import glob

from metagrok import np_json as json
from metagrok import jsons

side_conditions = set()
weathers = set()
volatiles = set()

raise Exception('Script is broken. TODO fix!')

for fname in glob('data/misc-state/*.jsons')[:-1]:
  print('processing ' + fname)
  for blob in jsons.stream(fname):
    if blob['weather']:
      weathers.add(blob['weather'])
    for side in blob['sides']:
      side_conditions.update(side['sideConditions'].keys())
      for pokemon in side['pokemon']:
        volatiles.update(pokemon.get('volatiles', {}).keys())

for fname, data in [
    ('BattleSideConditions', side_conditions),
    ('BattleWeathers', weathers),
    ('BattleVolatiles', volatiles),
]:
  path = 'dex/%s.json' % fname
  print('WRITING TO ' + path)
  with open(path, 'w') as fd:
    json.dump({k: 1. for k in data}, fd, indent = 2)

print('DONE')
