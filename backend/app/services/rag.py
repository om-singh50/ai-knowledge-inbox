import logging
import time
from typing import List, Optional
import sqlite3
from dataclasses import dataclass

from app.services.embedding import embedding_service
from app.services.vector_search import search, SearchResult
from app.services.generation import generation_service, ContextChunk
from app.db.repository import get_document_by_id

logger = logging.getLogger(__name__)

@dataclass
class RAGChunkSource:
    document_id: str
    source_type: str
    title: Optional[str]
    source: Optional[str]
    content: str
    relevance_score: float

@dataclass
class RAGResult:
    answer: str
    retrieved_context: List[RAGChunkSource]

def ask_question(conn: sqlite3.Connection, question: str, top_k: int = 5) -> RAGResult:
    start_time = time.time()
    if not question or not question.strip():
        return RAGResult(
            answer="Please provide a valid question.",
            retrieved_context=[]
        )

    logger.info(f"Operation=Query, Status=Started, top_k={top_k}")
    
    # 1. Embed question
    try:
        query_embedding = embedding_service.embed_query(question)
    except Exception as e:
        logger.error(f"Operation=Query, Status=Error, Step=Embedding, Elapsed={time.time()-start_time:.3f}s, Error={e}")
        return RAGResult(
            answer="I encountered an error while processing your question.",
            retrieved_context=[]
        )

    # 2. Vector search
    search_results = search(conn, query_embedding, top_k=top_k)
    
    if not search_results:
        logger.info(f"Operation=Query, Status=Success, Step=Search, Found=0, Elapsed={time.time()-start_time:.3f}s")
        return RAGResult(
            answer="The saved knowledge does not contain enough information to answer this question.",
            retrieved_context=[]
        )

    # 3. Convert retrieved chunks to context and resolve document metadata
    context_chunks = []
    rag_sources = []
    for res in search_results:
        doc = get_document_by_id(conn, res.document_id)
        
        # safely handle missing documents
        source_type = doc["source_type"] if doc else "unknown"
        title = doc["title"] if doc else None
        source_url = doc["source"] if doc else None
        
        rag_sources.append(RAGChunkSource(
            document_id=res.document_id,
            source_type=source_type,
            title=title,
            source=source_url,
            content=res.content,
            relevance_score=res.relevance_score
        ))

        context_chunks.append(ContextChunk(
            content=res.content,
            document_id=res.document_id,
        ))

    # 4. Generate answer
    try:
        answer = generation_service.generate_answer(question, context_chunks)
    except Exception as e:
        logger.error(f"Operation=Query, Status=Error, Step=Generation, Elapsed={time.time()-start_time:.3f}s, Error={e}")
        return RAGResult(
            answer="I encountered an error while generating the answer.",
            retrieved_context=rag_sources
        )

    logger.info(f"Operation=Query, Status=Success, Step=Complete, Sources={len(rag_sources)}, Elapsed={time.time()-start_time:.3f}s")
    return RAGResult(
        answer=answer,
        retrieved_context=rag_sources
    )
