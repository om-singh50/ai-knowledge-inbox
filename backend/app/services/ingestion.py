import logging
import asyncio
import sqlite3
import time
from typing import Optional

from app.schemas.api import IngestRequest, IngestResponse, SourceType
from app.services.scraper import fetch_url, ScraperException
from app.services.chunking import chunk_text
from app.services.embedding import embedding_service
from app.db.repository import create_document_with_chunks, ChunkCreate

logger = logging.getLogger(__name__)

class IngestionError(Exception):
    """Base exception for ingestion errors."""
    pass

class IngestionEmptyContentError(IngestionError):
    pass

class IngestionService:
    def __init__(self, db_conn: sqlite3.Connection):
        self.db_conn = db_conn

    async def ingest(self, request: IngestRequest) -> IngestResponse:
        start_time = time.time()
        logger.info(f"Operation=Ingest, Status=Started, source_type={request.source_type.value}")
        
        raw_content = ""
        title = request.title
        final_url = None
        source = None

        # 1. Fetch & Extract
        if request.source_type == SourceType.NOTE:
            raw_content = request.content
        elif request.source_type == SourceType.URL:
            try:
                fetch_result = await fetch_url(str(request.url))
                raw_content = fetch_result.text
                final_url = fetch_result.final_url
                source = final_url
                if not title and fetch_result.title:
                    title = fetch_result.title
            except ScraperException as e:
                logger.error(f"Operation=Ingest, Status=Error, Step=Fetch, Elapsed={time.time()-start_time:.3f}s, Error={e}")
                raise IngestionError(f"Failed to fetch URL: {e}") from e
                
        if not raw_content or not raw_content.strip():
            logger.error(f"Operation=Ingest, Status=Error, Step=Extract, Reason=EmptyContent, Elapsed={time.time()-start_time:.3f}s")
            raise IngestionEmptyContentError("Extracted or provided content is empty.")

        # 2. Chunk
        try:
            chunks = chunk_text(raw_content)
        except Exception as e:
            logger.error(f"Operation=Ingest, Status=Error, Step=Chunking, Elapsed={time.time()-start_time:.3f}s, Error={e}")
            raise IngestionError(f"Failed to chunk text: {e}") from e
            
        if not chunks:
            logger.error(f"Operation=Ingest, Status=Error, Step=Chunking, Reason=ZeroChunks, Elapsed={time.time()-start_time:.3f}s")
            raise IngestionEmptyContentError("Chunking resulted in 0 chunks.")

        # 3. Embed
        try:
            # CPU bound operation, run in thread pool
            embeddings = await asyncio.to_thread(embedding_service.embed_batch, chunks)
        except Exception as e:
            logger.error(f"Operation=Ingest, Status=Error, Step=Embedding, Elapsed={time.time()-start_time:.3f}s, Error={e}")
            raise IngestionError(f"Failed to generate embeddings: {e}") from e
            
        if len(embeddings) != len(chunks):
            logger.error(f"Operation=Ingest, Status=Error, Step=Embedding, Reason=Mismatch, Chunks={len(chunks)}, Embeddings={len(embeddings)}, Elapsed={time.time()-start_time:.3f}s")
            raise IngestionError("Embedding generation mismatch.")

        # 4. Persist
        chunks_data = [
            ChunkCreate(content=c, embedding=e) 
            for c, e in zip(chunks, embeddings)
        ]
        
        try:
            doc = create_document_with_chunks(
                conn=self.db_conn,
                source_type=request.source_type.value,
                raw_content=raw_content,
                chunks_data=chunks_data,
                source=source,
                title=title
            )
        except Exception as e:
            logger.error(f"Operation=Ingest, Status=Error, Step=Persistence, Elapsed={time.time()-start_time:.3f}s, Error={e}")
            raise IngestionError(f"Failed to persist document: {e}") from e

        logger.info(f"Operation=Ingest, Status=Success, DocumentID={doc['id']}, Chunks={len(chunks)}, Elapsed={time.time()-start_time:.3f}s")

        from datetime import datetime
        created_at_dt = datetime.fromisoformat(doc['created_at'].replace('Z', '+00:00')) if isinstance(doc['created_at'], str) else doc['created_at']

        return IngestResponse(
            id=doc['id'],
            source_type=request.source_type,
            title=doc.get('title'),
            url=final_url,
            created_at=created_at_dt,
            chunk_count=len(chunks)
        )
