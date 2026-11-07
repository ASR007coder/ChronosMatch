
# backend/app/routers/dashboard.py

from fastapi import APIRouter

from backend.app.routers.simulation import get_latest_job

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard")
async def dashboard():
    job = get_latest_job()

    if job is None:
        return {
            "job": None,
            "status": "idle",
        }

    return {
        "job": job,
        "status": job["status"],
    }
