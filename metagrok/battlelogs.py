import os
import gzip

from io import StringIO

from metagrok import np_json as json
from metagrok import jsons
from metagrok import fileio

class BattleLogger(object):
  def __init__(self, gid, log_dir = None):
    if log_dir:
      self._fname = os.path.join(log_dir, '%s.jsons.gz' % gid)
      self._fd = gzip.GzipFile(self._fname, 'wb')
    else:
      self._fname = None
      self._fd = None

  def log(self, blob, **kwargs):
    if self._fd:
      blob.update(kwargs)
      message = json.dumps(blob) + '\n'
      self._fd.write(message.encode('utf-8'))

  def result(self, opcode):
    self.log({}, result = opcode)

  def close(self):
    if self._fd:
      self._fd.close()

def parse(arg, gamma = 1.0, lam = 1.0, reward_shaper = None):
  states = jsons.load(arg)
  result = states[-1]['result']
  if result == 'winner':
    final_reward = 1.0
  elif result == 'loser':
    final_reward = -1.0
  else:
    assert result == 'tie', result
    final_reward = 0.0

  if reward_shaper:
    reward_shaper(states)

  states = states[:-1]
  for state in states:
    state['action'] = int(state['action'])
    if 'value_pred' not in state:
      state['value_pred'] = 0.0

  compute_returns(states, final_reward, gamma, lam)

  return states

def compute_returns(path, final_reward, gamma = 0.99, lam = 0.95):
  path[-1]['return'] = final_reward
  path[-1]['std_return'] = final_reward
  delta = final_reward - path[-1]['value_pred']
  path[-1]['advantage'] = gae = delta

  for i in reversed(list(range(len(path) - 1))):
    cp = path[i]
    np = path[i + 1]
    delta = cp.get('reward', 0.0) + gamma * np['value_pred'] - cp['value_pred']
    cp['advantage'] = gae = delta + gamma * lam * gae
    cp['return'] = gae + cp['value_pred']
    cp['std_return'] = gamma * np['std_return'] + cp.get('reward', 0.0)

def result_only(file_name):
  with fileio.open(file_name, 'rb') as fd:
    buf = StringIO(fd.read())

  buf.seek(-2, os.SEEK_END)
  while buf.read(1) != b'\n':
    buf.seek(-2, os.SEEK_CUR)
  line = json.loads(buf.readline())

  return line['result']