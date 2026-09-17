import sqlite3
import uuid
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def create_document(conn: sqlite3.Connection, source_type: str, raw_content: str, source: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
    """Creates a new document."""
    doc_id = str(uuid.uuid4())
    created_at = _now_utc()
    
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO documents (id, source_type, source, title, raw_content, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (doc_id, source_type, source, title, raw_content, created_at)
    )
    conn.commit()
    return get_document_by_id(conn, doc_id)

def get_document_by_id(conn: sqlite3.Connection, doc_id: str) -> Optional[Dict[str, Any]]:
    """Gets a document by its ID."""
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM documents WHERE id = ?', (doc_id,))
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None

def get_all_documents(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Gets all documents."""
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM documents ORDER BY created_at DESC')
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@dataclass
class ChunkCreate:
    content: str
    embedding: Optional[List[float]] = None

def create_chunks(conn: sqlite3.Connection, document_id: str, chunks_data: List[ChunkCreate]) -> List[Dict[str, Any]]:
    """
    Creates multiple chunks for a document.
    chunks_data should be a list of ChunkCreate.
    """
    # Enforce one embedding corresponds to exactly one chunk
    has_embeddings = [c.embedding is not None for c in chunks_data]
    if any(has_embeddings) and not all(has_embeddings):
        raise ValueError("Mismatched chunk and embedding lengths: either all chunks must have embeddings, or none.")

    created_at = _now_utc()
    chunk_records = []
    
    for index, chunk in enumerate(chunks_data):
        chunk_id = str(uuid.uuid4())
        embedding_json = json.dumps(chunk.embedding) if chunk.embedding is not None else None
        
        chunk_records.append((
            chunk_id,
            document_id,
            index,
            chunk.content,
            embedding_json,
            created_at
        ))
    
    cursor = conn.cursor()
    try:
        cursor.executemany(
            '''
            INSERT INTO chunks (id, document_id, chunk_index, content, embedding, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            chunk_records
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Database error during chunk persistence: {e}") from e
    
    return get_chunks_by_document_id(conn, document_id)

def get_chunks_by_document_id(conn: sqlite3.Connection, document_id: str) -> List[Dict[str, Any]]:
    """Gets all chunks for a document."""
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index ASC', (document_id,))
    rows = cursor.fetchall()
    
    result = []
    for row in rows:
        chunk_dict = dict(row)
        # Parse embedding back to list if it exists
        if chunk_dict['embedding']:
            try:
                chunk_dict['embedding'] = json.loads(chunk_dict['embedding'])
            except json.JSONDecodeError:
                pass
        result.append(chunk_dict)
    return result

def get_all_chunks(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Gets all chunks from the database."""
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM chunks')
    rows = cursor.fetchall()
    
    result = []
    for row in rows:
        chunk_dict = dict(row)
        # Parse embedding back to list if it exists
        if chunk_dict['embedding']:
            try:
                chunk_dict['embedding'] = json.loads(chunk_dict['embedding'])
            except json.JSONDecodeError:
                pass
        result.append(chunk_dict)
    return result

def create_document_with_chunks(
    conn: sqlite3.Connection,
    source_type: str,
    raw_content: str,
    chunks_data: List[ChunkCreate],
    source: Optional[str] = None,
    title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Atomically creates a new document and its associated chunks.
    Rolls back the transaction if any part fails.
    """
    doc_id = str(uuid.uuid4())
    created_at = _now_utc()
    
    # Enforce one embedding corresponds to exactly one chunk
    if chunks_data:
        has_embeddings = [c.embedding is not None for c in chunks_data]
        if any(has_embeddings) and not all(has_embeddings):
            raise ValueError("Mismatched chunk and embedding lengths: either all chunks must have embeddings, or none.")

    chunk_records = []
    for index, chunk in enumerate(chunks_data):
        chunk_id = str(uuid.uuid4())
        embedding_json = json.dumps(chunk.embedding) if chunk.embedding is not None else None
        
        chunk_records.append((
            chunk_id,
            doc_id,
            index,
            chunk.content,
            embedding_json,
            created_at
        ))

    cursor = conn.cursor()
    try:
        # Insert document
        cursor.execute(
            '''
            INSERT INTO documents (id, source_type, source, title, raw_content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (doc_id, source_type, source, title, raw_content, created_at)
        )
        
        # Insert chunks
        if chunk_records:
            cursor.executemany(
                '''
                INSERT INTO chunks (id, document_id, chunk_index, content, embedding, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                chunk_records
            )
        
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Database error during atomic persistence: {e}") from e

    doc = get_document_by_id(conn, doc_id)
    if doc is None:
        raise RuntimeError("Failed to retrieve document after atomic insert.")
    
    doc['chunks'] = get_chunks_by_document_id(conn, doc_id)
    return doc
