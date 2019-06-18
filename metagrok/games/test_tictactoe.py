import unittest

from metagrok.games.tictactoe import Game

class SequencePlayer(object):
  def __init__(self, seq):
    self._seq = seq
    self._idx = 0

  def update(self, opcode, data):
    if opcode == 'end':
      self.result = data

  def action(self):
    action = self._seq[self._idx]
    self._idx += 1
    return action

class TicTacToeTest(unittest.TestCase):
  def setUp(self):
    self._dangerous = False
    self._check_candidates = True

  def test_alternating_play(self):
    p1 = SequencePlayer([0, 2, 4, 6, 8])
    p2 = SequencePlayer([1, 3, 5, 7,  ])
    game = Game(dangerous = self._dangerous, fix_ordering = True)

    buf = game.play(p1, p2)['buf']
    states, candidates = list(zip(*buf))

    self.assertEqual(8, len(buf))
    self.assertEqual([ 0, 0, 0, 0, 0, 0, 0, 0, 0], states[0])
    self.assertEqual([+1, 0, 0, 0, 0, 0, 0, 0, 0], states[1])
    self.assertEqual([+1,-1, 0, 0, 0, 0, 0, 0, 0], states[2])
    self.assertEqual([+1,-1,+1, 0, 0, 0, 0, 0, 0], states[3])
    self.assertEqual([+1,-1,+1,-1, 0, 0, 0, 0, 0], states[4])
    self.assertEqual([+1,-1,+1,-1,+1, 0, 0, 0, 0], states[5])
    self.assertEqual([+1,-1,+1,-1,+1,-1, 0, 0, 0], states[6])
    self.assertEqual([+1,-1,+1,-1,+1,-1,+1, 0, 0], states[7])

    if self._check_candidates:
      self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1, 1], candidates[0])
      self.assertEqual([0, 1, 1, 1, 1, 1, 1, 1, 1], candidates[1])
      self.assertEqual([0, 0, 1, 1, 1, 1, 1, 1, 1], candidates[2])
      self.assertEqual([0, 0, 0, 1, 1, 1, 1, 1, 1], candidates[3])
      self.assertEqual([0, 0, 0, 0, 1, 1, 1, 1, 1], candidates[4])
      self.assertEqual([0, 0, 0, 0, 0, 1, 1, 1, 1], candidates[5])
      self.assertEqual([0, 0, 0, 0, 0, 0, 1, 1, 1], candidates[6])
      self.assertEqual(None, candidates[7])

    self.assertEqual('winner', p1.result)
    self.assertEqual('loser', p2.result)

  def test_racing_play(self):
    p1 = SequencePlayer([0, 1, 2, 3, 4])
    p2 = SequencePlayer([8, 7, 6, 5,  ])
    game = Game(dangerous = self._dangerous, fix_ordering = True)

    buf = game.play(p1, p2)['buf']
    states, candidates = list(zip(*buf))

    self.assertEqual(6, len(buf))
    self.assertEqual([ 0, 0, 0, 0, 0, 0, 0, 0, 0], states[0])
    self.assertEqual([+1, 0, 0, 0, 0, 0, 0, 0, 0], states[1])
    self.assertEqual([+1, 0, 0, 0, 0, 0, 0, 0,-1], states[2])
    self.assertEqual([+1,+1, 0, 0, 0, 0, 0, 0,-1], states[3])
    self.assertEqual([+1,+1, 0, 0, 0, 0, 0,-1,-1], states[4])
    self.assertEqual([+1,+1,+1, 0, 0, 0, 0,-1,-1], states[5])

    if self._check_candidates:
      self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1, 1], candidates[0])
      self.assertEqual([0, 1, 1, 1, 1, 1, 1, 1, 1], candidates[1])
      self.assertEqual([0, 1, 1, 1, 1, 1, 1, 1, 0], candidates[2])
      self.assertEqual([0, 0, 1, 1, 1, 1, 1, 1, 0], candidates[3])
      self.assertEqual([0, 0, 1, 1, 1, 1, 1, 0, 0], candidates[4])
      self.assertEqual(None, candidates[5])

    self.assertEqual('winner', p1.result)
    self.assertEqual('loser', p2.result)

  def test_p2_wins(self):
    p1 = SequencePlayer([0, 2, 7, 6, 1])
    p2 = SequencePlayer([3, 4, 5, 8])
    game = Game(dangerous = self._dangerous, fix_ordering = True)

    buf = game.play(p1, p2)['buf']
    states, candidates = list(zip(*buf))

    self.assertEqual(7, len(buf))
    self.assertEqual([ 0, 0, 0, 0, 0, 0, 0, 0, 0], states[0])
    self.assertEqual([+1, 0, 0, 0, 0, 0, 0, 0, 0], states[1])
    self.assertEqual([+1, 0, 0,-1, 0, 0, 0, 0, 0], states[2])
    self.assertEqual([+1, 0,+1,-1, 0, 0, 0, 0, 0], states[3])
    self.assertEqual([+1, 0,+1,-1,-1, 0, 0, 0, 0], states[4])
    self.assertEqual([+1, 0,+1,-1,-1, 0, 0,+1, 0], states[5])
    self.assertEqual([+1, 0,+1,-1,-1,-1, 0,+1, 0], states[6])

    if self._check_candidates:
      self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1, 1], candidates[0])
      self.assertEqual([0, 1, 1, 1, 1, 1, 1, 1, 1], candidates[1])
      self.assertEqual([0, 1, 1, 0, 1, 1, 1, 1, 1], candidates[2])
      self.assertEqual([0, 1, 0, 0, 1, 1, 1, 1, 1], candidates[3])
      self.assertEqual([0, 1, 0, 0, 0, 1, 1, 1, 1], candidates[4])
      self.assertEqual([0, 1, 0, 0, 0, 1, 1, 0, 1], candidates[5])
      self.assertEqual(None, candidates[6])

    self.assertEqual('winner', p2.result)
    self.assertEqual('loser', p1.result)

  def test_tie(self):
    p1 = SequencePlayer([0, 2, 5, 6, 7])
    p2 = SequencePlayer([1, 3, 4, 8])
    game = Game(dangerous = self._dangerous, fix_ordering = True)

    buf = game.play(p1, p2)['buf']
    states, candidates = list(zip(*buf))

    self.assertEqual(10, len(buf))
    self.assertEqual([ 0, 0, 0, 0, 0, 0, 0, 0, 0], states[0])
    self.assertEqual([+1, 0, 0, 0, 0, 0, 0, 0, 0], states[1])
    self.assertEqual([+1,-1, 0, 0, 0, 0, 0, 0, 0], states[2])
    self.assertEqual([+1,-1,+1, 0, 0, 0, 0, 0, 0], states[3])
    self.assertEqual([+1,-1,+1,-1, 0, 0, 0, 0, 0], states[4])
    self.assertEqual([+1,-1,+1,-1, 0,+1, 0, 0, 0], states[5])
    self.assertEqual([+1,-1,+1,-1,-1,+1, 0, 0, 0], states[6])
    self.assertEqual([+1,-1,+1,-1,-1,+1,+1, 0, 0], states[7])
    self.assertEqual([+1,-1,+1,-1,-1,+1,+1, 0,-1], states[8])
    self.assertEqual([+1,-1,+1,-1,-1,+1,+1,+1,-1], states[9])

    if self._check_candidates:
      self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1, 1], candidates[0])
      self.assertEqual([0, 1, 1, 1, 1, 1, 1, 1, 1], candidates[1])
      self.assertEqual([0, 0, 1, 1, 1, 1, 1, 1, 1], candidates[2])
      self.assertEqual([0, 0, 0, 1, 1, 1, 1, 1, 1], candidates[3])
      self.assertEqual([0, 0, 0, 0, 1, 1, 1, 1, 1], candidates[4])
      self.assertEqual([0, 0, 0, 0, 1, 0, 1, 1, 1], candidates[5])
      self.assertEqual([0, 0, 0, 0, 0, 0, 1, 1, 1], candidates[6])
      self.assertEqual([0, 0, 0, 0, 0, 0, 0, 1, 1], candidates[7])
      self.assertEqual([0, 0, 0, 0, 0, 0, 0, 1, 0], candidates[8])
      self.assertEqual(None, candidates[9])

    self.assertEqual('tie', p2.result)
    self.assertEqual('tie', p1.result)

  def test_dangerous_mode_valid_gameplay(self):
    self._dangerous = True
    self._check_candidates = False

    self.test_alternating_play()
    self.test_racing_play()
    self.test_p2_wins()
    self.test_tie()

if __name__ == '__main__':
  unittest.main()
