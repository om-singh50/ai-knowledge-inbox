import ipaddress
import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 10.0
MAX_REDIRECTS = 5
MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5 MB
USER_AGENT = "AI-Knowledge-Inbox-Fetcher/1.0"
ALLOWED_SCHEMES = {"http", "https"}

class ScraperException(Exception):
    """Base exception for scraper service."""
    pass

class InvalidURLException(ScraperException):
    pass

class UnsafeTargetException(ScraperException):
    pass

class FetchTimeoutException(ScraperException):
    pass

class FetchConnectionException(ScraperException):
    pass

class InvalidContentTypeException(ScraperException):
    pass

class ContentTooLargeException(ScraperException):
    pass

class HTTPStatusException(ScraperException):
    pass

@dataclass
class FetchResult:
    final_url: str
    title: str
    text: str

def is_safe_url(url: str) -> bool:
    """
    Checks if a URL has a valid scheme and doesn't point to localhost or a private IP.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ALLOWED_SCHEMES:
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False

        if hostname.lower() == "localhost":
            return False

        try:
            ip = ipaddress.ip_address(hostname)
            if (ip.is_private or ip.is_loopback or ip.is_link_local or 
                ip.is_multicast or ip.is_unspecified or ip.is_reserved):
                return False
        except ValueError:
            # Not an IP address, domain name check passes for this basic validation
            pass
            
        return True
    except Exception:
        return False

def extract_content(html: str) -> tuple[str, str]:
    """
    Parses HTML, removes non-content elements, and extracts title and readable text.
    """
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    for element in soup(["script", "style", "noscript", "template", "nav", "footer", "header"]):
        element.decompose()

    main_content = soup.find("article")
    if not main_content:
        main_content = soup.find("main")
    if not main_content:
        main_content = soup.body

    if not main_content:
        return title, ""

    text = main_content.get_text(separator="\n", strip=True)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return title, text.strip()

async def fetch_url(url: str, timeout: float = DEFAULT_TIMEOUT) -> FetchResult:
    """
    Fetches URL content, enforcing safety, size, and content type checks.
    """
    if not is_safe_url(url):
        logger.warning(f"Fetch failed: unsafe or invalid URL - {url}")
        if urlparse(url).scheme not in ALLOWED_SCHEMES:
            raise InvalidURLException(f"Invalid or unsupported URL scheme: {url}")
        raise UnsafeTargetException(f"Target URL is unsafe (e.g., localhost/private IP): {url}")

    logger.info(f"Fetch started: {url}")
    
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            max_redirects=MAX_REDIRECTS,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT}
        ) as client:
            
            async with client.stream("GET", url) as response:
                if response.status_code >= 400:
                    logger.warning(f"Fetch failed: HTTP {response.status_code} - {url}")
                    raise HTTPStatusException(f"HTTP {response.status_code}")
                
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    logger.warning(f"Fetch failed: invalid content type {content_type} - {url}")
                    raise InvalidContentTypeException(f"Unsupported content type: {content_type}")
                
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_RESPONSE_SIZE:
                    logger.warning(f"Fetch failed: content too large - {url}")
                    raise ContentTooLargeException(f"Response exceeds maximum size of {MAX_RESPONSE_SIZE} bytes")
                
                content = b""
                async for chunk in response.aiter_bytes():
                    content += chunk
                    if len(content) > MAX_RESPONSE_SIZE:
                        logger.warning(f"Fetch failed: content too large during read - {url}")
                        raise ContentTooLargeException(f"Response exceeds maximum size of {MAX_RESPONSE_SIZE} bytes")
                
                html_text = content.decode("utf-8", errors="replace")
                final_url = str(response.url)
                
                logger.info(f"Fetch completed: {url} -> {final_url} (size: {len(content)})")
                
                title, text = extract_content(html_text)
                
                return FetchResult(
                    final_url=final_url,
                    title=title,
                    text=text
                )

    except httpx.TimeoutException as e:
        logger.warning(f"Fetch failed: timeout - {url}")
        raise FetchTimeoutException(f"Request timed out: {e}")
    except httpx.RequestError as e:
        logger.warning(f"Fetch failed: connection error - {url}")
        raise FetchConnectionException(f"Connection error: {e}")
