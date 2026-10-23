
from monitoring.mock_events import sample_snapshots
from engine.matching_engine import MatchingEngine
from engine.models import BUY, SELL, Order
from monitoring.metrics import Metrics


def format_snapshot(snapshot):
    bid = (
        "Unavailable"
        if snapshot.best_bid is None
        else f"Rs. {snapshot.best_bid / 100:.2f}"
    )

    ask = (
        "Unavailable"
        if snapshot.best_ask is None
        else f"Rs. {snapshot.best_ask / 100:.2f}"
    )

    if snapshot.best_bid is None or snapshot.best_ask is None:
        spread = "Unavailable"
    else:
        spread = f"Rs. {(snapshot.best_ask - snapshot.best_bid) / 100:.2f}"

    latency_us = snapshot.latency_ns / 1000

    return (
        "CHRONOSMATCH - MOCK DATA\n"
        f"Best bid: {bid}\n"
        f"Best ask: {ask}\n"
        f"Spread: {spread}\n"
        f"Orders processed: {snapshot.orders_processed}\n"
        f"Trades executed: {snapshot.trades_executed}\n"
        f"Latest latency: {latency_us:.2f} microseconds\n"
    )


def run_demo():
    """Run a small simulation using the real matching engine."""
    engine = MatchingEngine()
    metrics = Metrics()

    orders = [
        Order(1, 1, SELL, 50000, 2),
        Order(2, 2, BUY, 50000, 1),
        Order(3, 3, BUY, 49000, 3),
    ]

    for order in orders:
        metrics.record_generated()
        try:
            trades = engine.submit_order(order)
        except ValueError:
            metrics.record_error()
            continue

        metrics.record_processed()
        metrics.record_trades(len(trades))

    best_bid = engine.best_bid()
    best_ask = engine.best_ask()

    print("=== CHRONOSMATCH - REAL ENGINE DEMO ===")
    print("Best bid:", best_bid)
    print("Best ask:", best_ask)
    print("Orders generated:", metrics.orders_generated)
    print("Orders processed:", engine.orders_processed)
    print("Trades executed:", engine.trades_executed)
    print("Monitoring errors:", metrics.errors)


if __name__ == "__main__":
    run_demo()
