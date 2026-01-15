import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Loads and matches domain-specific configurations."""
    
    def __init__(self, config_path: str = "config/selectors.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load the JSON configuration file."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found at {self.config_path}")
            return {"sites": []}
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {"sites": []}

    def get_config_for_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Finds the configuration for a given URL by matching the domain.
        Returns None if no match is found.
        """
        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # 1. Check "sites" list (Legacy/Strict support)
            if "sites" in self.config and isinstance(self.config["sites"], list):
                for site in self.config["sites"]:
                    site_domain = site.get("domain", "").lower()
                    if site_domain and site_domain in domain:
                        logger.info(f"Found configuration for domain: {site_domain}")
                        return site
            
            # 2. Check Dictionary Keys (Current format)
            # Iterate through all keys in the config
            for key, options in self.config.items():
                if not isinstance(options, dict):
                    continue
                    
                # A. Check explicit 'domain' field in value
                if "domain" in options:
                    if options["domain"].lower() in domain:
                        logger.info(f"Found configuration for domain (by field): {options['domain']}")
                        return options
                
                # B. Match Key against Domain (Heuristic)
                # Normalize key: replace underscore with dot
                normalized_key = key.replace('_', '.')
                if normalized_key in domain:
                     logger.info(f"Found configuration for domain (by key): {key}")
                     return options
                     
                # C. Check if key is a substring of domain (e.g. 'amazon' in 'amazon.com')
                # Use stricter length check to avoid false positives (e.g. 'co' in 'costco')
                if len(key) > 3 and key in domain:
                     logger.info(f"Found configuration for domain (substring match): {key}")
                     return options

            return None
            
        except Exception as e:
            logger.error(f"Error matching config for URL {url}: {e}")
            return None

    def get_config_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Finds configuration by name (key in the JSON).
        """
        try:
            # 1. Direct Key Match (Priority)
            if name in self.config:
                return self.config[name]
                
            # 2. Search in "sites" list (Legacy)
            if "sites" in self.config and isinstance(self.config["sites"], list):
                for site in self.config["sites"]:
                    if site.get("name") == name:
                        return site
            
            return None
        except Exception as e:
            logger.error(f"Error finding config by name {name}: {e}")
            return None
