from alpha_velocity.paper_auto.selector import ConservativePaperSelector
from alpha_velocity.paper_auto.planner import PaperOrderPlanner


def sample_row(symbol="ABC", composite=70, state="WATCH"):
    return {
        "symbol": symbol,
        "rank": 1,
        "technical_composite": composite,
        "close": 10.0,
        "volume_ratio_20d": 1.2,
        "state": state,
        "atr_pct_14d": 0.04,
        "trend_score": 80,
    }


def test_selector_rejects_weak_names():
    selector = ConservativePaperSelector()
    assert selector.select([sample_row(composite=30)]) == []


def test_selector_caps_position_count():
    selector = ConservativePaperSelector(max_positions=2)
    rows = [
        {**sample_row(f"S{i}"), "rank": i}
        for i in range(5)
    ]
    assert len(selector.select(rows)) == 2


def test_planner_creates_buy_order():
    selection = ConservativePaperSelector().select([sample_row()])[0]
    orders = PaperOrderPlanner().build_orders(
        [selection],
        account_equity=10000,
        current_positions={},
    )
    assert len(orders) == 1
    assert orders[0].action == "BUY"
    assert orders[0].stop_price is not None
    assert orders[0].target_price is not None
