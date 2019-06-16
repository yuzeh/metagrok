import numpy
from scipy.misc import logsumexp

def softmax1d(arr):
  xs = arr - arr.max()
  xs = numpy.exp(xs)
  return xs / xs.sum()

def logsoftmax1d(arr):
  xs = arr - arr.max()
  return xs - logsumexp(xs)
