import copy
import unittest

from metagrok.pkmn import parser
from metagrok.pkmn.engine.test_engine import state_begin, req_begin
from metagrok.pkmn.engine.core import postprocess
from metagrok.pkmn.models import v2_repro as v2
from metagrok.pkmn.models import v4_speedup as v4

class ModelsTest(unittest.TestCase):
  def test_v4(self):
    policy = v4.Policy()

    state = copy.deepcopy(state_begin)
    req = copy.deepcopy(req_begin)
    postprocess(state, req)

    candidates = parser.parse_valid_actions(req)

    rv = policy.act(state, candidates)

    self.assertSetEqual(set(rv.keys()), {'probs', 'log_probs', 'value_pred'})

  def test_v2(self):
    policy = v2.Policy()

    state = copy.deepcopy(state_begin)
    req = copy.deepcopy(req_begin)
    postprocess(state, req)

    candidates = parser.parse_valid_actions(req)

    rv = policy.act(state, candidates)

    self.assertSetEqual(set(rv.keys()), {'probs', 'log_probs', 'value_pred'})
