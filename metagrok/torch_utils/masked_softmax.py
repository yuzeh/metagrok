import unittest

import numpy as np

import torch
import torch.autograd as ag
import torch.nn.functional as F

class MaskedSoftmaxAndLogSoftmax(ag.Function):
  def __init__(self, dtype = torch.FloatTensor):
    super(MaskedSoftmaxAndLogSoftmax, self).__init__()
    self._dtype = dtype

  def forward(self, xs, mask):
    '''
    xs: (?, num_actions)
    mask: (?, num_actions)

    output: (?, num_actions)
    '''
    maxes = torch.max(xs + torch.log(mask), 1, keepdim = True)[0]
    masked_exp_xs = torch.exp(xs - maxes) * mask
    normalization_factor = masked_exp_xs.sum(1, keepdim = True)
    probs = masked_exp_xs / normalization_factor
    log_probs = (xs - maxes - torch.log(normalization_factor)) * mask

    self.save_for_backward(probs, mask)
    return probs, log_probs

  def backward(self, grad_probs, grad_log_probs):
    probs, mask = self.saved_tensors

    num_actions = grad_probs.size()[1]
    w1 = (probs * grad_probs).unsqueeze(0).unsqueeze(-1)
    w2 = torch.eye(num_actions).type(self._dtype).unsqueeze(0)
    if grad_probs.is_cuda:
      w2 = w2.cuda()
    w2 = (w2 - probs.unsqueeze(-1))

    grad1 = torch.matmul(w2, w1).squeeze(0).squeeze(-1)

    w1 = grad_log_probs
    sw1 = (mask * grad_log_probs).sum(1, keepdim = True)
    grad2 = (w1 * mask - probs * sw1)
    return grad1 + grad2, None

def apply(xs, mask, dtype = torch.FloatTensor):
  return MaskedSoftmaxAndLogSoftmax(dtype)(xs, mask)

class MaskedSoftmaxTest(unittest.TestCase):
  def test_unmasked_case(self):
    for i in range(10):
      x = ag.Variable(torch.randn(3, 7).double())
      m = ag.Variable(torch.ones(3, 7).double())

      softmax_expected = F.softmax(x, -1)
      logsoftmax_expected = F.log_softmax(x, -1)
      softmax_actual, logsoftmax_actual = apply(x, m, dtype = torch.DoubleTensor)

      np.testing.assert_allclose(softmax_expected.data.numpy(), softmax_actual.data.numpy())
      np.testing.assert_allclose(logsoftmax_expected.data.numpy(), logsoftmax_actual.data.numpy())

  def test_masked_case(self):
    for i in range(10):
      x = ag.Variable(torch.randn(1, 5).double())
      m = ag.Variable(torch.ByteTensor([1, 1, 0, 1, 1]))
      y = x.masked_select(m)
      mask = m.double()

      softmax_expected = F.softmax(y, -1)
      logsoftmax_expected = F.log_softmax(y, -1)
      softmax_actual, logsoftmax_actual = apply(x, mask, dtype = torch.DoubleTensor)

      self.assertAlmostEqual(softmax_actual.data[0][2], 0.0)
      self.assertAlmostEqual(logsoftmax_actual.data[0][2], 0.0)

      softmax_actual = softmax_actual.masked_select(m)
      logsoftmax_actual = logsoftmax_actual.masked_select(m)

      np.testing.assert_allclose(softmax_expected.data.numpy(), softmax_actual.data.numpy())
      np.testing.assert_allclose(logsoftmax_expected.data.numpy(), logsoftmax_actual.data.numpy())

if __name__ == '__main__':
  unittest.main()
