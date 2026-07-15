from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
class EventType(str,Enum):
 MARKET_BAR='MARKET_BAR'; SIGNAL='SIGNAL'; ORDER='ORDER'; FILL='FILL'; TIMER='TIMER'; RISK='RISK'; CORPORATE_ACTION='CORPORATE_ACTION'
@dataclass(frozen=True)
class Event: event_type:EventType; timestamp:datetime; sequence:int; payload:Any
@dataclass(frozen=True)
class MarketBarEvent:
 symbol:str; timestamp:datetime; open:float; high:float; low:float; close:float; volume:float; is_final:bool=True
@dataclass(frozen=True)
class SignalEvent:
 strategy_id:str; symbol:str; timestamp:datetime; side:str; strength:float; reference_price:float; metadata:dict[str,Any]=field(default_factory=dict)
@dataclass(frozen=True)
class OrderEvent:
 order_id:str; strategy_id:str; symbol:str; timestamp:datetime; action:str; quantity:int; order_type:str; limit_price:float|None=None; stop_price:float|None=None
@dataclass(frozen=True)
class FillEvent:
 order_id:str; symbol:str; timestamp:datetime; action:str; quantity:int; fill_price:float; commission:float; slippage:float
