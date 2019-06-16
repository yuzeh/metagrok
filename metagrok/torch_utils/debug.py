import gc
import sys

import torch

def memory_report():
  for obj in gc.get_objects():
    if torch.is_tensor(obj):
      print(type(obj), obj.size())