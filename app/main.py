# backend/app/main.py

from fastapi import FastAPI
from backend.app.routers import health, simulator, dashboard

app = FastAPI(
    title="ChronosMatch API",
    description="Backend API for ChronosMatch",
    version="1.0.0",
)

app.include_router(
    health.router,
    prefix="/api/v1",
    tags=["Health"],
)

app.include_router(
    simulator.router,
    prefix="/api/v1/simulator",
    tags=["Simulator"],
)

app.include_router(
    dashboard.router,
    prefix="/api/v1/dashboard",
    tags=["Dashboard"],
)


@app.get("/")
def root():
    return {"message": "Welcome to ChronosMatch API"}
