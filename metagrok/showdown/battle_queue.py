import gevent
import gevent.lock

from metagrok.showdown import actor

class BattleQueue(actor.Actor):
  '''
  Handles battle management. The main trick here is that only one battle is considered at a time.
  So, for example:
    - I can't be matchmaking right after I accepted a challenge but before the battle starts
    - I can't send a challenge to someone if I am in matchmaking right now
    - I can't accept a challenge if I just sent a challenge to someone

  args:
    - [conf] username
    - [conf] accept_challenges (default: False)
    - [conf] formats           (default: ['gen7randombattle'])
    - [conf] max_concurrent    (default: 8)
  '''
  def __init__(self, parent, conf):
    super(BattleQueue, self).__init__(parent)
    self._username          = conf.username
    self._accept_challenges = conf.accept_challenges
    self._formats           = conf.formats
    self._max_concurrent    = conf.max_concurrent

  def on_start(self):
    self._s.match_count_sem = gevent.lock.BoundedSemaphore(self._max_concurrent)
    self._s.match_wait_lock = gevent.lock.BoundedSemaphore()

    # Stores best known estimate of in-progress or expected games
    self._s.challenges_from = {}
    self._s.challenges_to   = {}
    self._s.searching       = []
    self._s.games           = {}

    # This field represents which battle is currently being sought. It is either:
    # - None
    # - ('matchmaking', gametype)
    # - ('challenging', (username, gametype))
    # - ('challenged',  (username, gametype))
    # - ('accepted',    (username, gametype))
    self._s.status = None

  def receive(self, msg):
    if msg.opcode in {'matchmaking', 'challenging', 'challenged'}:
      self._join(msg)
    elif msg.opcode == 'update-challenges':
      self._update(msg.data)
    elif msg.opcode == 'search-cancelled-by-server':
      # Hack: disregard the wait lock, send out a search again in a few seconds.
      def fn():
        if not self._s.status or self._s.status.opcode != 'matchmaking':
          self.die('Unknown status, search cancelled but not matchmaking: [%r]', self._s.status)
        else:
          self._update_status(self._s.status)
      gevent.spawn_later(3.0, fn)
    elif msg.opcode == 'battle-started':
      if self._s.status is None:
        self.die('received a [%r] cmd but no waiting battle-req to complete', msg)
      else:
        self._release_wait_lock()
        self._s.status = None
    elif msg.opcode == 'battle-ended':
      self._release_count_sem()
    else:
      self.die('got unexpected message: %s', msg)

  def _update(self, data):
    if 'games' in data:
      self._s.games = data['games'] or {}
    if 'searching' in data:
      self._s.searching = data['searching'] or []
    if 'challengesFrom' in data:
      new_challenges_from = data['challengesFrom'] or {}
      for opp, fmt in new_challenges_from.items():
        if self._s.challenges_from.get(opp) != fmt:
          if not self._accept_challenges:
            self.info('ignored [%s] challenge from [%s], not accepting challenges', fmt, opp)
            self._reject_challenge(opp)
          elif fmt not in self._formats:
            self.info('ignored [%s] challenge from [%s], wrong format', fmt, opp)
            self._reject_challenge(opp)
          else:
            # This is a new challenge, queue it up
            self.info('responding to new [%s] challenge from [%s]', fmt, opp)
            self.send('challenged', (opp, fmt))
      self._s.challenges_from = new_challenges_from
    if 'challengesTo' in data:
      self._s.challenges_to = data['challengesTo'] or {}

    if self._s.status is not None:
      status = self._s.status
      self.warn('got a [%s] while battle-req [%s] is in-flight', data, status)
      # TODO figure out why the line below was written
      # self._update_status(status)

  def _join(self, msg):
    def fn():
      # If we are at capacity do not do anything yet
      self._acquire_count_sem()

      # If we area already waiting for a battle, do not do anything yet
      self._acquire_wait_lock()

      self._update_status(msg)

    gevent.spawn(fn)

  def _update_status(self, msg):
    '''There is a chance the request is no longer valid because some time has passed:
      - A waiting challenge may have been cancelled by the opponent
      - We may not want to enter matchmaking anymore (doesn't happen in current impl)
      - THE OPPONENT MAY NO LONGER BE AVAILABLE. (In controlled environments this shouldn't happen)
    '''
    new_status = self._check_cancel(msg)
    if not new_status:
      self._cancel(msg)
    else:
      self._s.status = new_status

  def _reject_challenge(self, opp):
    self._parent.send('send-to-room', ('/reject ' + opp, ''))

  def _cancel(self, msg):
    self.debug('decided not to enter %r, releasing locks', msg)
    self._release_wait_lock()
    self._release_count_sem()

  def _acquire_count_sem(self):
    self.debug('acquiring count sem')
    self._s.match_count_sem.acquire()
    self.debug('acquired count sem')

  def _release_count_sem(self):
    self.debug('releasing count sem')
    self._s.match_count_sem.release()
    self.debug('released count sem')

  def _acquire_wait_lock(self):
    self.debug('acquiring wait lock')
    self._s.match_wait_lock.acquire()
    self.debug('acquired wait lock')

  def _release_wait_lock(self):
    self.debug('releasing wait lock')
    self._s.match_wait_lock.release()
    self.debug('released wait lock')

  def _check_cancel(self, msg):
    opcode, data = msg

    if opcode == 'matchmaking':
      if data['team']:
        self._parent.send('send-to-room', ('/utm ' + data['team'], ''))
      fmt = data['fmt']
      self._parent.send('send-to-room', ('/search ' + fmt, ''))
      return msg

    if opcode == 'challenged':
      opp, fmt = data

      # Right now we only do gen7randombattle
      if fmt not in self._formats:
        # Let's send a reject to be nice. This is good practice in life in general
        self._reject_challenge(opp)

        self.warn('[%s] sent us a [%s] req, rejecting', opp, fmt)
        return None

      if self._s.challenges_from.get(opp) == fmt:
        self._parent.send('send-to-room', ('/accept ' + opp, ''))
        return ('accepted', data)

      # The opponent may have decided to battle us with a different battletype
      self._reject_challenge(opp)

      self.warn('[%s] no longer wants to battle us', opp)
      return None

    if opcode == 'accepted':
      # TODO: whether this handles stuff properly depends on when the updatechallenges message
      # arrives in relation to the new room opening up. If the room opens up after challenges
      # are updated, we could be cancelling the challenge too soon. Is there a more robust check?
      opp, fmt = data
      if self._s.challenges_from.get(opp) == fmt:
        return msg
      self.warn('somehow [%s] no longer wants to battle us', opp)
      return None

    if opcode == 'challenging':
      # TODO: implement this properly in the general case
      # This is gonna be a pain to implement. A dangling challenge consumes a semaphore count and
      # generally messes stuff up. For now, we should only be sending challenges in controlled
      # envs, so we don't need to fix this issue yet.
      self._parent.send('send-to-room', ('/challenge %s %s' % data, ''))
      return msg

    self.die('unknown message %r', msg)

  def __repr__(self):
    return 'BQ(%s)' % self._username

  def __str__(self):
    return repr(self)
