import pytest
from unittest.mock import MagicMock, patch
import sqlite3

from app.services.rag import ask_question, RAGResult
from app.services.vector_search import SearchResult

@pytest.fixture
def mock_conn():
    return MagicMock(spec=sqlite3.Connection)

def test_ask_question_empty(mock_conn):
    result = ask_question(mock_conn, "")
    assert result.answer == "Please provide a valid question."
    assert result.retrieved_context == []

@patch("app.services.rag.get_document_by_id")
@patch("app.services.rag.embedding_service")
@patch("app.services.rag.search")
@patch("app.services.rag.generation_service")
def test_ask_question_success(mock_generation, mock_search, mock_embedding, mock_get_doc, mock_conn):
    mock_embedding.embed_query.return_value = [0.1, 0.2, 0.3]
    
    mock_search.return_value = [
        SearchResult(
            chunk_id="c1",
            document_id="d1",
            chunk_index=0,
            content="Context 1",
            relevance_score=0.9
        )
    ]
    
    mock_get_doc.return_value = {
        "id": "d1",
        "source_type": "note",
        "title": "Test Note",
        "source": None
    }
    
    mock_generation.generate_answer.return_value = "This is the answer."
    
    result = ask_question(mock_conn, "What is this?")
    
    assert result.answer == "This is the answer."
    assert len(result.retrieved_context) == 1
    assert result.retrieved_context[0].content == "Context 1"
    assert result.retrieved_context[0].source_type == "note"
    assert result.retrieved_context[0].title == "Test Note"
    
    mock_embedding.embed_query.assert_called_once_with("What is this?")
    mock_search.assert_called_once_with(mock_conn, [0.1, 0.2, 0.3], top_k=5)
    mock_generation.generate_answer.assert_called_once()

@patch("app.services.rag.embedding_service")
@patch("app.services.rag.search")
@patch("app.services.rag.generation_service")
def test_ask_question_no_context(mock_generation, mock_search, mock_embedding, mock_conn):
    mock_embedding.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_search.return_value = []
    
    result = ask_question(mock_conn, "What is this?")
    
    assert "not contain enough information" in result.answer
    assert result.retrieved_context == []
    
    mock_embedding.embed_query.assert_called_once()
    mock_search.assert_called_once()
    mock_generation.generate_answer.assert_not_called()

@patch("app.services.rag.embedding_service")
def test_ask_question_embedding_error(mock_embedding, mock_conn):
    mock_embedding.embed_query.side_effect = Exception("API Error")
    
    result = ask_question(mock_conn, "What is this?")
    
    assert "error while processing" in result.answer
    assert result.retrieved_context == []

@patch("app.services.rag.get_document_by_id")
@patch("app.services.rag.embedding_service")
@patch("app.services.rag.search")
@patch("app.services.rag.generation_service")
def test_ask_question_generation_error(mock_generation, mock_search, mock_embedding, mock_get_doc, mock_conn):
    mock_embedding.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_search.return_value = [
        SearchResult(
            chunk_id="c1",
            document_id="d1",
            chunk_index=0,
            content="Context 1",
            relevance_score=0.9
        )
    ]
    mock_get_doc.return_value = {
        "id": "d1",
        "source_type": "note",
        "title": "Test Note",
        "source": None
    }
    mock_generation.generate_answer.side_effect = Exception("Generation Error")
    
    result = ask_question(mock_conn, "What is this?")
    
    assert "error while generating" in result.answer
    assert len(result.retrieved_context) == 1

@patch("app.services.rag.get_document_by_id")
@patch("app.services.rag.embedding_service")
@patch("app.services.rag.search")
@patch("app.services.rag.generation_service")
def test_ask_question_document_metadata_variations(mock_generation, mock_search, mock_embedding, mock_get_doc, mock_conn):
    mock_embedding.embed_query.return_value = [0.1]
    
    mock_search.return_value = [
        SearchResult(chunk_id="c1", document_id="d_url", chunk_index=0, content="Content 1", relevance_score=0.95),
        SearchResult(chunk_id="c2", document_id="d_note", chunk_index=0, content="Content 2", relevance_score=0.85),
        SearchResult(chunk_id="c3", document_id="d_missing", chunk_index=0, content="Content 3", relevance_score=0.75)
    ]
    
    def side_effect_get_document(conn, doc_id):
        if doc_id == "d_url":
            return {"id": "d_url", "source_type": "url", "title": "A Web Page", "source": "https://example.com"}
        elif doc_id == "d_note":
            return {"id": "d_note", "source_type": "note", "title": "A Note", "source": None}
        return None
        
    mock_get_doc.side_effect = side_effect_get_document
    mock_generation.generate_answer.return_value = "Answer"
    
    result = ask_question(mock_conn, "query")
    
    # 1. Retrieved chunk gets correct document metadata
    assert len(result.retrieved_context) == 3
    
    # 2. URL source includes its URL
    c_url = result.retrieved_context[0]
    assert c_url.document_id == "d_url"
    assert c_url.source_type == "url"
    assert c_url.title == "A Web Page"
    assert c_url.source == "https://example.com"
    # 4. Relevance score is preserved
    assert c_url.relevance_score == 0.95
    assert c_url.content == "Content 1"
    
    # 3. Note source has no URL
    c_note = result.retrieved_context[1]
    assert c_note.document_id == "d_note"
    assert c_note.source_type == "note"
    assert c_note.title == "A Note"
    assert c_note.source is None
    assert c_note.relevance_score == 0.85
    
    # 5. Missing document is handled safely
    c_missing = result.retrieved_context[2]
    assert c_missing.document_id == "d_missing"
    assert c_missing.source_type == "unknown"
    assert c_missing.title is None
    assert c_missing.source is None
    assert c_missing.relevance_score == 0.75

