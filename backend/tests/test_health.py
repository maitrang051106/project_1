from app.api.health import router


def test_health_routes_exist() -> None:
    routes = [route.path for route in router.routes]
    assert "/health" in routes
    assert "/live" in routes
