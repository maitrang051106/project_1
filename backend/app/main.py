from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.direct_messages import router as direct_messages_router
from app.api.health import router as health_router
from app.api.matching import router as matching_router
from app.api.profile import router as profile_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)

# CORS configuration supporting credentials (cookies)
cors_origins = [
    settings.frontend_origin,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
for v_domain in [
    "https://project-1-hust-chatbox.vercel.app",
    "https://project-1-qtlhgs1xa-maitrang051106s-projects.vercel.app",
]:
    if v_domain not in cors_origins:
        cors_origins.append(v_domain)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
