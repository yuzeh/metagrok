import v1_repro
import v2_repro
import v3_capacity

class V1(v1_repro.Policy):
  pass

class V2(v2_repro.Policy):
  pass

V3Half = v3_capacity.HalfCapacity
V3Double = v3_capacity.DoubleCapacity
V3Quad = v3_capacity.QuadCapacity