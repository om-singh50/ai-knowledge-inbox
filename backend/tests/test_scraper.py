import pytest
import httpx
from app.services.scraper import (
    fetch_url,
    extract_content,
    is_safe_url,
    InvalidURLException,
    UnsafeTargetException,
    FetchTimeoutException,
    FetchConnectionException,
    InvalidContentTypeException,
    ContentTooLargeException,
    HTTPStatusException
)

def test_is_safe_url():
    assert is_safe_url("https://example.com") is True
    assert is_safe_url("http://example.com") is True
    
    assert is_safe_url("ftp://example.com") is False
    assert is_safe_url("file:///etc/passwd") is False
    assert is_safe_url("javascript:alert(1)") is False
    
    assert is_safe_url("http://localhost") is False
    assert is_safe_url("http://127.0.0.1") is False
    assert is_safe_url("https://10.0.0.1") is False
    assert is_safe_url("http://192.168.1.1") is False
    assert is_safe_url("http://172.16.0.1") is False
    
    # Should not throw for unparseable garbage
    assert is_safe_url("not a url at all") is False

def test_extract_content_basic():
    html = """
    <html>
        <head><title>Test Title</title></head>
        <body>
            <nav>Menu</nav>
            <main>
                <h1>Heading</h1>
                <p>This is a paragraph.</p>
                <script>alert('bad');</script>
            </main>
            <footer>Footer text</footer>
        </body>
    </html>
    """
    title, text = extract_content(html)
    assert title == "Test Title"
    assert "Menu" not in text
    assert "Footer text" not in text
    assert "alert('bad');" not in text
    assert "Heading\nThis is a paragraph." in text

def test_extract_content_article_priority():
    html = """
    <html>
        <body>
            <div>Sidebar</div>
            <article>Real content here</article>
        </body>
    </html>
    """
    title, text = extract_content(html)
    assert text == "Real content here"

def test_extract_content_empty():
    html = "<html><body></body></html>"
    title, text = extract_content(html)
    assert title == ""
    assert text == ""

@pytest.mark.asyncio
async def test_fetch_url_success(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com",
        text="<html><head><title>OK</title></head><body>Hello</body></html>",
        headers={"Content-Type": "text/html"}
    )
    result = await fetch_url("https://example.com")
    assert result.final_url == "https://example.com"
    assert result.title == "OK"
    assert result.text == "Hello"

@pytest.mark.asyncio
async def test_fetch_url_timeout(httpx_mock):
    httpx_mock.add_exception(httpx.ReadTimeout("timeout"), url="https://example.com")
    with pytest.raises(FetchTimeoutException):
        await fetch_url("https://example.com")

@pytest.mark.asyncio
async def test_fetch_url_connection_error(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("conn error"), url="https://example.com")
    with pytest.raises(FetchConnectionException):
        await fetch_url("https://example.com")

@pytest.mark.asyncio
async def test_fetch_url_invalid_content_type(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com",
        content=b"dummy",
        headers={"Content-Type": "application/pdf"}
    )
    with pytest.raises(InvalidContentTypeException):
        await fetch_url("https://example.com")

@pytest.mark.asyncio
async def test_fetch_url_too_large(httpx_mock):
    # Simulate Content-Length header check
    httpx_mock.add_response(
        url="https://example.com",
        headers={"Content-Type": "text/html", "Content-Length": "10485760"} # 10MB
    )
    with pytest.raises(ContentTooLargeException):
        await fetch_url("https://example.com")

@pytest.mark.asyncio
async def test_fetch_url_too_large_streaming(httpx_mock):
    # Missing Content-Length, but content itself is large
    # For testing, we mock a response that returns too much data
    # pytest-httpx doesn't easily stream infinite mock data, 
    # but we can provide content larger than MAX_RESPONSE_SIZE.
    from app.services.scraper import MAX_RESPONSE_SIZE
    httpx_mock.add_response(
        url="https://example.com",
        headers={"Content-Type": "text/html"},
        content=b"a" * (MAX_RESPONSE_SIZE + 1)
    )
    with pytest.raises(ContentTooLargeException):
        await fetch_url("https://example.com")

@pytest.mark.asyncio
async def test_fetch_url_non_200(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com",
        status_code=404,
        headers={"Content-Type": "text/html"}
    )
    with pytest.raises(HTTPStatusException):
        await fetch_url("https://example.com")

@pytest.mark.asyncio
async def test_fetch_url_unsafe_url():
    with pytest.raises(UnsafeTargetException):
        await fetch_url("http://localhost")
    with pytest.raises(InvalidURLException):
        await fetch_url("file:///etc/passwd")

@pytest.mark.asyncio
async def test_fetch_url_redirect(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com",
        status_code=301,
        headers={"Location": "https://example.com/new"}
    )
    httpx_mock.add_response(
        url="https://example.com/new",
        text="<html><body>New location</body></html>",
        headers={"Content-Type": "text/html"}
    )
    result = await fetch_url("https://example.com")
    assert result.final_url == "https://example.com/new"
    assert result.text == "New location"
