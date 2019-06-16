import v2_repro

def HalfCapacity():
  return v2_repro.Policy(embed_size = 16, pkmn_size = 32)

def DoubleCapacity():
  return v2_repro.Policy(embed_size = 64, pkmn_size = 128)
  
def QuadCapacity():
  return v2_repro.Policy(embed_size = 128, pkmn_size = 256)

def Policy2x2():
  return v2_repro.Policy(embed_size = 64, pkmn_size = 128, depth = 2)

#def Policy2x2_1():
#  return v2_repro.Policy(embed_size = 128, pkmn_size = 256, depth = 2, embed_depth = 1)

def Policy4x2():
  return v2_repro.Policy(embed_size = 128, pkmn_size = 256, depth = 2, embed_depth = 1)