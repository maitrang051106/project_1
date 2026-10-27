from unittest.mock import MagicMock
from app.core.db import SessionLocal, _SessionLocalProxy
import app.main


def test_import_app_main_and_routes():
    """Verify that app.main and all attached routers load without error."""
    assert app.main.app is not None
    assert app.main.app.title == "HUST Chatbox API"
    paths = app.main.app.openapi()["paths"]
    assert "/health" in paths
    assert "/api/auth/register" in paths
    assert "/api/profile" in paths
    assert "/api/match/join" in paths


def test_session_local_proxy_is_callable(monkeypatch):
    """Verify that SessionLocal is a proxy object providing access to sessionmaker."""
    assert isinstance(SessionLocal, _SessionLocalProxy)
    assert callable(SessionLocal)

    mock_session = MagicMock()
    mock_factory = MagicMock(return_value=mock_session)
    monkeypatch.setattr("app.core.db.get_session_factory", lambda: mock_factory)

    session = SessionLocal()
    assert session is mock_session
    mock_factory.assert_called_once()

