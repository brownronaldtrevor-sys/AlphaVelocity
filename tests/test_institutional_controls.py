from datetime import datetime,timedelta
import pytest
from alpha_velocity.validation.anti_lookahead import PointInTimeStore,TimestampedValue,LookAheadViolation
from alpha_velocity.validation.parameter_guard import ParameterGuard,CurveFitRiskError
from alpha_velocity.event.models import MarketBarEvent,OrderEvent
from alpha_velocity.simulation.execution import EventDrivenExecutionModel

def test_future_data_blocked():
 s=PointInTimeStore(); t=datetime(2026,1,1); s.add('EPS',TimestampedValue(1,t+timedelta(days=10),t))
 with pytest.raises(LookAheadViolation):s.require_latest('EPS',t+timedelta(days=5))
def test_curvefit_refused():
 with pytest.raises(CurveFitRiskError):ParameterGuard().audit(25,500,'OVERFIT')
def test_same_bar_fill_blocked():
 t=datetime(2026,1,1); o=OrderEvent('1','S','ABC',t,'BUY',10,'MKT'); b=MarketBarEvent('ABC',t,10,11,9,10.5,100000)
 assert EventDrivenExecutionModel().try_fill(o,b,100000) is None
