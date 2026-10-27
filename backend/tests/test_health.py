from app.api.health import router


def test_health_returns_ok() -> None:
    assert any(route.path == "/health" for route in router.routes)
