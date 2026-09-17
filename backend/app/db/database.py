import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import Generator
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a new SQLite connection."""
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # To access columns by name
    return conn

@contextmanager
def get_db_session() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database sessions."""
    conn = get_db_connection()
    try:
        # Enable foreign keys for sqlite
        conn.execute("PRAGMA foreign_keys = 1")
        yield conn
    finally:
        conn.close()

def init_db(db_path: str = None) -> None:
    """Creates the database and tables if they don't exist."""
    path_to_use = db_path or settings.db_path
    try:
        os.makedirs(os.path.dirname(path_to_use), exist_ok=True)
        
        logger.info(f"Initializing database at {path_to_use}")
        
        conn = sqlite3.connect(path_to_use)
        # Enable foreign keys for sqlite
        conn.execute("PRAGMA foreign_keys = 1")
        cursor = conn.cursor()
        
        # Create Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL CHECK(source_type IN ('note', 'url')),
                source TEXT,
                title TEXT,
                raw_content TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
        ''')
        
        # Create Chunks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding TEXT, -- JSON text representation of the vector
                created_at DATETIME NOT NULL,
                FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)')
        
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to initialize database at {path_to_use}: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
