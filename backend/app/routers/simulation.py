
# backend/app/routers/simulation.py

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.simulator.ipc_benchmark import run_one

router = APIRouter(tags=["Simulation"])

MIN_ORDERS = 10_000
MAX_ORDERS = 10_000_000

# One active simulation at a time.
_active_job_id = None
_latest_job = None
_job_lock = asyncio.Lock()


class SimulationRequest(BaseModel):
    total_orders: int = Field(
        strict=True,
        ge=MIN_ORDERS,
        le=MAX_ORDERS,
    )


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def build_dashboard_metrics(result: dict) -> dict:
    """
    Extract dashboard-friendly data from the pipeline result.

    Do not return the complete trade list: millions of trade dictionaries
    would create a large HTTP response and unnecessary frontend memory use.
    """

    simulator = result.get("simulator", {})
    producer = result.get("producer", {})
    timings = result.get("timings", {})

    processed = result.get("orders_processed", 0)
    trades = result.get("trades_executed", 0)

    steady_seconds = timings.get("steady_state_seconds", 0.0)
    wall_seconds = timings.get("pipeline_wall_seconds", 0.0)

    return {
        "orders_processed": processed,
        "orders_received": result.get("orders_received", 0),
        "trades_executed": trades,

        "published": producer.get("published", 0),

        "unique_order_ids": result.get("unique_order_ids"),
        "duplicate_order_ids": result.get("duplicate_order_ids"),

        "simulator": simulator,

        "latency": result.get("latency", {}),

        "steady_throughput": (
            processed / steady_seconds if steady_seconds > 0 else 0
        ),

        "wall_throughput": (
            processed / wall_seconds if wall_seconds > 0 else 0
        ),

        "timings": timings,
        "consumer_metrics": result.get("consumer_metrics", {}),

        "order_book": result.get("order_book", {}),
    }


async def execute_simulation(job_id: str, total_orders: int):
    global _active_job_id
    global _latest_job

    try:
        _latest_job["status"] = "running"
        _latest_job["started_at"] = utc_now()

        # Use the same benchmark configuration as the CLI:
        # python -m backend.simulator.ipc_benchmark --count N
        result = await run_one(
            count=total_orders,
            rate=1_000_000,
            seed=42,
        )

        dashboard_metrics = build_dashboard_metrics(result)

        _latest_job.update({
            "status": "completed",
            "completed_at": utc_now(),
            "metrics": dashboard_metrics,
        })

    except Exception as exc:
        _latest_job.update({
            "status": "failed",
            "completed_at": utc_now(),
            "error": f"{type(exc).__name__}: {exc}",
        })

    finally:
        _active_job_id = None


@router.post("/simulation/start")
async def start_simulation(request: SimulationRequest):
    global _active_job_id
    global _latest_job

    async with _job_lock:
        if _active_job_id is not None:
            raise HTTPException(
                status_code=409,
                detail="A simulation is already running.",
            )

        job_id = str(uuid.uuid4())

        _active_job_id = job_id

        _latest_job = {
            "job_id": job_id,
            "status": "queued",
            "total_orders": request.total_orders,
            "created_at": utc_now(),
            "started_at": None,
            "completed_at": None,
            "metrics": None,
            "error": None,
        }

        asyncio.create_task(
            execute_simulation(
                job_id=job_id,
                total_orders=request.total_orders,
            )
        )

    return {
        "message": "Simulation started",
        "job_id": job_id,
        "status": "queued",
        "total_orders": request.total_orders,
    }


def get_latest_job():
    return _latest_job
