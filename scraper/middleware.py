"""
Middleware system for request processing.
Inspired by Scrapy's middleware architecture.
"""
import logging
import random
import time
from typing import Dict, Any, Optional, List
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class BaseMiddleware:
    """Base class for all middlewares."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request before it's sent."""
        return request
    
    def process_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process a response after it's received."""
        return response


class UserAgentMiddleware(BaseMiddleware):
    """Rotates user agents for each request."""
    
    def __init__(self):
        super().__init__()
        self.ua = UserAgent()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Add a random user agent to the request."""
        if 'headers' not in request:
            request['headers'] = {}
        
        # Try to get a random user agent, fallback to predefined list
        try:
            user_agent = self.ua.random
        except Exception:
            user_agent = random.choice(self.user_agents)
        
        request['headers']['User-Agent'] = user_agent
        self.logger.debug(f"Set User-Agent: {user_agent[:50]}...")
        return request


class ProxyMiddleware(BaseMiddleware):
    """Handles proxy configuration and rotation."""
    
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__()
        self.proxies = proxies or []
        self.current_proxy_index = 0
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Add proxy to the request if configured."""
        if not self.proxies:
            return request
        
        proxy = self.proxies[self.current_proxy_index]
        request['proxy'] = proxy
        
        # Rotate to next proxy
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
        self.logger.debug(f"Using proxy: {proxy}")
        return request


class RetryMiddleware(BaseMiddleware):
    """Implements retry logic with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.0):
        super().__init__()
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Add retry configuration to the request."""
        request['_retry_config'] = {
            'max_retries': self.max_retries,
            'backoff_factor': self.backoff_factor
        }
        return request


class DelayMiddleware(BaseMiddleware):
    """Adds random delays between requests to avoid rate limiting."""
    
    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0):
        super().__init__()
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Add delay before processing request."""
        current_time = time.time()
        
        if self.last_request_time > 0:
            elapsed = current_time - self.last_request_time
            delay = random.uniform(self.min_delay, self.max_delay)
            
            if elapsed < delay:
                sleep_time = delay - elapsed
                self.logger.debug(f"Sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        return request


class HeadersMiddleware(BaseMiddleware):
    """Adds custom headers to requests."""
    
    def __init__(self, headers: Optional[Dict[str, str]] = None):
        super().__init__()
        self.default_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        if headers:
            self.default_headers.update(headers)
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Add default headers to the request."""
        if 'headers' not in request:
            request['headers'] = {}
        
        # Add default headers that aren't already set
        for key, value in self.default_headers.items():
            if key not in request['headers']:
                request['headers'][key] = value
        
        return request


class MiddlewareManager:
    """Manages and orchestrates all middlewares."""
    
    def __init__(self):
        self.middlewares: List[BaseMiddleware] = []
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize default middlewares
        self._setup_default_middlewares()
    
    def _setup_default_middlewares(self):
        """Setup default middlewares in the correct order."""
        # Order matters: Headers -> UserAgent -> Delay -> Retry -> Proxy
        self.add_middleware(HeadersMiddleware())
        self.add_middleware(UserAgentMiddleware())
        self.add_middleware(DelayMiddleware())
        self.add_middleware(RetryMiddleware())
    
    def add_middleware(self, middleware: BaseMiddleware):
        """Add a middleware to the manager."""
        self.middlewares.append(middleware)
        self.logger.debug(f"Added middleware: {middleware.__class__.__name__}")
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request through all middlewares."""
        for middleware in self.middlewares:
            try:
                request = middleware.process_request(request)
            except Exception as e:
                self.logger.error(f"Error in {middleware.__class__.__name__}.process_request: {e}")
        
        return request
    
    def process_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process a response through all middlewares in reverse order."""
        for middleware in reversed(self.middlewares):
            try:
                response = middleware.process_response(response)
            except Exception as e:
                self.logger.error(f"Error in {middleware.__class__.__name__}.process_response: {e}")
        
        return response
    
    def configure_proxy(self, proxies: List[str]):
        """Configure proxy middleware."""
        # Remove existing proxy middleware
        self.middlewares = [m for m in self.middlewares if not isinstance(m, ProxyMiddleware)]
        
        # Add new proxy middleware
        if proxies:
            self.add_middleware(ProxyMiddleware(proxies))
    
    def configure_delay(self, min_delay: float, max_delay: float):
        """Configure delay middleware."""
        # Remove existing delay middleware
        self.middlewares = [m for m in self.middlewares if not isinstance(m, DelayMiddleware)]
        
        # Add new delay middleware
        self.add_middleware(DelayMiddleware(min_delay, max_delay))
