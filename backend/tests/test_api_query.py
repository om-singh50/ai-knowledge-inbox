import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.rag import RAGResult, RAGChunkSource

client = TestClient(app)

def test_query_success():
    mock_rag_result = RAGResult(
        answer="The capital of France is Paris.",
        retrieved_context=[
            RAGChunkSource(
                document_id="doc_1",
                source_type="note",
                title="Europe Notes",
                source=None,
                content="Paris is the capital of France.",
                relevance_score=0.95
            )
        ]
    )
    with patch("app.api.routers.query.ask_question", return_value=mock_rag_result):
        response = client.post("/query", json={"question": "What is the capital of France?"})
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "The capital of France is Paris."
        assert len(data["sources"]) == 1
        assert data["sources"][0]["document_id"] == "doc_1"
        assert data["sources"][0]["source_type"] == "note"
        assert data["sources"][0]["title"] == "Europe Notes"
        assert data["sources"][0]["url"] is None
        assert data["sources"][0]["content"] == "Paris is the capital of France."
        assert data["sources"][0]["relevance_score"] == 0.95

def test_query_multiple_sources():
    mock_rag_result = RAGResult(
        answer="A summary of multiple sources.",
        retrieved_context=[
            RAGChunkSource(
                document_id="doc_1",
                source_type="note",
                title="Note 1",
                source=None,
                content="Content 1",
                relevance_score=0.9
            ),
            RAGChunkSource(
                document_id="doc_2",
                source_type="url",
                title="URL 2",
                source="https://example.com",
                content="Content 2",
                relevance_score=0.8
            )
        ]
    )
    with patch("app.api.routers.query.ask_question", return_value=mock_rag_result):
        response = client.post("/query", json={"question": "Summarize stuff"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 2
        assert data["sources"][1]["source_type"] == "url"
        assert data["sources"][1]["url"] == "https://example.com"

def test_query_no_sources():
    mock_rag_result = RAGResult(
        answer="I don't know.",
        retrieved_context=[]
    )
    with patch("app.api.routers.query.ask_question", return_value=mock_rag_result):
        response = client.post("/query", json={"question": "Unknown?"})
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "I don't know."
        assert len(data["sources"]) == 0

def test_query_validation_failure():
    # Empty question
    response = client.post("/query", json={"question": ""})
    assert response.status_code == 422
    
    # Missing question
    response = client.post("/query", json={})
    assert response.status_code == 422

def test_query_unexpected_error():
    with patch("app.api.routers.query.ask_question", side_effect=Exception("Database down")):
        response = client.post("/query", json={"question": "Will this crash?"})
        assert response.status_code == 500
        assert "Database down" not in response.json()["detail"]
        assert response.json()["detail"] == "An unexpected error occurred while processing your query."

def test_query_correct_source_mapping_unknown_type():
    mock_rag_result = RAGResult(
        answer="Mapping test.",
        retrieved_context=[
            RAGChunkSource(
                document_id="doc_xyz",
                source_type="weird_type",
                title="Title",
                source="https://weird.com",
                content="Content",
                relevance_score=0.5
            )
        ]
    )
    with patch("app.api.routers.query.ask_question", return_value=mock_rag_result):
        response = client.post("/query", json={"question": "Map this"})
        assert response.status_code == 200
        data = response.json()
        assert data["sources"][0]["source_type"] == "note"
        assert data["sources"][0]["url"] == "https://weird.com"
