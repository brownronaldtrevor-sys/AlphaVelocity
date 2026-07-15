from datetime import datetime, timedelta

from alpha_velocity.market.bars import Bar
from alpha_velocity.research.report import _candidate
from alpha_velocity.signals.technical import compute_snapshot


def test_research_candidate_has_no_expected_return_claim():
    bars = []
    price = 10.0
    for i in range(70):
        price *= 1.002
        bars.append(Bar(datetime(2025, 1, 1) + timedelta(days=i), price, price*1.01, price*.99, price, 100000))
    snap = compute_snapshot(bars)
    candidate = _candidate("TEST", snap)
    assert candidate.proposed_weight_pct == 0
    assert candidate.expected_return_pct == 0
    assert candidate.uncertainty >= 80
