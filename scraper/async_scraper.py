"""
High-performance async scraper using httpx for static content.
Supports concurrent fetching with rate limiting and middleware integration.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from bs4 import BeautifulSoup
import httpx
from scraper.middleware import MiddlewareManager
from scraper.pipelines import PipelineManager
from scraper.state_manager import StateManager
from scraper.base_scraper import BaseScraper
from scraper.config_loader import ConfigLoader
from scraper.extractor import Extractor

logger = logging.getLogger(__name__)


class AsyncScraper(BaseScraper):
    """
    High-performance async scraper for static content.
    Uses httpx for concurrent HTTP requests.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, 
                 concurrency: int = 5, 
                 rate_limit: float = 1.0,
                 use_state_manager: bool = True):
        """
        Initialize the async scraper.
        """
        super().__init__(config)
        self.concurrency = concurrency
        self.rate_limit = rate_limit
        self.semaphore = asyncio.Semaphore(concurrency)
        self.config_loader = ConfigLoader()
        self.extractor = Extractor()
        
        # Initialize state manager if enabled
        self.state_manager = StateManager() if use_state_manager else None
        
        # Middleware is already initialized in BaseScraper
        # Configure delay based on rate_limit
        if hasattr(self, 'middleware_manager'):
            delay = 1.0 / rate_limit if rate_limit > 0 else 0
            self.middleware_manager.configure_delay(delay, delay * 1.5)
        
        self.logger.info(f"AsyncScraper initialized (concurrency={concurrency}, rate_limit={rate_limit})")
    
    async def scrape(self, url: str, selectors: Optional[Dict[str, Any]] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Scrape a single URL.
        
        Args:
            url: The URL to scrape
            selectors: Optional CSS selectors for data extraction
            
        Returns:
            Scraped data (Dict or List[Dict])
        """
        # Resolve configuration
        container = None
        if not selectors:
            selectors = self.config.get('selectors', {})
            container = self.config.get('container')
            
        if not selectors:
            # Try to load from ConfigLoader
            loaded_config = self.config_loader.get_config_for_url(url)
            if loaded_config:
                selectors = loaded_config.get('selectors', {})
                container = loaded_config.get('container')
                self.logger.info(f"Loaded config for {url}: {len(selectors)} selectors")
        
        async with self.semaphore:
            # Check if already visited
            if self.state_manager and self.state_manager.is_visited(url):
                self.logger.debug(f"Skipping already visited URL: {url}")
                return {'url': url, 'status': 'skipped', 'reason': 'already_visited'}
            
            try:
                # Fetch the page
                html = await self._fetch_page(url)
                
                # Extract data
                data = self.extractor.extract(html, {'selectors': selectors, 'container': container})
                
                # Handle list of items vs single item
                if isinstance(data, list):
                    for item in data:
                        item['url'] = url
                        item['status'] = 'success'
                        # We don't save individual items to state manager here to avoid spamming it,
                        # but we could if needed. For now, we rely on the URL being visited.
                    
                    # Add results to pipeline
                    for item in data:
                        self.add_result(item)
                else:
                    data['url'] = url
                    data['status'] = 'success'
                    self.add_result(data)
                
                # Mark as visited
                if self.state_manager:
                    self.state_manager.mark_visited(url, status='success')
                    # If it's a single item, save it. If it's a list, we might save a summary or nothing.
                    # Current state manager expects a dict "data"
                    save_data = data if isinstance(data, dict) else {'item_count': len(data), 'type': 'list'}
                    self.state_manager.save_item(url, save_data)
                
                return data
                
            except Exception as e:
                self.logger.error(f"Error scraping {url}: {e}")
                
                # Mark as visited with error status
                if self.state_manager:
                    self.state_manager.mark_visited(url, status='failed')
                
                return {'url': url, 'status': 'failed', 'error': str(e)}
    
    async def _fetch_page(self, url: str) -> str:
        """
        Fetch a page using httpx.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content
        """
        # Prepare request
        request = {'url': url, 'headers': {}}
        
        # Process through middleware
        if hasattr(self, 'middleware_manager'):
            request = self.middleware_manager.process_request(request)
        
        # Make the request
        proxies = None
        proxy = request.get('proxy')
        if proxy:
            proxies = {'http://': proxy, 'https://': proxy}
            
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, proxies=proxies) as client:
            headers = request.get('headers', {})
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            return response.text
    
    # _extract_data method removed in favor of Extractor class
    
    async def scrape_multiple(self, urls: List[str], selectors: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs concurrently.
        
        Args:
            urls: List of URLs to scrape
            selectors: Optional CSS selectors for data extraction
            
        Returns:
            List of scraped data
        """
        # Start a session if using state manager
        if self.state_manager and urls:
            self.state_manager.start_session(urls[0], metadata={
                'total_urls': len(urls),
                'concurrency': self.concurrency
            })
        
        try:
            # Create tasks for all URLs
            tasks = [self.scrape(url, selectors) for url in urls]
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and return results
            valid_results = []
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error(f"Task failed with exception: {result}")
                else:
                    valid_results.append(result)
            
            return valid_results
            
        finally:
            # End the session
            if self.state_manager:
                self.state_manager.end_session()
    
    async def scrape_with_pagination(self, start_url: str, 
                                     selectors: Optional[Dict[str, Any]] = None,
                                     pagination_config: Optional[Dict[str, Any]] = None,
                                     max_pages: int = 50) -> List[Dict[str, Any]]:
        """
        Scrape multiple pages following pagination.
        
        Args:
            start_url: The starting URL
            selectors: CSS selectors for data extraction
            pagination_config: Configuration for pagination (e.g., next button selector)
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of all scraped data
        """
        selectors = selectors or self.config.get('selectors', {})
        pagination_config = pagination_config or self.config.get('pagination', {})
        
        if not pagination_config and max_pages <= 1:
            # No pagination config and no implicit pagination requested
            result = await self.scrape(start_url, selectors)
            return [result] if result.get('status') == 'success' else []
        
        all_results = []
        current_url = start_url
        page_num = 1
        
        # Start a session
        if self.state_manager:
            self.state_manager.start_session(start_url, metadata={
                'max_pages': max_pages,
                'pagination': True
            })
        
        try:
            while page_num <= max_pages:
                self.logger.info(f"Scraping page {page_num}: {current_url}")
                
                # Scrape current page
                result = await self.scrape(current_url, selectors)
                
                if result.get('status') == 'success':
                    all_results.append(result)
                else:
                    self.logger.warning(f"Failed to scrape page {page_num}")
                    break
                
                # Find next page URL
                next_url = await self._find_next_page(current_url, pagination_config)
                
                if not next_url:
                    self.logger.info("No more pages found")
                    break
                
                current_url = next_url
                page_num += 1
            
            return all_results
            
        finally:
            if self.state_manager:
                self.state_manager.end_session()
    
    async def _find_next_page(self, current_url: str, pagination_config: Dict[str, Any]) -> Optional[str]:
        """
        Find the next page URL based on pagination configuration.
        
        Args:
            current_url: Current page URL
            pagination_config: Pagination configuration
            
        Returns:
            Next page URL or None if not found
        """
        pagination_type = pagination_config.get('type', 'next_button')
        
        if pagination_type == 'next_button':
            # Fetch the page to find the next button
            try:
                html = await self._fetch_page(current_url)
                soup = BeautifulSoup(html, 'lxml')
                
                next_element = None
                
                # 1. Try Configured Selector
                next_selector = pagination_config.get('selector')
                if next_selector:
                    next_element = soup.select_one(next_selector)
                
                # 2. Fallback: Search for "Next" text links/buttons
                if not next_element:
                    # Look for <a> or <button>
                    for tag in ['a', 'button']:
                        # Find all elements of this tag
                        elements = soup.find_all(tag)
                        for el in elements:
                            text = el.get_text(strip=True).lower()
                            # Check against common "Next" patterns
                            if any(p in text for p in ['next', 'more', 'older', '>', '»']):
                                # Avoid "Previous" or "Back" mistakingly matching ">" if logic was weird, but here we specific strings.
                                # Check if it's NOT "Previous"
                                if 'prev' in text or 'back' in text or 'newer' in text:
                                    continue
                                
                                # If it's a button, it might have an onclick or form, but we need an href usually for AsyncScraper
                                # AsyncScraper can't click buttons, only follow links. So meaningful only for <a>.
                                if tag == 'a' and el.get('href'):
                                    self.logger.info(f"Found next page by text '{text}': {el.get('href')}")
                                    next_element = el
                                    break
                                # If it's a button, we can't do much in AsyncScraper unless it wraps an A or has a value? 
                                # Ignoring valid buttons for AsyncScraper is technical limitation.
                        if next_element:
                            break
                            
                if next_element:
                    next_href = next_element.get('href')
                    if next_href:
                        # Handle relative URLs
                        from urllib.parse import urljoin
                        return urljoin(current_url, next_href)
            except Exception as e:
                self.logger.error(f"Error finding next page: {e}")
        
        elif pagination_type == 'url_pattern':
            # Increment page number in URL
            # This is a simple implementation, can be enhanced
            import re
            pattern = pagination_config.get('pattern', r'page=(\d+)')
            match = re.search(pattern, current_url)
            
            if match:
                current_page = int(match.group(1))
                next_page = current_page + 1
                return re.sub(pattern, f'page={next_page}', current_url)
        
        return None


async def scrape_urls_async(urls: List[str], 
                            selectors: Optional[Dict[str, Any]] = None,
                            concurrency: int = 5,
                            rate_limit: float = 1.0) -> List[Dict[str, Any]]:
    """
    Convenience function to scrape multiple URLs asynchronously.
    
    Args:
        urls: List of URLs to scrape
        selectors: CSS selectors for data extraction
        concurrency: Maximum concurrent requests
        rate_limit: Requests per second
        
    Returns:
        List of scraped data
    """
    scraper = AsyncScraper(concurrency=concurrency, rate_limit=rate_limit)
    return await scraper.scrape_multiple(urls, selectors)
