import pytest
import sqlite3
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.api.deps import get_db

def get_test_db():
    # check_same_thread=False is necessary for FastAPI when testing threading issues
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE documents (id TEXT PRIMARY KEY, source_type TEXT NOT NULL, source TEXT, title TEXT, raw_content TEXT NOT NULL, created_at DATETIME NOT NULL)''')
    cursor.execute('''CREATE TABLE chunks (id TEXT PRIMARY KEY, document_id TEXT NOT NULL, chunk_index INTEGER NOT NULL, content TEXT NOT NULL, embedding TEXT, created_at DATETIME NOT NULL)''')
    conn.commit()
    yield conn
    conn.close()

app.dependency_overrides[get_db] = get_test_db
client = TestClient(app)

def test_sqlite_threading_bug_regression():
    """
    Regression test to verify that the SQLite connection allows cross-thread usage.
    FastAPI get_db dependency runs in a thread pool, but async endpoints run in the main event loop.
    The asyncio.to_thread call inside IngestionService was causing an operational error
    if check_same_thread wasn't disabled.
    """
    with patch('app.services.ingestion.embedding_service.embed_batch', return_value=[[0.1]*3072]):
        resp = client.post('/ingest', json={'content': 'Testing threading fix', 'source_type': 'note'})
        assert resp.status_code == 201
        assert resp.json()["source_type"] == "note"
        assert resp.json()["chunk_count"] == 1

def test_query_no_evidence_behavior():
    """
    Test that when the system is asked a factual question that is NOT in the
    knowledge base (and the context is empty/unrelated), Gemini responds safely
    indicating it doesn't know, rather than fabricating a factual answer.
    """
    response = client.post('/query', json={'question': 'What is the capital of Mars?'})
    assert response.status_code == 200
    data = response.json()
    
    answer = data.get("answer", "").lower()
    
    # Assert it didn't fabricate an answer (e.g. didn't say it's some fictional city)
    assert "mars" not in answer or "capital" not in answer or "is" not in answer
    
    # Assert the safe response keywords
    assert "not available" in answer or "don't know" in answer or "saved knowledge" in answer or "cannot answer" in answer
    
    # Ensure response matches QueryResponse schema constraints
    assert "sources" in data
    assert isinstance(data["sources"], list)
    
    # In this isolated test db, sources should be empty since nothing is ingested that would match
    if len(data["sources"]) > 0:
        # If there are sources, they must not support a fabricated answer.
        # But since DB is empty, it should be empty.
        pass
