import pytest
from unittest.mock import MagicMock, patch
from google.genai.errors import APIError

from app.core.config import settings
from app.services.generation import (
    GenerationService,
    ContextChunk,
    GenerationInitializationError,
    GenerationInputError,
    GenerationServiceError,
)

@pytest.fixture
def mock_genai_client():
    with patch("app.services.generation.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        yield mock_client

@pytest.fixture
def service(mock_genai_client):
    service = GenerationService()
    # reset singleton client for tests
    service._client = None
    return service

def test_generate_answer_success(service, mock_genai_client):
    settings.gemini_api_key = "test_key"
    mock_response = MagicMock()
    mock_response.text = "This is a grounded answer."
    mock_genai_client.models.generate_content.return_value = mock_response

    context = [
        ContextChunk(content="FastAPI is a Python framework.", title="FastAPI Docs")
    ]
    answer = service.generate_answer("What is FastAPI?", context)

    assert answer == "This is a grounded answer."
    
    # Check that client is reused (Q)
    assert service._get_client() is mock_genai_client
    
    # Check what was sent (B, C, D, E, F, G)
    call_args = mock_genai_client.models.generate_content.call_args
    assert call_args is not None
    kwargs = call_args[1]
    prompt = kwargs["contents"]
    
    assert "What is FastAPI?" in prompt
    assert "FastAPI is a Python framework." in prompt
    assert "FastAPI Docs" in prompt
    assert "SYSTEM INSTRUCTIONS" in prompt
    assert "RETRIEVED CONTEXT" in prompt
    assert "USER QUESTION" in prompt
    assert "Do not invent facts" in prompt
    assert "not available in the saved knowledge" in prompt

def test_empty_context_handled_safely(service, mock_genai_client):
    # (H) Empty context is handled safely
    settings.gemini_api_key = "test_key"
    mock_response = MagicMock()
    mock_response.text = "I don't know."
    mock_genai_client.models.generate_content.return_value = mock_response

    answer = service.generate_answer("What is FastAPI?", [])
    assert answer == "I don't know."
    
    prompt = mock_genai_client.models.generate_content.call_args[1]["contents"]
    assert "RETRIEVED CONTEXT\n\nEND RETRIEVED CONTEXT" in prompt

def test_empty_question_rejected(service):
    # (I) Empty question is rejected
    with pytest.raises(GenerationInputError):
        service.generate_answer("", [])

def test_whitespace_question_rejected(service):
    # (J) Whitespace-only question is rejected
    with pytest.raises(GenerationInputError):
        service.generate_answer("   \n", [])

def test_missing_api_key(service):
    # (K) Missing API key
    settings.gemini_api_key = ""
    with pytest.raises(GenerationInitializationError):
        service.generate_answer("Hello", [])

def test_auth_failure(service, mock_genai_client):
    # (L) Authentication failure
    settings.gemini_api_key = "test_key"
    mock_error = APIError("Unauthorized", {})
    mock_error.code = 401
    mock_genai_client.models.generate_content.side_effect = mock_error

    with pytest.raises(GenerationServiceError, match="API Error 401"):
        service.generate_answer("Hello", [])
    
    assert mock_genai_client.models.generate_content.call_count == 1  # No retry

def test_rate_limit_failure(service, mock_genai_client):
    # (M) Rate-limit/quota failure
    settings.gemini_api_key = "test_key"
    mock_error = APIError("Too Many Requests", {})
    mock_error.code = 429
    mock_genai_client.models.generate_content.side_effect = mock_error

    with pytest.raises(GenerationServiceError, match="API Error 429"):
        service.generate_answer("Hello", [])
    
    assert mock_genai_client.models.generate_content.call_count == 1  # No retry

def test_network_failure_with_retry(service, mock_genai_client):
    # (N) Network/provider failure (transient)
    settings.gemini_api_key = "test_key"
    mock_error = APIError("Internal Server Error", {})
    mock_error.code = 500
    
    mock_response = MagicMock()
    mock_response.text = "Success on retry"
    
    # Fail first, succeed second
    mock_genai_client.models.generate_content.side_effect = [mock_error, mock_response]

    answer = service.generate_answer("Hello", [])
    assert answer == "Success on retry"
    assert mock_genai_client.models.generate_content.call_count == 2

def test_empty_model_response(service, mock_genai_client):
    # (O) Empty model response
    settings.gemini_api_key = "test_key"
    mock_response = MagicMock()
    mock_response.text = ""
    mock_genai_client.models.generate_content.return_value = mock_response

    with pytest.raises(GenerationServiceError, match="empty or missing text"):
        service.generate_answer("Hello", [])

def test_malformed_provider_response(service, mock_genai_client):
    # (P) Malformed provider response (no text attribute)
    settings.gemini_api_key = "test_key"
    mock_response = MagicMock(spec=[]) # doesn't have .text
    mock_genai_client.models.generate_content.return_value = mock_response

    with pytest.raises(GenerationServiceError, match="Unexpected Error:"):
        service.generate_answer("Hello", [])
