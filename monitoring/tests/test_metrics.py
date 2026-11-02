
from monitoring.metrics import Metrics


def test_initial_counters():
    metrics = Metrics()
    assert metrics.orders_generated == 0
    assert metrics.orders_processed == 0
    assert metrics.trades_executed == 0
    assert metrics.errors == 0


def test_record_generated():
    metrics = Metrics()
    metrics.record_generated()
    metrics.record_generated()
    assert metrics.orders_generated == 2


def test_record_processed():
    metrics = Metrics()
    metrics.record_processed()
    assert metrics.orders_processed == 1


def test_record_trades():
    metrics = Metrics()
    metrics.record_trades(3)
    assert metrics.trades_executed == 3


def test_record_error():
    metrics = Metrics()
    metrics.record_error()
    assert metrics.errors == 1
def test_display(capsys):
    metrics = Metrics()
    metrics.record_generated()
    metrics.display()

    output = capsys.readouterr().out

    assert "Orders generated: 1" in output
    assert "Orders processed: 0" in output
    assert "Trades executed: 0" in output
    assert "Errors: 0" in output