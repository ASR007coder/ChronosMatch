# backend\tests\test_ipc_pipeline_integration.py
from backend.pipeline.ipc_pipeline import process_orders


def test_ipc_pipeline_matches_orders_and_returns_trades():
    orders = [
        {
            "order_id": 1,
            "sequence": 1,
            "price": 10000,
            "timestamp_ns": 100,
            "quantity": 5,
            "side": 0,  # BUY
        },
        {
            "order_id": 2,
            "sequence": 2,
            "price": 10000,
            "timestamp_ns": 200,
            "quantity": 3,
            "side": 1,  # SELL
        },
    ]

    result = process_orders(orders)

    assert result["orders_received"] == 2
    assert result["orders_processed"] == 2
    assert result["trades_executed"] == 1

    assert result["trades"] == [
        {
            "trade_id": 1,
            "buy_order_id": 1,
            "sell_order_id": 2,
            "price": 10000,
            "quantity": 3,
            "sequence": 2,
        }
    ]

    assert result["order_book"] == {
        "bids": [(10000, 2)],
        "asks": [],
    }
