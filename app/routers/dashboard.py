# backend/app/routers/dashboard.py



from fastapi import APIRouter

router = APIRouter()

# Stores metrics from the latest completed simulation.
# These values reset when the backend restarts.
_latest_metrics = {
    "status": "no_simulation",
    "orders_generated": 0,
    "orders_sent": 0,
    "orders_received": 0,
    "orders_processed": 0,
    "trades_executed": 0,
    "elapsed_seconds": 0.0,
    "throughput_orders_per_second": 0.0,
    "ipc_errors": 0,
    "ipc_timeouts": 0,
}


def update_dashboard_metrics(metrics: dict) -> None:
    """Update dashboard data after a simulation completes."""
    _latest_metrics.update(metrics)


@router.get("/summary")
def get_dashboard_summary():
    """Return the latest simulation summary."""
    return {
        "status": _latest_metrics["status"],
        "orders_generated": _latest_metrics["orders_generated"],
        "orders_sent": _latest_metrics["orders_sent"],
        "orders_received": _latest_metrics["orders_received"],
        "orders_processed": _latest_metrics["orders_processed"],
        "trades_executed": _latest_metrics["trades_executed"],
    }


@router.get("/metrics")
def get_dashboard_metrics():
    """Return performance and IPC metrics."""
    return _latest_metrics.copy()
