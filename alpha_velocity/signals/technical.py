from dataclasses import dataclass
from statistics import mean, pstdev
from alpha_velocity.market.bars import Bar

@dataclass(frozen=True)
class TechnicalSnapshot:
    close: float
    return_5d: float
    return_20d: float
    distance_from_20d_high: float
    volume_ratio_20d: float
    atr_pct_14d: float
    volatility_20d: float
    trend_score: float
    breakout_score: float
    volume_score: float
    reversal_score: float
    composite_score: float
    state: str

def _pct(a,b): return 0.0 if b==0 else a/b-1.0
def _clip(x): return max(0.0,min(100.0,x))

def compute_snapshot(bars:list[Bar])->TechnicalSnapshot:
    if len(bars)<60: raise ValueError('At least 60 daily bars are required.')
    closes=[b.close for b in bars]; vols=[max(b.volume,0.0) for b in bars]; last=bars[-1]
    r5=_pct(last.close,closes[-6]); r20=_pct(last.close,closes[-21])
    hi20=max(b.high for b in bars[-20:]); dist=_pct(last.close,hi20)
    avgv=mean(vols[-21:-1]) or 1.0; vr=vols[-1]/avgv
    trs=[]
    for prev,cur in zip(bars[-15:-1],bars[-14:]):
        trs.append(max(cur.high-cur.low,abs(cur.high-prev.close),abs(cur.low-prev.close)))
    atr=(mean(trs)/last.close) if last.close else 0.0
    rets=[_pct(closes[i],closes[i-1]) for i in range(len(closes)-20,len(closes))]
    vol20=pstdev(rets) if len(rets)>1 else 0.0
    ma10=mean(closes[-10:]); ma20=mean(closes[-20:]); ma50=mean(closes[-50:])
    trend=_clip(50+(18 if last.close>ma10 else -12)+(16 if ma10>ma20 else -10)+(16 if ma20>ma50 else -10))
    breakout=_clip(65+dist*500+r5*180+max(0.0,vr-1.0)*15)
    volume=_clip(35+vr*28+max(r5,0.0)*120)
    reversal=_clip(45+max(-r20,0.0)*120+max(r5,0.0)*220+max(vr-1.0,0.0)*12)
    comp=_clip(.30*trend+.30*breakout+.20*volume+.20*reversal)
    state='PAPER_BUY_CANDIDATE' if comp>=78 and breakout>=70 else 'WATCH' if comp>=65 else 'AVOID_OR_EXIT_REVIEW' if comp<=35 else 'NEUTRAL'
    return TechnicalSnapshot(last.close,r5,r20,dist,vr,atr,vol20,trend,breakout,volume,reversal,comp,state)
