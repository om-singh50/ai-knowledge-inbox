import pytest
import sqlite3
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.schemas.api import IngestRequest, SourceType
from app.services.ingestion import (
    IngestionService,
    IngestionError,
    IngestionEmptyContentError
)
from app.services.scraper import FetchResult, ScraperException

@pytest_asyncio.fixture
async def db_conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row

    # Create tables
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE documents (
        id TEXT PRIMARY KEY,
        source_type TEXT NOT NULL,
        source TEXT,
        title TEXT,
        raw_content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    ''')
    cursor.execute('''
    CREATE TABLE chunks (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(id)
    )
    ''')
    conn.commit()
    yield conn
    conn.close()


@pytest.mark.asyncio
async def test_successful_note_ingestion(db_conn):
    service = IngestionService(db_conn)
    req = IngestRequest(
        source_type=SourceType.NOTE,
        content="This is a simple note content. " * 20,
        title="My Note"
    )

    with patch('app.services.ingestion.embedding_service.embed_batch', return_value=[[0.1] * 384]) as mock_embed:
        resp = await service.ingest(req)

    assert resp.id is not None
    assert resp.source_type == SourceType.NOTE
    assert resp.title == "My Note"
    assert resp.url is None
    assert resp.chunk_count == 1
    
    # check DB
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (resp.id,))
    doc = cursor.fetchone()
    assert doc is not None

@pytest.mark.asyncio
async def test_successful_url_ingestion(db_conn):
    service = IngestionService(db_conn)
    req = IngestRequest(
        source_type=SourceType.URL,
        url="https://example.com"
    )

    fetch_result = FetchResult(
        final_url="https://example.com/final",
        title="Extracted Title",
        text="Extracted web page content. " * 20
    )

    with patch('app.services.ingestion.fetch_url', new_callable=AsyncMock) as mock_fetch, \
         patch('app.services.ingestion.embedding_service.embed_batch', return_value=[[0.1] * 384]) as mock_embed:
        
        mock_fetch.return_value = fetch_result
        resp = await service.ingest(req)
        mock_fetch.assert_called_once()

    assert resp.id is not None
    assert resp.source_type == SourceType.URL
    assert resp.title == "Extracted Title"
    assert resp.url == "https://example.com/final"
    assert resp.chunk_count == 1

@pytest.mark.asyncio
async def test_title_selection_behavior(db_conn):
    service = IngestionService(db_conn)
    req = IngestRequest(
        source_type=SourceType.URL,
        url="https://example.com",
        title="Explicit Title"
    )

    fetch_result = FetchResult(
        final_url="https://example.com",
        title="Extracted Title",
        text="Extracted web page content."
    )

    with patch('app.services.ingestion.fetch_url', new_callable=AsyncMock) as mock_fetch, \
         patch('app.services.ingestion.embedding_service.embed_batch', return_value=[[0.1] * 384]):
        mock_fetch.return_value = fetch_result
        resp = await service.ingest(req)

    # Should use the explicit title
    assert resp.title == "Explicit Title"

@pytest.mark.asyncio
async def test_empty_extracted_content_failure(db_conn):
    service = IngestionService(db_conn)
    req = IngestRequest(
        source_type=SourceType.URL,
        url="https://example.com"
    )

    fetch_result = FetchResult(
        final_url="https://example.com",
        title="Title",
        text=""
    )

    with patch('app.services.ingestion.fetch_url', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = fetch_result
        with pytest.raises(IngestionEmptyContentError):
            await service.ingest(req)

@pytest.mark.asyncio
async def test_chunking_failure(db_conn):
    service = IngestionService(db_conn)
    req = IngestRequest(
        source_type=SourceType.NOTE,
        content="Some content"
    )

    with patch('app.services.ingestion.chunk_text', side_effect=Exception("Chunking error")):
        with pytest.raises(IngestionError, match="Failed to chunk text"):
            await service.ingest(req)
            
    # Check that nothing was saved
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM documents")
    assert cursor.fetchone()[0] == 0

@pytest.mark.asyncio
async def test_embedding_failure(db_conn):
    service = IngestionService(db_conn)
    req = IngestRequest(
        source_type=SourceType.NOTE,
        content="Some content"
    )

    with patch('app.services.ingestion.embedding_service.embed_batch', side_effect=Exception("Embedding error")):
        with pytest.raises(IngestionError, match="Failed to generate embeddings"):
            await service.ingest(req)
            
    # Check that nothing was saved
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM documents")
    assert cursor.fetchone()[0] == 0

@pytest.mark.asyncio
async def test_persistence_failure(db_conn):
    service = IngestionService(db_conn)
    req = IngestRequest(
        source_type=SourceType.NOTE,
        content="Some content"
    )

    with patch('app.services.ingestion.embedding_service.embed_batch', return_value=[[0.1]]), \
         patch('app.services.ingestion.create_document_with_chunks', side_effect=Exception("DB error")):
        with pytest.raises(IngestionError, match="Failed to persist document"):
            await service.ingest(req)
