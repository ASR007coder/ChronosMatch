from fastapi import APIRouter

from backend.app.routers.simulation import get_latest_job

router = APIRouter(tags=["Dashboard"])

_dashboard_metrics = {
    "status": "idle",
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


def update_dashboard_metrics(metrics: dict):
    _dashboard_metrics.update(metrics)


@router.get("/dashboard/summary")
async def dashboard_summary():
    job = get_latest_job()

    if job and job.get("metrics"):
        metrics = job["metrics"]
        return {
            "status": job["status"],
            "orders_generated": metrics.get("orders_generated", metrics.get("published", 0)),
            "orders_sent": metrics.get("orders_sent", metrics.get("published", 0)),
            "orders_received": metrics.get("orders_received", 0),
            "orders_processed": metrics.get("orders_processed", 0),
            "trades_executed": metrics.get("trades_executed", 0),
        }

    return {
        key: _dashboard_metrics[key]
        for key in (
            "status",
            "orders_generated",
            "orders_sent",
            "orders_received",
            "orders_processed",
            "trades_executed",
        )
    }


@router.get("/dashboard/metrics")
async def dashboard_metrics():
    return _dashboard_metrics


@router.get("/dashboard")
async def dashboard():
    job = get_latest_job()

    if job is None:
        return {"job": None, "status": "idle"}

    return {"job": job, "status": job["status"]}