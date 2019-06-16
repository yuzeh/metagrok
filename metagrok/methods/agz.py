# -*- coding: utf-8 -*-

from metagrok.methods import updater

class AGZUpdater(updater.PolicyUpdater):
  '''
  Implements the dual policy + value objective that is described in the AlphaGo Zero Paper:

  (p, v) := f_θ(s),

  loss := η (z - v)^2 - π' log(p) + λ ||θ||^2

  Where:
    - p: policy output by model
    - v: value prediction output by model
    - θ: parameters of model
    - f_θ: model function
    - s: state input of sample
    - z: value output of sample
    - π: ground truth policy (one-hot for supervised, search probs for MTCS) output of sample

  Hyperparams:
    - η: weight factor of value component of model
    - λ: regularization factor
  '''

  def __init__(self, **kwargs):
    super(AGZUpdater, self).__init__(**kwargs)
    self._value_loss_weight = kwargs['value_loss_weight']

    self._eb_keys = {'value', 'log_probs', 'probs'}

  def batch_update(self, policy, features, probs, returns, actions, **kwargs):
    eta = self._value_loss_weight

    res = policy.evaluate_batch(features, actions, keys = self._eb_keys)
    pred_value = res['value']
    pred_log_probs = res['log_probs']

    value_loss = (pred_value - returns.squeeze(-1)).pow(2).mean()
    action_loss = -(probs * pred_log_probs).mean()

    best_action = res['probs'].argmax(-1)
    acc = (best_action == actions.squeeze().type_as(best_action)).float().mean()

    return {
      'value_loss': eta * value_loss,
      'action_loss': action_loss,
      '_action_acc': acc,
    }
