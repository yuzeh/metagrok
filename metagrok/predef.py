# This file needs to be imported at the top of every process that either
#   - uses gevent
#   - uses torch
import torch; assert torch
from gevent import monkey; monkey.patch_all()

import logging

logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
