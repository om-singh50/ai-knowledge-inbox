import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.main import app
from app.schemas.api import SourceType, IngestResponse
from app.services.ingestion import IngestionError, IngestionEmptyContentError

client = TestClient(app)

@pytest.fixture
def mock_ingestion_service():
    with patch("app.api.routers.ingest.IngestionService") as mock_service_class:
        mock_instance = MagicMock()
        mock_instance.ingest = AsyncMock()
        mock_service_class.return_value = mock_instance
        yield mock_instance

def test_ingest_note_success(mock_ingestion_service):
    mock_ingestion_service.ingest.return_value = IngestResponse(
        id="doc_1",
        source_type=SourceType.NOTE,
        title="Test Note",
        url=None,
        created_at=datetime.now(timezone.utc),
        chunk_count=2
    )

    response = client.post("/ingest", json={
        "source_type": "note",
        "content": "This is a test note.",
        "title": "Test Note"
    })

    assert response.status_code == 201
    assert response.json()["id"] == "doc_1"
    assert response.json()["source_type"] == "note"
    mock_ingestion_service.ingest.assert_called_once()

def test_ingest_url_success(mock_ingestion_service):
    mock_ingestion_service.ingest.return_value = IngestResponse(
        id="doc_2",
        source_type=SourceType.URL,
        title="Test URL",
        url="https://example.com",
        created_at=datetime.now(timezone.utc),
        chunk_count=5
    )

    response = client.post("/ingest", json={
        "source_type": "url",
        "url": "https://example.com",
        "title": "Test URL"
    })

    assert response.status_code == 201
    assert response.json()["id"] == "doc_2"
    assert response.json()["source_type"] == "url"
    mock_ingestion_service.ingest.assert_called_once()

def test_ingest_validation_failure_invalid_source_type():
    response = client.post("/ingest", json={
        "source_type": "invalid_type",
        "content": "Some text"
    })
    assert response.status_code == 422

def test_ingest_validation_failure_empty_note():
    response = client.post("/ingest", json={
        "source_type": "note",
        "content": ""
    })
    assert response.status_code == 422

def test_ingest_validation_failure_missing_url():
    response = client.post("/ingest", json={
        "source_type": "url"
    })
    assert response.status_code == 422

def test_ingest_empty_content_error(mock_ingestion_service):
    mock_ingestion_service.ingest.side_effect = IngestionEmptyContentError("Content is empty")
    response = client.post("/ingest", json={
        "source_type": "note",
        "content": "some text"
    })
    assert response.status_code == 400
    assert "Content is empty" in response.json()["detail"]

def test_ingest_url_fetch_failure(mock_ingestion_service):
    mock_ingestion_service.ingest.side_effect = IngestionError("Failed to fetch URL: timeout")
    response = client.post("/ingest", json={
        "source_type": "url",
        "url": "https://example.com"
    })
    assert response.status_code == 400
    assert "Failed to fetch URL content" in response.json()["detail"]

def test_ingest_embedding_service_failure(mock_ingestion_service):
    mock_ingestion_service.ingest.side_effect = IngestionError("Failed to generate embeddings: service down")
    response = client.post("/ingest", json={
        "source_type": "note",
        "content": "some text"
    })
    assert response.status_code == 503
    assert "Embedding service unavailable" in response.json()["detail"]

def test_ingest_unexpected_internal_failure(mock_ingestion_service):
    mock_ingestion_service.ingest.side_effect = Exception("Some weird error")
    response = client.post("/ingest", json={
        "source_type": "note",
        "content": "some text"
    })
    assert response.status_code == 500
    assert "unexpected error" in response.json()["detail"].lower()

def test_ingest_generic_ingestion_error(mock_ingestion_service):
    mock_ingestion_service.ingest.side_effect = IngestionError("Failed to persist document")
    response = client.post("/ingest", json={
        "source_type": "note",
        "content": "some text"
    })
    assert response.status_code == 500
    assert "Internal server error during ingestion" in response.json()["detail"]
