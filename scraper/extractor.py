import logging
import re
from typing import Dict, Any, Optional, List, Union
from bs4 import BeautifulSoup, Tag
import trafilatura

logger = logging.getLogger(__name__)

class Extractor:
    """
    Unified extraction logic for web scraping.
    Implements a 3-layer strategy:
    1. Configured Selectors (Exact match)
    2. Automatic List Detection (Heuristic)
    3. Smart Content Extraction (Fallback)
    """

    def __init__(self):
        pass

    def extract(self, html: str, config: Optional[Dict[str, Any]] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Extract data from HTML content.
        
        Args:
            html: HTML content as string
            config: Configuration dictionary (optional)
            
        Returns:
            Extracted data (Dict or List[Dict])
        """
        if not html:
            return {}
            
        config = config or {}
        soup = BeautifulSoup(html, 'lxml')
        
        # Layer 1: Configured Selectors
        selectors = config.get('selectors') or config.get('fields')
        if selectors:
            logger.debug("Attempting extraction with configured selectors...")
            container = config.get('container')
            result = self._extract_with_selectors(soup, selectors, container)
            
            # If we got results, valid results, return them
            if result:
                if isinstance(result, list) and len(result) > 0:
                    logger.info(f"✅ Extracted {len(result)} items using configured selectors")
                    return result
                elif isinstance(result, dict) and any(result.values()):
                    logger.info("✅ Extracted data using configured selectors")
                    return result
                else:
                    logger.info("Configured selectors yielded no data. Trying heuristics...")
        
        # Layer 2: Automatic List Detection
        # Only try if we didn't find specific data or if explicit config is missing
        # We assume if the user provided selectors and unique data was found, they want that.
        # But if they provided selectors and NOTHING was found, we fall back.
        logger.info("Attempting automatic list detection...")
        auto_list_result = self._detect_and_extract_list(soup)
        if auto_list_result:
            logger.info(f"✅ Automatically detected list with {len(auto_list_result)} items")
            return auto_list_result

        # Layer 3: Smart Content Extraction (Fallback)
        logger.info("Falling back to smart content extraction...")
        return self._extract_smart_content(html, soup)

    def _extract_with_selectors(self, soup: BeautifulSoup, selectors: Dict[str, str], container: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Extract using explicit CSS selectors."""
        
        # List extraction
        if container:
            items = []
            containers = soup.select(container)
            logger.debug(f"Found {len(containers)} containers matching '{container}'")
            
            for element in containers:
                item_data = self._extract_fields(element, selectors)
                if any(item_data.values()):
                    items.append(item_data)
            
            return items
            
        # Single item extraction
        return self._extract_fields(soup, selectors)

    def _extract_fields(self, element: Union[BeautifulSoup, Tag], selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract fields from a single element/soup."""
        data = {}
        for field_name, selector in selectors.items():
            try:
                # Support nested selectors/attributes? For now simple text/attr
                target = element.select_one(selector)
                if target:
                    # Special handling for common fields
                    lower_field = field_name.lower()
                    if lower_field in ['link', 'url', 'href']:
                        data[field_name] = target.get('href', target.get_text(strip=True))
                    elif lower_field in ['image', 'img', 'src', 'thumbnail']:
                        data[field_name] = target.get('src', target.get('data-src', target.get_text(strip=True)))
                    elif lower_field in ['price', 'cost']:
                        # Try to find a price-like element or just text
                        data[field_name] = target.get_text(strip=True)
                    else:
                        data[field_name] = target.get_text(strip=True)
            except Exception as e:
                # logger.debug(f"Error extracting field {field_name}: {e}")
                pass
        return data

    def _detect_and_extract_list(self, soup: BeautifulSoup) -> Optional[List[Dict[str, Any]]]:
        """
        Heuristic algorithm to detect repeating elements that look like a list.
        strategies:
        1. Find elements that appear many times with same class.
        2. Check if they contain common "card" features (image, link, title, price).
        """
        
        # 1. Identify potential item containers
        # We look for elements with classes that appear frequently
        class_counts = {}
        
        # Scan common container tags
        for tag_name in ['div', 'article', 'li', 'tr']:
            for element in soup.find_all(tag_name):
                classes = element.get('class')
                if classes:
                    # Create a signature from classes
                    sig = ".".join(sorted(classes))
                    if sig not in class_counts:
                        class_counts[sig] = []
                    class_counts[sig].append(element)

        # Filter for candidates that have > 2 items
        candidates = [elements for sig, elements in class_counts.items() if len(elements) >= 3]
        
        # Sort by quantity (prefer more items? or median?)
        # Let's try to score them based on content density
        best_items = []
        max_score = 0
        
        for elements in candidates:
            # Score this candidate set
            score = 0
            extracted_set = []
            
            # Check a sample of elements (first 5)
            sample_size = min(len(elements), 5)
            valid_items = 0
            
            for el in elements[:sample_size]:
                item_data = self._heuristically_extract_item(el)
                if len(item_data) >= 2: # At least 2 meaningful fields
                    valid_items += 1
            
            # If the sample looks good, extract all
            if valid_items / sample_size > 0.6: # > 60% valid
                for el in elements:
                    item_data = self._heuristically_extract_item(el)
                    if any(item_data.values()):
                        extracted_set.append(item_data)
                
                # Calculate score: (num_items * avg_fields)
                if extracted_set:
                    avg_fields = sum(len(d) for d in extracted_set) / len(extracted_set)
                    score = len(extracted_set) * avg_fields * (1.5 if avg_fields >= 3 else 1.0)
            
            if score > max_score:
                max_score = score
                best_items = extracted_set

        return best_items if best_items else None

    def _heuristically_extract_item(self, element: Tag) -> Dict[str, Any]:
        """Try to extract common fields from a potential item element."""
        data = {}
        
        # 1. Image
        img = element.find('img')
        if img:
            src = img.get('src') or img.get('data-src')
            if src and len(src) > 10: # filtering generic icons
                data['image'] = src
        
        # 2. Link
        a_tag = element.find('a')
        if a_tag:
            href = a_tag.get('href')
            if href:
                data['link'] = href
            # Often the title is inside the main link
            link_text = a_tag.get_text(strip=True)
            if link_text and len(link_text) > 3:
                data['title'] = link_text
                
        # 3. Title (if not found in link or needs better finding)
        # Look for headings
        if 'title' not in data:
            for h in ['h1', 'h2', 'h3', 'h4', 'h5', 'strong']:
                h_tag = element.find(h)
                if h_tag:
                    text = h_tag.get_text(strip=True)
                    if text:
                        data['title'] = text
                        break
        
        # 4. Price (look for currency symbols)
        text_content = element.get_text(" ", strip=True)
        # Simple regex for price
        price_match = re.search(r'[\$€£0-9]+[.,]\d{2}', text_content)
        if price_match:
            data['price'] = price_match.group(0)
            
        return data

    def _extract_smart_content(self, html: str, soup: BeautifulSoup) -> Dict[str, Any]:
        """Fallback to extracting main content and metadata."""
        results = {}
        
        # Metadata
        if soup.title:
            results['title'] = soup.title.get_text(strip=True)
            
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or \
                    soup.find('meta', attrs={'property': 'og:description'})
        if meta_desc:
            results['description'] = meta_desc.get('content', '').strip()
            
        # Main Content via Trafilatura
        try:
            main_content = trafilatura.extract(html)
            if main_content:
                results['content'] = main_content
            else:
                # Fallback to body text
                results['content'] = soup.body.get_text('\n', strip=True)[:5000] # Limit size
        except Exception as e:
            logger.warning(f"Trafilatura extraction failed: {e}")
            if soup.body:
                results['content'] = soup.body.get_text('\n', strip=True)[:5000]
                
        results['extraction_type'] = 'smart_fallback'
        return results
