import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from scraper.pipelines import PipelineManager

# Make middleware optional
try:
    from scraper.middleware import MiddlewareManager
    MIDDLEWARE_AVAILABLE = True
except ImportError:
    MIDDLEWARE_AVAILABLE = False
    logging.warning("Middleware not available. Install middleware.py for advanced features.")

class BaseScraper(ABC):
    def __init__(self, config=None):
        self.config = config or {}
        self.results = []
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize managers
        self.pipeline_manager = PipelineManager()
        
        # Only initialize middleware if available
        if MIDDLEWARE_AVAILABLE:
            self.middleware_manager = MiddlewareManager()
        else:
            self.middleware_manager = None

    @abstractmethod
    def scrape(self, url, selectors):
        """Scrape the given URL using the provided selectors."""
        pass

    def add_result(self, item: Dict[str, Any]):
        """
        Process a single scraped item through pipelines and add to results.
        Inspired by Scrapy's processing flow.
        """
        processed_item = self.pipeline_manager.process_item(item, self)
        if processed_item is not None:
            self.results.append(processed_item)
        else:
            self.logger.debug(f"Item dropped by pipeline: {item}")

    def get_results(self):
        """Return the collected results."""
        return self.results
