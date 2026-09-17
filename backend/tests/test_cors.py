from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cors_headers():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type"
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "GET" in response.headers.get("access-control-allow-methods", "")
    assert "Content-Type" in response.headers.get("access-control-allow-headers", "")

def test_cors_not_allowed_origin():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    # The CORS middleware will return 400 for a disallowed origin in preflight,
    # or just omit the CORS headers for a simple request.
    # We just ensure the origin is not returned.
    assert response.headers.get("access-control-allow-origin") != "http://evil.com"
