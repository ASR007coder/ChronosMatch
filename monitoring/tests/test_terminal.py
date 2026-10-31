
from monitoring.mock_events import (
    DashboardSnapshot,
    sample_snapshots,
)
from dashboard.terminal import format_snapshot


def test_price_formatting():
    output = format_snapshot(sample_snapshots()[0])

    assert "Best bid: Rs. 499.00" in output
    assert "Best ask: Rs. 500.00" in output


def test_spread_calculation():
    output = format_snapshot(sample_snapshots()[0])

    assert "Spread: Rs. 1.00" in output


def test_missing_bid():
    snapshot = DashboardSnapshot(None, 50000, 100, 20, 25000)
    output = format_snapshot(snapshot)

    assert "Best bid: Unavailable" in output
    assert "Spread: Unavailable" in output


def test_missing_ask():
    snapshot = DashboardSnapshot(49900, None, 100, 20, 25000)
    output = format_snapshot(snapshot)

    assert "Best ask: Unavailable" in output
    assert "Spread: Unavailable" in output


def test_latency_conversion():
    output = format_snapshot(sample_snapshots()[0])

    assert "Latest latency: 25.00 microseconds" in output

def test_mock_snapshots():
    snapshots = sample_snapshots()
    assert len(snapshots) == 3


def test_mock_counters_increase():
    snapshots = sample_snapshots()
    orders = [s.orders_processed for s in snapshots]
    trades = [s.trades_executed for s in snapshots]

    assert orders == sorted(orders)
    assert trades == sorted(trades)
    assert len(set(orders)) == len(orders)
    assert len(set(trades)) == len(trades)


def test_mock_latency_is_non_negative():
    snapshots = sample_snapshots()
    assert all(s.latency_ns >= 0 for s in snapshots)


def test_mock_bid_does_not_exceed_ask():
    snapshots = sample_snapshots()
    assert all(
        s.best_bid <= s.best_ask
        for s in snapshots
        if s.best_bid is not None and s.best_ask is not None
    )


def test_zero_trades():
    snapshot = DashboardSnapshot(49900, 50000, 100, 0, 25000)
    output = format_snapshot(snapshot)
    assert "Trades executed: 0" in output
