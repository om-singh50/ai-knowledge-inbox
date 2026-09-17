from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3
import logging

from app.schemas.api import IngestRequest, IngestResponse
from app.services.ingestion import IngestionService, IngestionError, IngestionEmptyContentError
from app.api.deps import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    request: IngestRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        service = IngestionService(db)
        response = await service.ingest(request)
        return response
    except IngestionEmptyContentError as e:
        logger.warning(f"Bad Request: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except IngestionError as e:
        error_msg = str(e)
        if "Failed to fetch URL" in error_msg:
            logger.warning(f"Upstream fetch failure: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch URL content.")
        if "Embedding generation" in error_msg or "Failed to generate embeddings" in error_msg:
            logger.error(f"Service Unavailable: {e}")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Embedding service unavailable.")
            
        logger.error(f"Ingestion Error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during ingestion.")
    except Exception as e:
        logger.error(f"Unexpected error during ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")
