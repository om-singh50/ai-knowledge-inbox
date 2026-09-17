import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.api.deps import get_db
from app.schemas.api import QueryRequest, QueryResponse, SourceSnippet, SourceType
from app.services.rag import ask_question

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
def query_endpoint(
    request: QueryRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        rag_result = ask_question(db, request.question)
        
        sources = []
        for src in rag_result.retrieved_context:
            try:
                stype = SourceType(src.source_type)
            except ValueError:
                stype = SourceType.NOTE
                
            sources.append(
                SourceSnippet(
                    document_id=src.document_id,
                    source_type=stype,
                    title=src.title,
                    url=src.source,
                    content=src.content,
                    relevance_score=src.relevance_score
                )
            )
            
        return QueryResponse(
            answer=rag_result.answer,
            sources=sources
        )
    except Exception as e:
        logger.error(f"Unexpected error during query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your query."
        )
