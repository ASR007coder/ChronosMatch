
from engine.matching_engine import MatchingEngine
from engine.models import BUY, SELL, Order
from monitoring.metrics import Metrics


def test_engine_results_update_monitoring_metrics():
    engine = MatchingEngine()
    metrics = Metrics()

    # Add a resting sell order at 50000 paise.
    sell_order = Order(
        order_id=1, sequence=1, side=SELL,
        price=50000, quantity=2
    )
    metrics.record_generated()
    trades = engine.submit_order(sell_order)
    metrics.record_processed()
    metrics.record_trades(len(trades))

    # A matching buy order should execute against the resting sell.
    buy_order = Order(
        order_id=2, sequence=2, side=BUY,
        price=50000, quantity=1
    )
    metrics.record_generated()
    trades = engine.submit_order(buy_order)
    metrics.record_processed()
    metrics.record_trades(len(trades))

    assert engine.orders_processed == 2
    assert engine.trades_executed == 1
    assert metrics.orders_generated == 2
    assert metrics.orders_processed == 2
    assert metrics.trades_executed == 1
    assert trades[0].price == 50000
    assert trades[0].quantity == 1
