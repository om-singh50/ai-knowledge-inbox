import logging
import time
from typing import List, Optional
from dataclasses import dataclass

from google import genai
from google.genai.errors import APIError

from app.core.config import settings

logger = logging.getLogger(__name__)

class GenerationInitializationError(Exception):
    """Raised when the generation model fails to initialize or authentication is missing."""
    pass

class GenerationInputError(Exception):
    """Raised when the input question is invalid."""
    pass

class GenerationServiceError(Exception):
    """Raised for API errors, network issues, or quota limitations."""
    pass


@dataclass
class ContextChunk:
    content: str
    title: Optional[str] = None
    url: Optional[str] = None
    source_type: Optional[str] = None
    document_id: Optional[str] = None


class GenerationService:
    _instance: Optional["GenerationService"] = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GenerationService, cls).__new__(cls)
        return cls._instance

    def _get_client(self):
        if self._client is None:
            if not settings.gemini_api_key:
                raise GenerationInitializationError("GEMINI_API_KEY is not configured.")
            logger.info("Initializing Gemini generation client")
            try:
                self._client = genai.Client(api_key=settings.gemini_api_key)
            except Exception as e:
                raise GenerationInitializationError(f"Failed to initialize Gemini client: {e}") from e
        return self._client

    def generate_answer(self, question: str, context: List[ContextChunk]) -> str:
        if not question or not question.strip():
            raise GenerationInputError("Question cannot be empty or whitespace-only.")

        client = self._get_client()
        model_name = settings.gemini_generation_model or "gemini-3.6-flash"

        start_time = time.time()
        logger.info(f"Answer generation started for question. Context chunks: {len(context)}")

        system_instruction = (
            "You are a helpful assistant. "
            "Answer the user's question using ONLY the supplied context. "
            "Do not invent facts that are not supported by the context. "
            "Do not use outside knowledge to fill missing information. "
            "If the supplied context is insufficient, clearly say that the information is not available in the saved knowledge. "
            "Do not fabricate sources. "
            "Do not fabricate URLs. "
            "Do not claim that information exists in a source when it is not present in the supplied context. "
            "Keep the answer concise and directly relevant to the question."
        )

        context_parts = []
        for i, chunk in enumerate(context):
            source_header = f"[Source {i+1}]"
            if chunk.title:
                source_header += f" Title: {chunk.title}"
            if chunk.url:
                source_header += f" URL: {chunk.url}"
            context_parts.append(f"{source_header}\n{chunk.content}")
        
        context_str = "\n\n".join(context_parts)

        prompt = (
            f"SYSTEM INSTRUCTIONS\n{system_instruction}\nEND SYSTEM INSTRUCTIONS\n\n"
            f"RETRIEVED CONTEXT\n{context_str}\nEND RETRIEVED CONTEXT\n\n"
            f"USER QUESTION\n{question.strip()}\nEND USER QUESTION"
        )
        
        attempts = 0
        max_attempts = 2
        while attempts < max_attempts:
            attempts += 1
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )

                if not response or not response.text:
                    raise GenerationServiceError("Invalid provider response: empty or missing text.")

                elapsed = time.time() - start_time
                logger.info(f"Answer generation completed in {elapsed:.3f}s. Attempts: {attempts}")
                return response.text.strip()

            except APIError as e:
                # Determine if it's transient or fatal
                if hasattr(e, 'code'):
                    if e.code in (401, 403, 400, 429):
                        logger.error(f"Generation failed (fatal API error: {e.code}): {e}")
                        raise GenerationServiceError(f"API Error {e.code}: {e.message}") from e

                if attempts == max_attempts:
                    logger.error(f"Generation failed after {attempts} attempts: {e}")
                    raise GenerationServiceError(f"API Error: {e}") from e
                    
            except Exception as e:
                if attempts == max_attempts:
                    logger.error(f"Generation failed (unexpected error): {e}")
                    raise GenerationServiceError(f"Unexpected Error: {e}") from e

generation_service = GenerationService()
