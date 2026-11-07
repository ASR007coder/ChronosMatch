
# backend/app/run.py

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.routers import health
from backend.app.routers import simulation
from backend.app.routers import dashboard


app = FastAPI(
    title="ChronosMatch",
    description="Low-latency market matching engine",
    version="1.0.0",
)

# API routes.
app.include_router(
    health.router,
    prefix="/api/v1",
)

app.include_router(
    simulation.router,
    prefix="/api/v1",
)

app.include_router(
    dashboard.router,
    prefix="/api/v1",
)

# Serve the frontend from the same server.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"

if FRONTEND_DIR.exists():
    app.mount(
        "/",
        StaticFiles(
            directory=str(FRONTEND_DIR),
            html=True,
        ),
        name="frontend",
    )
else:
    raise RuntimeError(
        f"Frontend directory not found: {FRONTEND_DIR}"
    )
