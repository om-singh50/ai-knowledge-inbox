import pytest
from pydantic import ValidationError
from datetime import datetime
from app.schemas.api import (
    SourceType,
    IngestRequest,
    IngestResponse,
    ItemResponse,
    QueryRequest,
    QueryResponse,
    SourceSnippet,
)

# INGEST REQUEST TESTS

def test_ingest_request_valid_note():
    # 1. Valid note request.
    req = IngestRequest(source_type="note", content="This is a test note.")
    assert req.source_type == SourceType.NOTE
    assert req.content == "This is a test note."
    assert req.url is None

def test_ingest_request_valid_url():
    # 2. Valid URL request.
    req = IngestRequest(source_type="url", url="https://example.com")
    assert req.source_type == SourceType.URL
    assert str(req.url) == "https://example.com/"
    assert req.content is None

def test_ingest_request_note_empty_content_fails():
    # 3. Note with empty content should fail.
    with pytest.raises(ValidationError):
        IngestRequest(source_type="note", content="")

def test_ingest_request_note_whitespace_content_fails():
    # 4. Note with whitespace-only content should fail.
    with pytest.raises(ValidationError):
        IngestRequest(source_type="note", content="   \n \t  ")

def test_ingest_request_note_with_url_fails():
    # 5. Note with a URL field should fail.
    with pytest.raises(ValidationError):
        IngestRequest(source_type="note", content="Test", url="https://example.com")

def test_ingest_request_url_without_url_fails():
    # 6. URL request without URL should fail.
    with pytest.raises(ValidationError):
        IngestRequest(source_type="url")

def test_ingest_request_url_with_content_fails():
    # 7. URL request containing note content should fail.
    with pytest.raises(ValidationError):
        IngestRequest(source_type="url", url="https://example.com", content="Test content")

def test_ingest_request_unsupported_source_type_fails():
    # 8. Unsupported source_type should fail.
    with pytest.raises(ValidationError):
        IngestRequest(source_type="invalid_type", content="test")

def test_ingest_request_whitespace_normalized():
    # 9. Leading/trailing whitespace should be normalized where the schema currently promises this behavior.
    req = IngestRequest(source_type="note", content="   Content with spaces   ", title="   My Title   ")
    assert req.content == "Content with spaces"
    assert req.title == "My Title"

def test_ingest_request_invalid_url_fails():
    # 10. Invalid/non-HTTP URL should fail.
    with pytest.raises(ValidationError):
        IngestRequest(source_type="url", url="not_a_url")
    with pytest.raises(ValidationError):
        IngestRequest(source_type="url", url="ftp://example.com")

# QUERY REQUEST TESTS

def test_query_request_valid():
    # 11. Valid question should succeed.
    req = QueryRequest(question="What is the meaning of life?")
    assert req.question == "What is the meaning of life?"

def test_query_request_empty_fails():
    # 12. Empty question should fail.
    with pytest.raises(ValidationError):
        QueryRequest(question="")

def test_query_request_whitespace_fails():
    # 13. Whitespace-only question should fail.
    with pytest.raises(ValidationError):
        QueryRequest(question="   \t   ")

def test_query_request_too_long_fails():
    # 14. Question longer than the configured maximum should fail.
    long_question = "a" * 1001
    with pytest.raises(ValidationError):
        QueryRequest(question=long_question)

def test_query_request_whitespace_stripped():
    # 15. Surrounding whitespace should be stripped.
    req = QueryRequest(question="   Why is the sky blue?   ")
    assert req.question == "Why is the sky blue?"

# RESPONSE SCHEMAS TESTS

def test_ingest_response_valid():
    # 16. Valid IngestResponse should validate.
    resp = IngestResponse(
        id="123",
        source_type="note",
        title="My Note",
        created_at=datetime.utcnow(),
        chunk_count=3
    )
    assert resp.id == "123"
    assert resp.source_type == SourceType.NOTE

def test_item_response_valid():
    # 17. Valid ItemResponse should validate.
    resp = ItemResponse(
        id="456",
        source_type="url",
        source="https://example.com",
        created_at=datetime.utcnow()
    )
    assert resp.id == "456"

def test_query_response_multiple_sources_valid():
    # 18. Valid QueryResponse with multiple sources should validate.
    sources = [
        SourceSnippet(
            document_id="1",
            source_type="note",
            content="Snippet 1"
        ),
        SourceSnippet(
            document_id="2",
            source_type="url",
            url="https://example.com",
            content="Snippet 2",
            relevance_score=0.95
        )
    ]
    resp = QueryResponse(answer="Here is the answer.", sources=sources)
    assert resp.answer == "Here is the answer."
    assert len(resp.sources) == 2

def test_source_snippet_supports_note_and_url():
    # 19. SourceSnippet should correctly support note and URL sources.
    note_snippet = SourceSnippet(
        document_id="doc_1",
        source_type="note",
        content="Note content chunk."
    )
    assert note_snippet.source_type == SourceType.NOTE
    assert note_snippet.content == "Note content chunk."
    
    url_snippet = SourceSnippet(
        document_id="doc_2",
        source_type="url",
        url="https://example.com/page",
        content="URL content chunk."
    )
    assert url_snippet.source_type == SourceType.URL
    assert url_snippet.url == "https://example.com/page"
