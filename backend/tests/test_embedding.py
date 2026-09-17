import pytest
from unittest.mock import patch, MagicMock

from app.services.embedding import (
    EmbeddingService,
    EmbeddingInputError,
    EmbeddingInitializationError,
    EmbeddingServiceError,
)
from app.core.config import settings

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton instance before each test."""
    EmbeddingService._instance = None
    EmbeddingService._client = None
    yield
    EmbeddingService._instance = None
    EmbeddingService._client = None

@pytest.fixture(autouse=True)
def setup_settings():
    original_key = settings.gemini_api_key
    settings.gemini_api_key = "test_key"
    yield
    settings.gemini_api_key = original_key

@pytest.fixture
def mock_genai_client():
    with patch("app.services.embedding.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Fake embed_content method
        def fake_embed_content(model, contents, config):
            class FakeEmbedding:
                def __init__(self, values):
                    self.values = values
            
            class FakeResponse:
                def __init__(self, embeddings):
                    self.embeddings = embeddings
                    
            if isinstance(contents, str):
                return FakeResponse([FakeEmbedding([0.1, 0.2, 0.3])])
            return FakeResponse([FakeEmbedding([0.1, 0.2, 0.3]) for _ in contents])
            
        mock_client.models.embed_content.side_effect = fake_embed_content
        yield mock_client_class

def test_embed_single_document(mock_genai_client):
    service = EmbeddingService()
    result = service.embed_document("hello world")
    
    assert result == [0.1, 0.2, 0.3]
    mock_genai_client.assert_called_once_with(api_key="test_key")
    
    client_instance = mock_genai_client.return_value
    client_instance.models.embed_content.assert_called_once()
    
    # check kwargs
    _, kwargs = client_instance.models.embed_content.call_args
    assert kwargs["contents"] == ["hello world"]
    assert kwargs["config"].task_type == "RETRIEVAL_DOCUMENT"

def test_embed_query(mock_genai_client):
    service = EmbeddingService()
    result = service.embed_query("question?")
    
    assert result == [0.1, 0.2, 0.3]
    client_instance = mock_genai_client.return_value
    
    # check kwargs
    _, kwargs = client_instance.models.embed_content.call_args
    assert kwargs["contents"] == ["question?"]
    assert kwargs["config"].task_type == "RETRIEVAL_QUERY"

def test_embed_batch_texts(mock_genai_client):
    service = EmbeddingService()
    result = service.embed_documents(["hello", "world"])
    
    assert result == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
    client_instance = mock_genai_client.return_value
    
    _, kwargs = client_instance.models.embed_content.call_args
    assert kwargs["contents"] == ["hello", "world"]
    assert kwargs["config"].task_type == "RETRIEVAL_DOCUMENT"

def test_embed_empty_text():
    service = EmbeddingService()
    with pytest.raises(EmbeddingInputError, match="cannot be empty or whitespace"):
        service.embed("")
        
    with pytest.raises(EmbeddingInputError, match="cannot be empty or whitespace"):
        service.embed("   ")

def test_embed_batch_empty_text():
    service = EmbeddingService()
    with pytest.raises(EmbeddingInputError, match="cannot be empty"):
        service.embed_batch([])
        
    with pytest.raises(EmbeddingInputError, match="cannot be empty or whitespace"):
        service.embed_batch(["hello", "  "])

def test_missing_api_key():
    settings.gemini_api_key = ""
    service = EmbeddingService()
    with pytest.raises(EmbeddingInitializationError, match="GEMINI_API_KEY is not configured"):
        service.embed("test")

def test_client_loaded_only_once(mock_genai_client):
    service = EmbeddingService()
    service.embed("first call")
    service.embed("second call")
    service.embed_batch(["third call"])
    
    # Should only be instantiated once
    mock_genai_client.assert_called_once()
    
    assert mock_genai_client.return_value.models.embed_content.call_count == 3

def test_invalid_provider_response(mock_genai_client):
    client_instance = mock_genai_client.return_value
    class FakeBadResponse:
        embeddings = []
    client_instance.models.embed_content.side_effect = lambda **k: FakeBadResponse()
    
    service = EmbeddingService()
    with pytest.raises(EmbeddingServiceError, match="missing embeddings"):
        service.embed("test")

def test_api_error_retry(mock_genai_client):
    from google.genai.errors import APIError
    client_instance = mock_genai_client.return_value
    
    class FakeAPIError(APIError):
        def __init__(self, message, code):
            self.message = message
            self.code = code
            super().__init__(message)
            
    # Raise transient error then succeed
    def side_effect(*args, **kwargs):
        if client_instance.models.embed_content.call_count == 1:
            raise Exception("Transient network issue")
        class FakeResponse:
            class FakeEmbedding:
                values = [0.1, 0.2]
            embeddings = [FakeEmbedding()]
        return FakeResponse()

    client_instance.models.embed_content.side_effect = side_effect
    
    service = EmbeddingService()
    result = service.embed("test")
    assert result == [0.1, 0.2]
    assert client_instance.models.embed_content.call_count == 2

def test_api_error_fatal(mock_genai_client):
    from google.genai.errors import APIError
    client_instance = mock_genai_client.return_value
    
    class FakeAPIError(APIError):
        def __init__(self, message, code):
            super().__init__(message, code, {})
            self.code = code
            self.message = message
            
    # Raise fatal error
    client_instance.models.embed_content.side_effect = FakeAPIError("Quota exceeded", 429)
    
    service = EmbeddingService()
    with pytest.raises(EmbeddingServiceError, match="API Error 429"):
        service.embed("test")
    # Fatal error should fail immediately, no retry
    assert client_instance.models.embed_content.call_count == 1
