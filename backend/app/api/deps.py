from typing import Generator
import sqlite3
from app.db.database import get_db_connection

def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_db_connection()
    try:
        conn.execute("PRAGMA foreign_keys = 1")
        yield conn
    finally:
        conn.close()
