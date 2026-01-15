import logging
import json
from typing import Any, Dict, List, Optional
from jsonschema import validate, ValidationError

class ItemPipeline:
    """
    Handles post-processing of scraped items.
    Inspired by Scrapy's Item Pipeline.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def process_item(self, item: Dict[str, Any], scraper: Any) -> Optional[Dict[str, Any]]:
        """
        Process a single item. Return the item or None to drop it.
        """
        # Basic cleaning: strip whitespace from all string values
        for key, value in item.items():
            if isinstance(value, str):
                item[key] = value.strip()
        
        # Deduplication could be handled here if we had item finger-printing
        
        return item

class ValidationPipeline(ItemPipeline):
    """
    Validates items against a set of rules.
    """
    def process_item(self, item: Dict[str, Any], scraper: Any) -> Optional[Dict[str, Any]]:
        # Basic validation: ensure title exists
        if not item.get('title'):
            self.logger.warning(f"Dropping item missing title: {item}")
            return None
        return item

class SchemaValidationPipeline(ItemPipeline):
    """
    Validates items against a JSON schema if provided in config.
    """
    def process_item(self, item: Dict[str, Any], scraper: Any) -> Optional[Dict[str, Any]]:
        schema = scraper.config.get('schema')
        if not schema:
            return item
            
        try:
            validate(instance=item, schema=schema)
            return item
        except ValidationError as e:
            self.logger.warning(f"Schema validation failed for item: {e.message}")
            return None

class DeduplicationPipeline(ItemPipeline):
    """
    Prevents duplicate items within a single run.
    """
    def __init__(self):
        super().__init__()
        self.seen_ids = set()

    def process_item(self, item: Dict[str, Any], scraper: Any) -> Optional[Dict[str, Any]]:
        # Generate a unique fingerprint for the item
        # Use link if available, otherwise hash the content
        item_id = item.get('link') or item.get('url') or hash(frozenset(item.items()))
        
        if item_id in self.seen_ids:
            self.logger.debug(f"Dropping duplicate item: {item_id}")
            return None
            
        self.seen_ids.add(item_id)
        return item

class PipelineManager:
    """
    Manages a sequence of pipelines.
    """
    def __init__(self, pipelines: List[ItemPipeline] = None):
        self.pipelines = pipelines or [
            ItemPipeline(), 
            ValidationPipeline(),
            DeduplicationPipeline(),
            SchemaValidationPipeline()
        ]

    def process_item(self, item: Dict[str, Any], scraper: Any) -> Optional[Dict[str, Any]]:
        for pipeline in self.pipelines:
            item = pipeline.process_item(item, scraper)
            if item is None:
                break
        return item
