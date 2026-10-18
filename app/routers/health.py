# backend/app/router/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "ChronosMatch API is running",
    }