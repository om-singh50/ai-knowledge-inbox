import logging
import sqlite3
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_db
from app.db import repository
from app.schemas.api import ItemResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/items")

@router.get(
    "",
    response_model=List[ItemResponse],
    response_model_exclude={"raw_content", "chunks", "embeddings"}
)
def get_items(conn: sqlite3.Connection = Depends(get_db)):
    try:
        documents = repository.get_all_documents(conn)
        return documents
    except Exception as e:
        logger.error(f"Database error while fetching items: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
