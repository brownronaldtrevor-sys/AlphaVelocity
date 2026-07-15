class SimulationClock:
 def __init__(self): self._now=None
 @property
 def now(self):
  if self._now is None: raise RuntimeError('Clock has not started')
  return self._now
 def advance(self,timestamp):
  if self._now is not None and timestamp<self._now: raise ValueError('Clock cannot move backward')
  self._now=timestamp
