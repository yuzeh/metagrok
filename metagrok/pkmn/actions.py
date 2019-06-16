from collections import namedtuple

_Action = namedtuple('Action', 'type slot target modifier')
_Action.__new__.__defaults__ = (None,) * len(_Action._fields)

class Action(_Action):
  __slots__ = ()
  def __str__(self):
    if self.modifier:
      return '%s %s %s' % (self.type, self.slot, self.modifier)
    return '%s %s' % (self.type, self.slot)

GEN7SINGLES = tuple(
  [Action(type = 'move', slot = i + 1) for i in range(4)]
  + [Action(type = 'switch', slot = i + 1) for i in range(6)]
  + [Action(type = 'move', slot = i + 1, modifier = 'mega') for i in range(4)]
  + [Action(type = 'move', slot = i + 1, modifier = 'zmove') for i in range(4)]
  + [Action(type = 'move', slot = i + 1, modifier = 'ultra') for i in range(4)]
)