
from monitoring.mock_events import sample_snapshots


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


if __name__ == "__main__":
    for snapshot in sample_snapshots():
        print(format_snapshot(snapshot))
        print("-" * 30)
