from dataclasses import dataclass
from alpha_velocity.event.models import FillEvent
class ExecutionReject(RuntimeError): pass
@dataclass(frozen=True)
class ExecutionAssumptions:
 commission_per_share:float=.005; minimum_commission:float=1.; half_spread_bps:float=8.; market_impact_coefficient:float=.10; max_participation_rate:float=.05; allow_same_bar_fill:bool=False
class EventDrivenExecutionModel:
 def __init__(self,assumptions=None): self.a=assumptions or ExecutionAssumptions()
 def try_fill(self,order,bar,prior_bar_volume):
  if order.symbol!=bar.symbol:return None
  if not self.a.allow_same_bar_fill and bar.timestamp<=order.timestamp:return None
  max_qty=int(max(0,prior_bar_volume*self.a.max_participation_rate))
  if max_qty<1: raise ExecutionReject('Insufficient modeled liquidity')
  qty=min(order.quantity,max_qty); side=1 if order.action=='BUY' else -1
  spread=bar.open*self.a.half_spread_bps/10000; impact=bar.open*self.a.market_impact_coefficient*(qty/max(prior_bar_volume,1))
  if order.order_type=='MKT': ref=bar.open
  elif order.order_type=='LMT':
   if order.limit_price is None: raise ExecutionReject('Missing limit')
   if not (bar.low<=order.limit_price if order.action=='BUY' else bar.high>=order.limit_price): return None
   ref=order.limit_price
  elif order.order_type=='STP':
   if order.stop_price is None: raise ExecutionReject('Missing stop')
   if not (bar.high>=order.stop_price if order.action=='BUY' else bar.low<=order.stop_price): return None
   ref=max(bar.open,order.stop_price) if order.action=='BUY' else min(bar.open,order.stop_price)
  else: raise ExecutionReject('Unsupported order type')
  px=ref+side*(spread+impact); comm=max(self.a.minimum_commission,qty*self.a.commission_per_share)
  return FillEvent(order.order_id,order.symbol,bar.timestamp,order.action,qty,px,comm,abs(px-ref))
