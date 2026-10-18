# backend/pipeline/fake_simulator.py

import time


def generate_orders(total_orders: int) -> list[dict]:
    """Generate fake buy and sell orders for local testing."""

    orders = []

    for i in range(total_orders):
        orders.append({
            "order_id": i + 1,
            "sequence": i + 1,
            "price": 10000 + (i % 10) * 100,
            "timestamp_ns": time.time_ns(),
            "quantity": (i % 5) + 1,
            "side": i % 2,  # 0 = BUY, 1 = SELL
        })

    return orders
