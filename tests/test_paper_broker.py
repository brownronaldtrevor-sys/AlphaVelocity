from alpha_velocity.paper.broker import SimulatedBroker
from alpha_velocity.paper.models import PaperOrder

def test_buy_and_sell(tmp_path):
    broker = SimulatedBroker(str(tmp_path / "acct.json"), starting_cash=10000, slippage_bps=0)
    fill = broker.execute(PaperOrder("ABC", "BUY", 100, 10, "test"))
    assert fill is not None
    assert broker.account.positions["ABC"].quantity == 100
    fill2 = broker.execute(PaperOrder("ABC", "SELL", 40, 11, "test"))
    assert fill2 is not None
    assert broker.account.positions["ABC"].quantity == 60
