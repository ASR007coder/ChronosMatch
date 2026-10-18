
from unittest.mock import Mock

from engine.models import BUY, SELL, Order
from pipeline.runner import run_orders


def test_pipeline_processes_orders_and_records_trades():
    orders = [
        Order(
            order_id=1, sequence=1, side=SELL,
            price=50000, quantity=2
        ),
        Order(
            order_id=2, sequence=2, side=BUY,
            price=50000, quantity=1
        ),
    ]

    metrics, trades = run_orders(orders)

    assert metrics.orders_generated == 2
    assert metrics.orders_processed == 2
    assert metrics.trades_executed == 1
    assert metrics.errors == 0
    assert len(trades) == 1


def test_pipeline_handles_invalid_orders():
    orders = [
        Order(
            order_id=1, sequence=1, side=SELL,
            price=50000, quantity=2
        ),
        Order(
            order_id=2, sequence=2, side=BUY,
            price=50000, quantity=1
        ),
    ]

    engine = Mock()
    engine.submit_order.side_effect = [
        [],
        ValueError("simulated invalid order"),
    ]

    metrics, trades = run_orders(orders, engine=engine)

    assert metrics.orders_generated == 2
    assert metrics.orders_processed == 1
    assert metrics.errors == 1
    assert metrics.trades_executed == 0
    assert trades == []
