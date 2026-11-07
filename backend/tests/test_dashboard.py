
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routers import dashboard


client = TestClient(app)


def test_dashboard_summary_returns_expected_fields():
    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "orders_generated" in data
    assert "orders_sent" in data
    assert "orders_received" in data
    assert "orders_processed" in data
    assert "trades_executed" in data


def test_dashboard_metrics_returns_expected_fields():
    response = client.get("/api/v1/dashboard/metrics")

    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "orders_generated" in data
    assert "orders_sent" in data
    assert "orders_received" in data
    assert "orders_processed" in data
    assert "trades_executed" in data
    assert "elapsed_seconds" in data
    assert "throughput_orders_per_second" in data
    assert "ipc_errors" in data
    assert "ipc_timeouts" in data


def test_dashboard_metrics_can_be_updated():
    test_metrics = {
        "status": "completed",
        "orders_generated": 100,
        "orders_sent": 100,
        "orders_received": 100,
        "orders_processed": 100,
        "trades_executed": 40,
        "elapsed_seconds": 2.0,
        "throughput_orders_per_second": 50.0,
        "ipc_errors": 0,
        "ipc_timeouts": 0,
    }

    dashboard.update_dashboard_metrics(test_metrics)

    response = client.get("/api/v1/dashboard/metrics")

    assert response.status_code == 200
    assert response.json() == test_metrics

    summary_response = client.get("/api/v1/dashboard/summary")
    summary = summary_response.json()

    assert summary["status"] == "completed"
    assert summary["orders_generated"] == 100
    assert summary["orders_processed"] == 100
    assert summary["trades_executed"] == 40
