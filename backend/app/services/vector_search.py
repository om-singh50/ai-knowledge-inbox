import math
import logging
import time
from dataclasses import dataclass
from typing import List
import sqlite3

from app.db.repository import get_all_chunks

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    relevance_score: float

def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        return 0.0
    
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
        
    return dot_product / (norm_a * norm_b)

def search(
    conn: sqlite3.Connection,
    query_embedding: List[float],
    top_k: int = 5
) -> List[SearchResult]:
    start_time = time.time()
    
    if not query_embedding:
        return []
        
    query_dim = len(query_embedding)
    
    chunks = get_all_chunks(conn)
    candidates = []
    
    for chunk in chunks:
        emb = chunk.get("embedding")
        if not emb:
            continue
        if not isinstance(emb, list):
            continue
        if len(emb) != query_dim:
            continue
            
        score = cosine_similarity(query_embedding, emb)
        
        candidates.append(SearchResult(
            chunk_id=chunk["id"],
            document_id=chunk["document_id"],
            chunk_index=chunk["chunk_index"],
            content=chunk["content"],
            relevance_score=score
        ))
    
    # Sort by relevance_score DESC, then document_id ASC, then chunk_index ASC (deterministic)
    candidates.sort(key=lambda x: (-x.relevance_score, x.document_id, x.chunk_index))
    
    results = candidates[:top_k]
    
    elapsed = time.time() - start_time
    logger.info(
        f"Vector search completed: candidate_count={len(candidates)}, "
        f"top_k={top_k}, returned_count={len(results)}, "
        f"elapsed_time={elapsed:.4f}s"
    )
    
    return results
