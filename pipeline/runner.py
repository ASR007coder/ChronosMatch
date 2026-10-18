
from engine.matching_engine import MatchingEngine
from monitoring.metrics import Metrics


def run_orders(orders, engine=None, metrics=None):
    """Process orders and record engine results and errors."""
    if engine is None:
        engine = MatchingEngine()

    if metrics is None:
        metrics = Metrics()

    all_trades = []

    for order in orders:
        metrics.record_generated()

        try:
            trades = engine.submit_order(order)
        except ValueError:
            metrics.record_error()
            continue

        metrics.record_processed()
        metrics.record_trades(len(trades))
        all_trades.extend(trades)

    return metrics, all_trades
