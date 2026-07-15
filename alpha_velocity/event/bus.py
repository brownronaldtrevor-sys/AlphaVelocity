import heapq
from dataclasses import dataclass,field
from alpha_velocity.event.models import Event
@dataclass(order=True)
class _Queued: sort_key:tuple; event:Event=field(compare=False)
class EventBus:
 def __init__(self): self._queue=[]
 def publish(self,event): heapq.heappush(self._queue,_Queued((event.timestamp,event.sequence),event))
 def __iter__(self):
  while self._queue: yield heapq.heappop(self._queue).event
