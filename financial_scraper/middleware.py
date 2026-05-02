import logging
import random
from typing import Optional, List, Any

from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

logger = logging.getLogger(__name__)

class SpiderMiddleware:
    def __init__(self, proxies: Optional[List[str]] = None):
        """Initialize middleware with optional proxy list."""
        self.ua = UserAgent()
        self.proxies = proxies or []
        self._current_proxy_index = 0

    def get_random_ua(self) -> str:
        """Get a random User-Agent string."""
        return self.ua.random

    def get_proxy(self) -> Optional[str]:
        """Get the next proxy from the list in a round-robin fashion."""
        if not self.proxies:
            return None
        proxy = self.proxies[self._current_proxy_index]
        self._current_proxy_index = (self._current_proxy_index + 1) % len(self.proxies)
        logger.debug(f"Using proxy: {proxy}")
        return proxy

    def get_httpx_client(self, use_proxy: bool = False, timeout: float = 30.0) -> httpx.Client:
        """Create and return an httpx Client with random UA and optional proxy."""
        headers = {
            "User-Agent": self.get_random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        proxy_dict = None
        if use_proxy and self.proxies:
            proxy_url = self.get_proxy()
            if proxy_url:
                proxy_dict = proxy_url

        client = httpx.Client(headers=headers, proxy=proxy_dict, timeout=timeout)
        logger.debug(f"Created httpx client with UA: {headers['User-Agent'][:50]}...")
        return client

    def get_playwright_context_options(self, use_proxy: bool = False) -> dict:
        """Get options for Playwright browser context."""
        options = {
            "user_agent": self.get_random_ua(),
            "viewport": {"width": 1920, "height": 1080},
        }
        if use_proxy and self.proxies:
            proxy_url = self.get_proxy()
            if proxy_url:
                options["proxy"] = {"server": proxy_url}
        return options

    @staticmethod
    def with_retry(max_attempts: int = 3, min_wait: int = 2, max_wait: int = 10):
        """Decorator for retrying a function with exponential backoff on HTTP/Request errors."""
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError, TimeoutError)),
            before_sleep=lambda retry_state: logger.warning(
                f"Retrying {retry_state.fn.__name__} after {retry_state.attempt_number} failures "
                f"(Exception: {retry_state.outcome.exception()})"
            )
        )

# Example usage for retry:
# @SpiderMiddleware.with_retry(max_attempts=3)
# def fetch_url(url: str):
#     ...
