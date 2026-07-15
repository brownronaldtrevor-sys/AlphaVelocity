from datetime import datetime,timedelta
from alpha_velocity.market.bars import Bar
from alpha_velocity.signals.technical import compute_snapshot

def test_snapshot():
    bars=[]; p=10.0; start=datetime(2026,1,1)
    for i in range(70):
        p*=1.003; v=100000 if i<69 else 220000
        bars.append(Bar(start+timedelta(days=i),p*.99,p*1.01,p*.98,p,v))
    s=compute_snapshot(bars)
    assert 0<=s.composite_score<=100
    assert s.volume_ratio_20d>2
