class Scheduler(object):
  def __init__(self, schedule):
    self._schedule = sorted(schedule, key = lambda x: x['until'])

  def select(self, itr):
    for idx in range(len(self._schedule)):
      cur = self._schedule[idx]
      if itr < cur['until']:
        break
    return self._schedule[idx]['value']
