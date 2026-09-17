import os
import tempfile
import sqlite3
import pytest
from app.db.database import init_db
from app.db.repository import (
    create_document,
    get_document_by_id,
    get_all_documents,
    create_chunks,
    get_chunks_by_document_id,
    ChunkCreate
)

@pytest.fixture
def db_conn():
    # Use a temporary file for the database during tests
    fd, temp_path = tempfile.mkstemp()
    os.close(fd)
    
    # Initialize DB at temp path
    init_db(temp_path)
    
    # Provide connection
    conn = sqlite3.connect(temp_path)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys for sqlite
    conn.execute("PRAGMA foreign_keys = 1")
    
    yield conn
    
    conn.close()
    os.remove(temp_path)

def test_create_and_get_document(db_conn):
    doc = create_document(
        db_conn,
        source_type="note",
        raw_content="This is a test note.",
        title="Test Note"
    )
    
    assert doc is not None
    assert doc["id"] is not None
    assert doc["source_type"] == "note"
    assert doc["raw_content"] == "This is a test note."
    assert doc["title"] == "Test Note"
    assert doc["source"] is None
    
    fetched_doc = get_document_by_id(db_conn, doc["id"])
    assert fetched_doc is not None
    assert fetched_doc["id"] == doc["id"]

def test_get_all_documents(db_conn):
    create_document(db_conn, source_type="note", raw_content="Note 1")
    create_document(db_conn, source_type="url", raw_content="Content from URL", source="http://example.com")
    
    docs = get_all_documents(db_conn)
    assert len(docs) == 2
    assert docs[0]["raw_content"] in ["Note 1", "Content from URL"]

def test_create_and_get_chunks(db_conn):
    doc = create_document(db_conn, source_type="note", raw_content="A long note to be chunked.")
    
    chunks_data = [
        ChunkCreate(content="A long note", embedding=[0.1, 0.2, 0.3]),
        ChunkCreate(content="to be chunked.", embedding=[0.4, 0.5, 0.6])
    ]
    
    chunks = create_chunks(db_conn, doc["id"], chunks_data)
    
    assert len(chunks) == 2
    assert chunks[0]["document_id"] == doc["id"]
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["content"] == "A long note"
    assert chunks[0]["embedding"] == [0.1, 0.2, 0.3]
    
    assert chunks[1]["document_id"] == doc["id"]
    assert chunks[1]["chunk_index"] == 1
    
    fetched_chunks = get_chunks_by_document_id(db_conn, doc["id"])
    assert len(fetched_chunks) == 2

def test_cascade_delete(db_conn):
    doc = create_document(db_conn, source_type="note", raw_content="Cascade delete test")
    chunks_data = [ChunkCreate(content="Chunk 1"), ChunkCreate(content="Chunk 2")]
    create_chunks(db_conn, doc["id"], chunks_data)
    
    assert len(get_chunks_by_document_id(db_conn, doc["id"])) == 2
    
    # Delete doc
    db_conn.execute("DELETE FROM documents WHERE id = ?", (doc["id"],))
    db_conn.commit()
    
    # Verify chunks are deleted
    assert len(get_chunks_by_document_id(db_conn, doc["id"])) == 0

def test_chunk_ordering(db_conn):
    doc = create_document(db_conn, source_type="note", raw_content="Order test")
    chunks_data = [ChunkCreate(content="C1"), ChunkCreate(content="C2"), ChunkCreate(content="C3")]
    create_chunks(db_conn, doc["id"], chunks_data)
    
    chunks = get_chunks_by_document_id(db_conn, doc["id"])
    assert len(chunks) == 3
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["content"] == "C1"
    assert chunks[1]["chunk_index"] == 1
    assert chunks[1]["content"] == "C2"
    assert chunks[2]["chunk_index"] == 2
    assert chunks[2]["content"] == "C3"

def test_json_embedding_roundtrip(db_conn):
    doc = create_document(db_conn, source_type="note", raw_content="Embedding JSON test")
    chunks_data = [ChunkCreate(content="JSON Test", embedding=[0.5, 0.6, -0.7])]
    create_chunks(db_conn, doc["id"], chunks_data)
    
    chunks = get_chunks_by_document_id(db_conn, doc["id"])
    assert len(chunks) == 1
    # Check that it's properly deserialized to a list, not string
    assert type(chunks[0]["embedding"]) is list
    assert chunks[0]["embedding"] == [0.5, 0.6, -0.7]

def test_mismatched_chunk_embedding_lengths(db_conn):
    doc = create_document(db_conn, source_type="note", raw_content="Mismatch test")
    # One has embedding, one doesn't
    chunks_data = [
        ChunkCreate(content="With embedding", embedding=[0.1, 0.2]),
        ChunkCreate(content="Without embedding", embedding=None)
    ]
    
    with pytest.raises(ValueError, match="Mismatched chunk and embedding lengths"):
        create_chunks(db_conn, doc["id"], chunks_data)
        
def test_embedding_persistence_failure_cleanly(db_conn):
    doc = create_document(db_conn, source_type="note", raw_content="Failure test")
    chunks_data = [ChunkCreate(content="Valid", embedding=[0.1, 0.2])]
    
    # Simulate DB error by dropping table temporarily
    db_conn.execute("DROP TABLE chunks")
    db_conn.commit()
    
    with pytest.raises(RuntimeError, match="Database error during chunk persistence"):
        create_chunks(db_conn, doc["id"], chunks_data)


