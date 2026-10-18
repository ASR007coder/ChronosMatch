# backend/app/router/simulator.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.pipeline.ipc_pipeline import process_orders
from backend.pipeline.fake_simulator import generate_orders


router = APIRouter()


class SimulationRequest(BaseModel):
    total_orders: int = Field(default=10, ge=1, le=10000)




@router.post("/start")
def start_simulation(request: SimulationRequest):
    try:
        orders = generate_orders(request.total_orders)
        result = process_orders(orders)

        return {
            "status": "completed",
            "message": "Orders processed by the matching engine",
            "orders_generated": len(orders),
            **result,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Simulation, IPC, or matching-engine processing failed",
        ) from exc
