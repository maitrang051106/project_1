import ssl
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def get_db_connect_args(db_url: str) -> dict[str, Any]:
    """Configure connection arguments for database drivers.

    For cloud databases like Aiven MySQL that use self-signed certificates or
    require SSL without standard public CA trust in containers, create an
    SSLContext with verification disabled so TLS encryption is enabled without
    failing on self-signed certificate chains.
    """
    connect_args: dict[str, Any] = {}
    lower_url = db_url.lower()
    if "aivencloud.com" in lower_url or "ssl" in lower_url:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_ctx
    return connect_args


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            connect_args=get_db_connect_args(settings.database_url),
            pool_pre_ping=False,
            pool_recycle=3600,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


class _SessionLocalProxy:
    """Proxy object that delegates to get_session_factory() while preserving lazy initialization."""

    def __call__(self, *args: Any, **kwargs: Any) -> AsyncSession:
        return get_session_factory()(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(get_session_factory(), name)


SessionLocal = _SessionLocalProxy()

__all__ = [
    "get_engine",
    "get_session_factory",
    "get_db",
    "SessionLocal",
    "get_db_connect_args",
]

