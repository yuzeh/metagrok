import unittest

from .scheduler import Scheduler

class SchedulerTest(unittest.TestCase):
  def test_scheduler(self):
    schedule = [
      {"value": 'a', "until": 100},
      {"value": 'b', "until": 200},
      {"value": 'c', "until": 300},
      {"value": 'd', "until": 400},
      {"value": 'e', "until": 500},
    ]
    scheduler = Scheduler(schedule)

    self.assertEqual('a', scheduler.select(0))
    self.assertEqual('a', scheduler.select(99))
    self.assertEqual('b', scheduler.select(100))
    self.assertEqual('b', scheduler.select(199))
    self.assertEqual('c', scheduler.select(200))
    self.assertEqual('d', scheduler.select(399))
    self.assertEqual('e', scheduler.select(400))
    self.assertEqual('e', scheduler.select(500))
    self.assertEqual('e', scheduler.select(501))

if __name__ == '__main__':
  unittest.main()