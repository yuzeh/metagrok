import json
import numpy as np

with open('data/learnsets.json') as fd:
  learnsets = {k: list(v['learnset'].keys()) for k, v in json.load(fd).items()}

all_pokes = sorted(set(learnsets.keys()))
all_moves = sorted(set(sum(list(learnsets.values()), [])))

poke2idx = {k: i for i, k in enumerate(all_pokes)}
move2idx = {k: i for i, k in enumerate(all_moves)}

M = np.zeros((len(all_pokes), len(all_moves)), dtype = float)
for k, vs in learnsets.items():
  i = poke2idx[k]
  for v in vs:
    j = move2idx[v]
    M[i, j] = 1.0

U, S, V = np.linalg.svd(M)
CS = np.cumsum(S)
CS /= CS[-1]
print(CS)
