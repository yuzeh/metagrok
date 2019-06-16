import inspect

import gevent
import gevent.event

class BaseGame(object):
  @property
  def batch_playable(self):
    return True

  @property
  def num_players(self):
    raise NotImplementedError
  
  def play(self, *players):
    raise NotImplementedError

  @staticmethod
  def action(player):
    rv = player.action()
    if isinstance(rv, gevent.event.AsyncResult):
      rv = rv.get()
    return rv

  def __call__(self, players):
    assert len(players) == self.num_players
    return gevent.spawn(self.play, *players)