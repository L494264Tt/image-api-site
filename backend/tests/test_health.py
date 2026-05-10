import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.observability import REQUEST_ID_HEADER


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_header_is_generated() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert uuid.UUID(response.headers[REQUEST_ID_HEADER])


def test_request_id_header_is_preserved() -> None:
    client = TestClient(app)

    response = client.get("/api/health", headers={REQUEST_ID_HEADER: "request-id-123"})

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "request-id-123"


def test_request_log_includes_metadata_without_query_string(caplog) -> None:
    client = TestClient(app)

    with caplog.at_level("INFO", logger="app.requests"):
        response = client.get("/api/health?token=secret-value", headers={REQUEST_ID_HEADER: "request-id-123"})

    assert response.status_code == 200
    record = next(item for item in caplog.records if item.name == "app.requests")
    assert record.message == "request_complete"
    assert record.method == "GET"
    assert record.path == "/api/health"
    assert record.status_code == 200
    assert record.duration_ms >= 0
    assert record.request_id == "request-id-123"
    assert "secret-value" not in record.getMessage()
