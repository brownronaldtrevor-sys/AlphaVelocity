from dataclasses import dataclass
from datetime import datetime
from typing import Any
class LookAheadViolation(RuntimeError): pass
@dataclass(frozen=True)
class TimestampedValue: value:Any; available_at:datetime; source_timestamp:datetime; revision_id:str|None=None
class PointInTimeStore:
 def __init__(self): self._data={}
 def add(self,key,item): self._data.setdefault(key,[]).append(item); self._data[key].sort(key=lambda x:x.available_at)
 def get_latest(self,key,as_of):
  rows=[x for x in self._data.get(key,[]) if x.available_at<=as_of]
  return rows[-1] if rows else None
 def require_latest(self,key,as_of):
  item=self.get_latest(key,as_of)
  if item is None: raise LookAheadViolation(f'No value for {key!r} available at {as_of.isoformat()}')
  return item
