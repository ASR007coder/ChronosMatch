
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from engine.models import BUY, SELL, Order
from engine.matching_engine import MatchingEngine
from pipeline.runner import run_orders

app = FastAPI(title="ChronosMatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulationRequest(BaseModel):
    total_orders: int = Field(ge=1, le=10000)


@app.get("/")
def home():
    return {"message": "ChronosMatch Backend Running"}


@app.post("/api/v1/simulator/start")
def start_simulation(request: SimulationRequest):

    total_orders = request.total_orders

    engine = MatchingEngine()

    orders = []

    for i in range(1, total_orders + 1):

        side = BUY if i % 2 != 0 else SELL

        order = Order(
            order_id=i,
            sequence=i,
            side=side,
            price=50000,
            quantity=1
        )

        orders.append(order)

    # Calculate performance
    start_time = time.perf_counter()

    metrics, trades = run_orders(orders, engine=engine)

    end_time = time.perf_counter()

    processing_time = end_time - start_time
    processing_time_ms = processing_time * 1000

    average_latency_ms = (
        processing_time_ms / metrics.orders_processed
        if metrics.orders_processed > 0 else 0
    )

    throughput = (
        metrics.orders_processed / processing_time
        if processing_time > 0 else 0
    )

    bids, asks = engine.depth(5)

    return {
        "orders_generated": metrics.orders_generated,
        "orders_received": total_orders,
        "orders_processed": metrics.orders_processed,
        "trades_executed": metrics.trades_executed,
        "errors": metrics.errors,
        "processing_time_ms": round(processing_time_ms, 3),
        "average_latency_ms": round(average_latency_ms, 3),
        "throughput_orders_per_second": round(throughput, 2),
        "trades": [
            trade._asdict() for trade in trades
        ],
        "order_book": {
            "bids": bids,
            "asks": asks
        }
    }
