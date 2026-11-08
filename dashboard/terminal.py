def format_snapshot(snapshot):
    if snapshot.best_bid is not None:
        best_bid = f"Rs. {snapshot.best_bid / 100:.2f}"
    else:
        best_bid = "Unavailable"

    if snapshot.best_ask is not None:
        best_ask = f"Rs. {snapshot.best_ask / 100:.2f}"
    else:
        best_ask = "Unavailable"

    if snapshot.best_bid is not None and snapshot.best_ask is not None:
        spread = f"Rs. {(snapshot.best_ask - snapshot.best_bid) / 100:.2f}"
    else:
        spread = "Unavailable"

    latency = snapshot.latency_ns / 1000

    return (
        f"Best bid: {best_bid}\n"
        f"Best ask: {best_ask}\n"
        f"Spread: {spread}\n"
        f"Orders processed: {snapshot.orders_processed}\n"
        f"Trades executed: {snapshot.trades_executed}\n"
        f"Latest latency: {latency:.2f} microseconds"
    )