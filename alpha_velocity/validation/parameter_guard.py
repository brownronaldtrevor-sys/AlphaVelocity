from dataclasses import dataclass
class CurveFitRiskError(RuntimeError): pass
@dataclass(frozen=True)
class ParameterAudit: parameter_count:int; effective_sample_size:int; observations_per_parameter:float; warning_level:str; message:str
class ParameterGuard:
 def __init__(self,minimum_observations_per_parameter=50.0,hard_max_parameters=20): self.minimum=minimum_observations_per_parameter; self.hard=hard_max_parameters
 def audit(self,parameter_count,effective_sample_size,strategy_name,refuse=True):
  ratio=float('inf') if parameter_count<=0 else effective_sample_size/parameter_count
  issues=[]
  if parameter_count>self.hard: issues.append(f'{parameter_count} parameters exceed hard limit {self.hard}')
  if parameter_count>0 and ratio<self.minimum: issues.append(f'only {ratio:.1f} effective observations per parameter')
  if issues:
   msg=f'Refusing strategy {strategy_name!r}: '+ '; '.join(issues)+'. Reduce parameters or pre-register the specification.'
   if refuse: raise CurveFitRiskError(msg)
   return ParameterAudit(parameter_count,effective_sample_size,ratio,'HIGH',msg)
  return ParameterAudit(parameter_count,effective_sample_size,ratio,'LOW' if ratio>=100 else 'MEDIUM','Parameter burden requires walk-forward and multiple-testing controls.')
