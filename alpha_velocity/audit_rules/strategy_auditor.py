from dataclasses import dataclass,field
@dataclass(frozen=True)
class AuditFinding: severity:str; code:str; message:str
@dataclass
class StrategySpecification:
 name:str; parameter_names:list[str]; uses_revised_fundamentals:bool=False; uses_close_to_trade_at_close:bool=False; assumes_midpoint_fills:bool=False; includes_delisted_securities:bool=False; includes_corporate_actions:bool=False; includes_borrow_costs:bool=False; allows_shorting:bool=False; includes_spread_and_impact:bool=False; uses_point_in_time_data:bool=False; hypotheses_tested:int=1; notes:dict=field(default_factory=dict)
class InstitutionalStrategyAuditor:
 def audit(self,s):
  f=[]
  def add(sev,code,msg):f.append(AuditFinding(sev,code,msg))
  if not s.uses_point_in_time_data:add('CRITICAL','PIT-001','No point-in-time guarantee; backtest is not credible.')
  if s.uses_revised_fundamentals:add('CRITICAL','PIT-002','Revised fundamentals create revision/look-ahead bias.')
  if s.uses_close_to_trade_at_close:add('CRITICAL','EXEC-001','Signal uses close and assumes same-close execution.')
  if s.assumes_midpoint_fills:add('HIGH','EXEC-002','Midpoint fills lack queue/fill-probability modeling.')
  if not s.includes_spread_and_impact:add('HIGH','EXEC-003','Spread and impact omitted.')
  if not s.includes_delisted_securities:add('CRITICAL','DATA-001','Survivorship bias: delisted securities excluded.')
  if not s.includes_corporate_actions:add('HIGH','DATA-002','Corporate actions omitted.')
  if s.allows_shorting and not s.includes_borrow_costs:add('CRITICAL','SHORT-001','Short strategy omits borrow availability/fees/recalls.')
  if s.hypotheses_tested>20:add('HIGH','STAT-001',f'{s.hypotheses_tested} hypotheses tested without correction.')
  if len(s.parameter_names)>20:add('CRITICAL','STAT-002',f'{len(s.parameter_names)} tunable parameters indicate severe curve-fitting risk.')
  return f
