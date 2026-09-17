import os
import sqlite3
import tempfile
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.db.database import init_db
from app.api.deps import get_db
from app.db import repository

client = TestClient(app)

@pytest.fixture
def override_get_db_session() -> Generator[sqlite3.Connection, None, None]:
    fd, temp_path = tempfile.mkstemp()
    os.close(fd)
    
    init_db(temp_path)
    
    conn = sqlite3.connect(temp_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = 1")
    
    def override():
        try:
            yield conn
        finally:
            pass

    app.dependency_overrides[get_db] = override
    
    yield conn
    
    app.dependency_overrides.clear()
    conn.close()
    os.remove(temp_path)

def test_get_items_empty(override_get_db_session):
    response = client.get("/items")
    assert response.status_code == 200
    assert response.json() == []

def test_get_items_one_note(override_get_db_session):
    repository.create_document(
        override_get_db_session,
        source_type="note",
        raw_content="Note content",
        title="Note Title"
    )
    
    response = client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source_type"] == "note"
    assert data[0]["title"] == "Note Title"
    assert data[0]["source"] is None
    assert "raw_content" not in data[0]
    assert "chunks" not in data[0]
    assert "embeddings" not in data[0]

def test_get_items_one_url(override_get_db_session):
    repository.create_document(
        override_get_db_session,
        source_type="url",
        raw_content="URL content",
        title="URL Title",
        source="https://example.com"
    )
    
    response = client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source_type"] == "url"
    assert data[0]["title"] == "URL Title"
    assert data[0]["source"] == "https://example.com"
    assert "raw_content" not in data[0]

def test_get_items_multiple_newest_first(override_get_db_session):
    repository.create_document(
        override_get_db_session,
        source_type="note",
        raw_content="First",
        title="First Note"
    )
    
    repository.create_document(
        override_get_db_session,
        source_type="note",
        raw_content="Second",
        title="Second Note"
    )
    
    response = client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Second Note"
    assert data[1]["title"] == "First Note"

def test_get_items_db_failure(override_get_db_session):
    # To test db failure without needing a full db setup, we can patch repository
    with patch("app.api.routers.items.repository.get_all_documents") as mock_get_all:
        mock_get_all.side_effect = Exception("DB error")
        response = client.get("/items")
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}
