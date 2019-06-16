import unittest

from metagrok.pkmn.reward_shaper import RewardShaper
from metagrok import jsons

def load_test_data():
  return jsons.load('test-data/reward-shaper-tests.jsons')

class RewardShaperTest(unittest.TestCase):
  def test_faint(self):
    data = load_test_data()
    shaper = RewardShaper(faint = 0.1)
    shaper(data)
    self.assertAlmostEqual(data[-2]['reward'], -0.1)
    self.assertAlmostEqual(data[-9]['reward'], +0.1)

  def test_fail(self):
    data = load_test_data()
    shaper = RewardShaper(fail = 0.02)
    shaper(data)
    self.assertAlmostEqual(data[-3]['reward'], -0.02)

  def test_resisted(self):
    data = load_test_data()
    shaper = RewardShaper(resisted = 0.01)
    shaper(data)
    self.assertAlmostEqual(data[-9]['reward'], -0.01)

  def test_supereffective(self):
    data = load_test_data()
    shaper = RewardShaper(supereffective = 0.01)
    shaper(data)
    self.assertAlmostEqual(data[-10]['reward'], 0.01)

if __name__ == '__main__':
  unittest.main()