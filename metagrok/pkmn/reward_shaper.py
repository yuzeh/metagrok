class RewardShaper(object):
  def __init__(self, **kwargs):
    self._faint = kwargs.get('faint')
    self._fail = kwargs.get('fail')
    self._supereffective = kwargs.get('supereffective')
    self._resisted = kwargs.get('resisted')
    self._immune = kwargs.get('immune')
    self._iteration = kwargs.get('iteration', 0)

  def __call__(self, blobs):
    for i in reversed(range(len(blobs) - 1)):
      nex = blobs[i + 1]
      cur = blobs[i]
      state = cur['state']
      if isinstance(state, list):
        state = state[-1]['state']
      updates = nex['_updates']
      reward = cur.get('reward', 0.)

      # Determine if player is p1 or p2
      whoami = state['whoami']
      if state['sides'][0]['name'] == whoami:
        who = 'p1'
      else:
        assert state['sides'][1]['name'] == whoami
        who = 'p2'

      for update in updates:
        if self._faint is not None and update.startswith('|faint|'):
          if update.split('|')[2].startswith(who):
            reward -= self._faint
          else:
            reward += self._faint

        if self._fail is not None and update.startswith('|-fail|'):
          if update.split('|')[2].startswith(who):
            reward -= self._fail

        if self._supereffective is not None and update.startswith('|-supereffective|'):
          if not update.split('|')[2].startswith(who):
            reward += self._supereffective

        if self._resisted is not None and update.startswith('|-resisted|'):
          if not update.split('|')[2].startswith(who):
            reward -= self._resisted

        if self._immune is not None and update.startswith('|-immune|'):
          if not update.split('|')[2].startswith(who):
            reward -= self._immune

      cur['reward'] = reward

class NewRewardShaper(object):
  def __init__(self, **kwargs):
    self._zero_sum = kwargs.get('zero_sum', False)
    self._events = {}
    for key in _key_to_event:
      if kwargs.get(key):
        self._events[key] = kwargs[key]

  def __call__(self, blobs):
    for i in reversed(range(len(blobs) - 1)):
      nex = blobs[i + 1]
      cur = blobs[i]
      state = cur['state']
      updates = nex['_updates']
      reward = cur.get('reward', 0.)

      # Determine if player is p1 or p2
      whoami = state['whoami']
      if state['sides'][0]['name'] == whoami:
        who = 'p1'
      else:
        assert state['sides'][1]['name'] == whoami
        who = 'p2'

      for update in updates:
        for event, delta in self._events.iteritems():
          v = mentions(update, _key_to_event[event], who)
          if v != 0:
            if v > 0 or self._zero_sum:
              reward += delta * v
      cur['reward'] = reward

def mentions(update, event, who):
  '''
  The functions below take two arguments. Return value is:
  * +1 if `update` mentioned the event and happened to `who`
  * -1 if `update` mentioned the event and did not happen to `who`
  *  0 if `update` does not mention the event
  '''
  if update.startswith(event):
    return +1 if update.split('|')[2].startswith(who) else -1
  return 0

_key_to_event = dict(
    faint = '|faint|',
    fail = '|-fail|',
    supereffective = '|-supereffective|',
    resisted = '|-resisted|',
    immune = '|-immune|',
)

def create(new_style = False, **kwargs):
  if new_style:
    ctor = NewRewardShaper
  else:
    ctor = RewardShaper
  return ctor(**kwargs)