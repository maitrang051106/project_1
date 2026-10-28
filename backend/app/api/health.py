import asyncio
from typing import Any

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.db import SessionLocal
from app.services.store import store_service

router = APIRouter(tags=["health"])


async def probe_database() -> bool:
    try:
      async with SessionLocal() as db:
        res = await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=2.0)
        return bool(res)
    except Exception:
      return False


async def probe_redis() -> bool:
    try:
      return await store_service.is_redis_healthy()
    except Exception:
      return False


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Lightweight process liveness probe."""
    return {"status": "live"}


@router.get("/health")
async def health_check() -> Response:
    """Readiness probe checking database and Redis dependencies.
    Returns sanitized status without leaking sensitive error messages or credentials.
    """
    db_ok, redis_ok = await asyncio.gather(probe_database(), probe_redis())

    is_production = settings.environment.lower() == "production"
    # In production, both DB and Redis are required
    # In development, DB is required; Redis can fallback to memory
    is_ready = db_ok and (redis_ok or not is_production)

    data = {
        "status": "ok" if is_ready else "unavailable",
        "database": "ok" if db_ok else "unavailable",
        "redis": "ok" if redis_ok else "unavailable",
    }

    status_code = (
        status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(status_code=status_code, content=data)
