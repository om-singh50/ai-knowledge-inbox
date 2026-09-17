import pytest
import sqlite3
import math

from app.db.database import get_db_connection, init_db
from app.db.repository import create_document_with_chunks, ChunkCreate
from app.services.vector_search import cosine_similarity, search, SearchResult

def test_cosine_similarity():
    # Identical vectors
    assert math.isclose(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)
    
    # Orthogonal vectors
    assert math.isclose(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)
    
    # Opposite vectors
    assert math.isclose(cosine_similarity([1.0, 0.0], [-1.0, 0.0]), -1.0)
    
    # Empty vectors
    assert cosine_similarity([], []) == 0.0
    
    # Mismatched lengths
    assert cosine_similarity([1.0], [1.0, 0.0]) == 0.0
    
    # Zero vector
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

@pytest.fixture
def db_conn():
    # Use a temporary file for SQLite since init_db takes a path and closes the connection
    import tempfile
    import os
    fd, path = tempfile.mkstemp()
    os.close(fd)
    
    init_db(path)
    
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
    
    os.remove(path)

def test_search_ranking(db_conn):
    query_vec = [1.0, 0.0]
    
    # Insert chunks with different vectors
    chunks_data = [
        ChunkCreate(content="perfect", embedding=[1.0, 0.0]),
        ChunkCreate(content="opposite", embedding=[-1.0, 0.0]),
        ChunkCreate(content="orthogonal", embedding=[0.0, 1.0]),
        ChunkCreate(content="close", embedding=[0.9, 0.1])
    ]
    
    create_document_with_chunks(db_conn, "note", "raw", chunks_data)
    
    results = search(db_conn, query_vec, top_k=5)
    
    assert len(results) == 4
    assert results[0].content == "perfect"
    assert math.isclose(results[0].relevance_score, 1.0)
    
    assert results[1].content == "close"
    
    assert results[2].content == "orthogonal"
    assert math.isclose(results[2].relevance_score, 0.0)
    
    assert results[3].content == "opposite"
    assert math.isclose(results[3].relevance_score, -1.0)

def test_search_top_k(db_conn):
    query_vec = [1.0, 0.0]
    
    chunks_data = [
        ChunkCreate(content=f"chunk_{i}", embedding=[1.0, i*0.01])
        for i in range(10)
    ]
    
    create_document_with_chunks(db_conn, "note", "raw", chunks_data)
    
    results = search(db_conn, query_vec, top_k=3)
    assert len(results) == 3

def test_search_fewer_than_k(db_conn):
    query_vec = [1.0, 0.0]
    
    chunks_data = [
        ChunkCreate(content="only", embedding=[1.0, 0.0])
    ]
    
    create_document_with_chunks(db_conn, "note", "raw", chunks_data)
    
    results = search(db_conn, query_vec, top_k=5)
    assert len(results) == 1

def test_search_empty_db(db_conn):
    query_vec = [1.0, 0.0]
    results = search(db_conn, query_vec, top_k=5)
    assert len(results) == 0

def test_search_missing_and_malformed_embeddings(db_conn):
    query_vec = [1.0, 0.0]
    
    # Directly insert via SQL since repository enforces all or none for embeddings
    cursor = db_conn.cursor()
    cursor.execute('''INSERT INTO documents (id, source_type, raw_content, created_at) VALUES ('doc1', 'note', 'raw', 'now')''')
    
    # Missing embedding (None)
    cursor.execute('''INSERT INTO chunks (id, document_id, chunk_index, content, embedding, created_at)
                      VALUES ('c1', 'doc1', 0, 'missing', NULL, 'now')''')
    
    # Malformed embedding (not a list)
    cursor.execute('''INSERT INTO chunks (id, document_id, chunk_index, content, embedding, created_at)
                      VALUES ('c2', 'doc1', 1, 'malformed', '"not_a_list"', 'now')''')
    
    # Mismatched dimension (len=3 instead of 2)
    cursor.execute('''INSERT INTO chunks (id, document_id, chunk_index, content, embedding, created_at)
                      VALUES ('c3', 'doc1', 2, 'mismatched', '[1.0, 0.0, 0.0]', 'now')''')
    
    # Valid embedding
    cursor.execute('''INSERT INTO chunks (id, document_id, chunk_index, content, embedding, created_at)
                      VALUES ('c4', 'doc1', 3, 'valid', '[1.0, 0.0]', 'now')''')
    
    db_conn.commit()
    
    results = search(db_conn, query_vec, top_k=5)
    assert len(results) == 1
    assert results[0].content == "valid"

def test_search_deterministic_tie(db_conn):
    query_vec = [1.0, 0.0]
    
    cursor = db_conn.cursor()
    # Create two documents so we can have different document IDs
    cursor.execute('''INSERT INTO documents (id, source_type, raw_content, created_at) VALUES ('docB', 'note', 'raw', 'now')''')
    cursor.execute('''INSERT INTO documents (id, source_type, raw_content, created_at) VALUES ('docA', 'note', 'raw', 'now')''')
    
    # Insert chunks with identical vectors (and thus identical scores)
    # They should sort by score DESC, document_id ASC, chunk_index ASC
    cursor.execute('''INSERT INTO chunks (id, document_id, chunk_index, content, embedding, created_at)
                      VALUES ('c1', 'docB', 1, 'B1', '[1.0, 0.0]', 'now')''')
    cursor.execute('''INSERT INTO chunks (id, document_id, chunk_index, content, embedding, created_at)
                      VALUES ('c2', 'docB', 0, 'B0', '[1.0, 0.0]', 'now')''')
    cursor.execute('''INSERT INTO chunks (id, document_id, chunk_index, content, embedding, created_at)
                      VALUES ('c3', 'docA', 0, 'A0', '[1.0, 0.0]', 'now')''')
    
    db_conn.commit()
    
    results = search(db_conn, query_vec, top_k=5)
    assert len(results) == 3
    assert results[0].document_id == "docA" and results[0].chunk_index == 0
    assert results[1].document_id == "docB" and results[1].chunk_index == 0
    assert results[2].document_id == "docB" and results[2].chunk_index == 1

