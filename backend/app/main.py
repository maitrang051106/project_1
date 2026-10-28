from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.direct_messages import router as direct_messages_router
from app.api.health import router as health_router
from app.api.matching import router as matching_router
from app.api.profile import router as profile_router
from app.core.config import settings
from app.services.store import RedisUnavailable, store_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await store_service.init_redis()
    yield
    await store_service.close_redis()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.exception_handler(RedisUnavailable)
async def redis_unavailable_handler(request: Request, exc: RedisUnavailable):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Service temporarily unavailable due to shared storage outage. Please retry shortly."},
    )

# CORS configuration supporting credentials (cookies)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers with /api prefix
app.include_router(health_router)
app.include_router(auth_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(matching_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(direct_messages_router, prefix="/api")

# Also support direct paths without /api prefix
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(matching_router)
app.include_router(chat_router)
app.include_router(direct_messages_router)
