import logging
import time
from typing import List, Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingInitializationError(Exception):
    """Raised when the embedding model fails to initialize or authentication is missing."""
    pass

class EmbeddingInputError(Exception):
    """Raised when the input text is invalid (e.g., empty or whitespace)."""
    pass

class EmbeddingServiceError(Exception):
    """Raised for API errors, network issues, or quota limitations."""
    pass


class EmbeddingService:
    _instance: Optional["EmbeddingService"] = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance

    def _get_client(self):
        if self._client is None:
            if not settings.gemini_api_key:
                raise EmbeddingInitializationError("GEMINI_API_KEY is not configured.")
            logger.info("Initializing Gemini embedding client")
            try:
                self._client = genai.Client(api_key=settings.gemini_api_key)
            except Exception as e:
                raise EmbeddingInitializationError(f"Failed to initialize Gemini client: {e}") from e
        return self._client

    def _call_api_with_retry(self, texts: List[str], task_type: str) -> List[List[float]]:
        client = self._get_client()
        model_name = settings.embedding_model or "gemini-embedding-001"
        
        start_time = time.time()
        logger.info(f"Embedding operation started for {len(texts)} texts, task_type: {task_type}")

        attempts = 0
        max_attempts = 2  # One retry for transient errors
        while attempts < max_attempts:
            attempts += 1
            try:
                # https://google.github.io/google-genai/
                # The SDK takes `model`, `contents`, and `config` which can specify `task_type`
                # contents can be a single string or a list of strings
                config = types.EmbedContentConfig(task_type=task_type)
                
                response = client.models.embed_content(
                    model=model_name,
                    contents=texts,
                    config=config
                )
                
                # Check response
                if not response or not response.embeddings:
                    raise EmbeddingServiceError("Invalid provider response: missing embeddings.")
                
                if len(response.embeddings) != len(texts):
                    raise EmbeddingServiceError("Provider returned mismatched number of embeddings.")
                
                result = [emb.values for emb in response.embeddings]
                
                elapsed = time.time() - start_time
                logger.info(f"Embedding operation completed in {elapsed:.3f}s for {len(texts)} texts")
                return result
                
            except APIError as e:
                # Determine if it's transient or fatal
                # 401 Unauthorized, 403 Forbidden, 400 Bad Request, 429 Too Many Requests
                if hasattr(e, 'code'):
                    if e.code in (401, 403, 400, 429):
                        logger.error(f"Embedding operation failed (fatal API error: {e.code}): {e}")
                        raise EmbeddingServiceError(f"API Error {e.code}: {e.message}") from e
                
                if attempts == max_attempts:
                    logger.error(f"Embedding operation failed after {attempts} attempts: {e}")
                    raise EmbeddingServiceError(f"API Error: {e}") from e
                    
            except Exception as e:
                # Network or unexpected error
                if attempts == max_attempts:
                    logger.error(f"Embedding operation failed (unexpected error): {e}")
                    raise EmbeddingServiceError(f"Unexpected Error: {e}") from e

    def embed_document(self, text: str) -> List[float]:
        return self.embed(text, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> List[float]:
        return self.embed(text, task_type="RETRIEVAL_QUERY")

    def embed(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
        if not text or not text.strip():
            raise EmbeddingInputError("Input text cannot be empty or whitespace-only.")
        
        results = self._call_api_with_retry([text], task_type)
        return results[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embed_batch(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_batch(self, texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
        if not texts:
            raise EmbeddingInputError("Input batch cannot be empty.")
        
        for text in texts:
            if not text or not text.strip():
                raise EmbeddingInputError("Input text in batch cannot be empty or whitespace-only.")
                
        return self._call_api_with_retry(texts, task_type)

# Global instance for easy import
embedding_service = EmbeddingService()
