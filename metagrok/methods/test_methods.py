import unittest

import numpy as np
import torch

from metagrok import config

from metagrok.games.tictactoe import Policy
from metagrok.torch_utils.data import TTensorDictDataset

from metagrok.methods import learner
from metagrok.methods.vanilla_pg import VanillaPGUpdater
from metagrok.methods.ppo import PPOUpdater

config.set_cuda(False)

class MethodTest(unittest.TestCase):
  pass

class VanillaPGTest(MethodTest):
  def test_gradient_step_direction(self):
    'Test that good actions are boosted and bad actions are dampened'
    policy = Policy().type(config.tt())

    updater = VanillaPGUpdater(
        policy = policy,
        opt_lr = 1e-1,
        num_epochs = 1,
        vbatch_size = 2,
    )

    # Fake a training example
    policy = policy.eval()
    state = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 0]], dtype = int)
    mask = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1])

    results = policy.act(state, mask)

    features = policy.extract(state, mask)
    old_probs = results['probs']
    old_log_probs = results['log_probs']

    features = {
        k: np.repeat(np.expand_dims(v, axis = 0), 2, axis = 0)
        for k, v in features.iteritems()}

    advantages = np.array([-1., +1.], dtype = config.nt())
    log_probs = np.repeat(np.expand_dims(old_log_probs, axis = 0), 2, axis = 0)
    actions = np.array([4, 2], dtype = 'int64')

    extras = dict(
        advantages = advantages,
        log_probs = log_probs,
        actions = actions,
        value_preds = np.zeros(2, dtype = config.nt()),
        returns = np.zeros(2, dtype = config.nt()),
    )
    for k, v in features.iteritems():
      extras['features_' + k] = v
    learner.post_prepare(extras)
    extras['advantages'] = np.array([-1., +1.], dtype = config.nt())
    extras = TTensorDictDataset({k: torch.from_numpy(v) for k, v in extras.iteritems()})

    updater.update(extras)

    policy = policy.eval()
    results = policy.act(state, mask)
    new_probs = results['probs']
    new_log_probs = results['log_probs']

    # print new_probs - old_probs
    # print
    # print new_log_probs - old_log_probs

    self.assertTrue(np.allclose(np.log(old_probs), old_log_probs))
    self.assertTrue(np.allclose(np.log(new_probs), new_log_probs))
    self.assertGreater(new_probs[2], old_probs[2])
    self.assertLess(new_probs[4], old_probs[4])

class PPOTest(MethodTest):
  def test_gradient_step_direction(self):
    'Test that good actions are boosted and bad actions are dampened'
    policy = Policy().type(config.tt())

    updater = PPOUpdater(
        policy = policy,
        opt_lr = 1e-1,
        num_epochs = 1,
        vbatch_size = 2,
        clip_param = 0.1,
    )

    # Fake a training example
    policy = policy.eval()
    state = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 0]], dtype = int)
    mask = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1])

    results = policy.act(state, mask)

    features = policy.extract(state, mask)
    old_probs = results['probs']
    old_log_probs = results['log_probs']

    features = {
        k: np.repeat(np.expand_dims(v, axis = 0), 2, axis = 0)
        for k, v in features.iteritems()}

    advantages = np.array([-1., +1.], dtype = config.nt())
    log_probs = np.repeat(np.expand_dims(old_log_probs, axis = 0), 2, axis = 0)
    actions = np.array([4, 2], dtype = 'int64')

    extras = dict(
        advantages = advantages,
        log_probs = log_probs,
        actions = actions,
        value_preds = np.zeros(2, dtype = config.nt()),
        returns = np.zeros(2, dtype = config.nt()),
    )
    for k, v in features.iteritems():
      extras['features_' + k] = v
    learner.post_prepare(extras)
    extras['advantages'] = np.array([-1., +1.], dtype = config.nt())
    extras = TTensorDictDataset({k: torch.from_numpy(v) for k, v in extras.iteritems()})

    updater.update(extras)

    policy = policy.eval()
    results = policy.act(state, mask)
    new_probs = results['probs']
    new_log_probs = results['log_probs']

    # print new_probs - old_probs
    # print
    # print new_log_probs - old_log_probs

    self.assertTrue(np.allclose(np.log(old_probs), old_log_probs))
    self.assertTrue(np.allclose(np.log(new_probs), new_log_probs))
    self.assertGreater(new_probs[2], old_probs[2])
    self.assertLess(new_probs[4], old_probs[4])


if __name__ == '__main__':
  unittest.main()