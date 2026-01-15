import logging
import random
import asyncio
from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Page, BrowserContext
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import os
from scraper.config_loader import ConfigLoader
from scraper.extractor import Extractor

logger = logging.getLogger(__name__)

class UniversalScraper:
    """
    A universal web scraper using Playwright that handles both static and dynamic content.
    Includes smart fallback extraction and stealth mechanisms.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.ua = UserAgent()
        self._playwright = None
        self._browser = None
        self.config_loader = ConfigLoader()
        self.extractor = Extractor()
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def scrape(self, url: str, config: Optional[Dict[str, Any]] = None, screenshot: bool = False) -> Dict[str, Any]:
        """
        Scrape a URL with pagination support and anti-bot handling.
        """
        # 1. Resolve Configuration
        # If manual config is passed, use it. Otherwise, look up in selectors.json
        if not config:
            config = self.config_loader.get_config_for_url(url) or {}
            if config:
                logger.info("Using domain-specific configuration.")
            
        logger.info(f"Scraping URL: {url}")
        all_results = []
        all_results = []
        max_pages = 50 # Default to 50 pages for better coverage
        if config.get('pagination') and config['pagination'].get('max_pages'):
             max_pages = config['pagination']['max_pages']

        async with async_playwright() as p:
            # Launch browser with stealth settings
            browser = await p.chromium.launch(headless=self.headless)
            context = await self._create_stealth_context(browser)
            page = await context.new_page()
            
            try:
                # Apply stealth (Try library first, then manual)
                try:
                    from playwright_stealth import stealth_async
                    await stealth_async(page)
                except ImportError:
                    # Fallback to manual stealth script
                    await context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                    """)
                
                # Navigate
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                page_num = 1
                while page_num <= max_pages:
                    logger.info(f"Processing page {page_num}...")
                    
                    # Anti-Bot / CAPTCHA Detection
                    await self._detect_captcha(page)
                    
                    # Random delay
                    await asyncio.sleep(random.uniform(2, 5))
                    
                    # Extract Data
                    page_data = await self._extract_data(page, config)
                    
                    # Flatten items into main list
                    if page_data.get('items'):
                        all_results.extend(page_data['items'])
                    else:
                        # Append single page result if not a list
                        all_results.append(page_data)


                    # Check Max Items
                    if config.get('max_items') and len(all_results) >= config['max_items']:
                        logger.info(f"Reached max items limit ({config['max_items']}). Stopping.")
                        all_results = all_results[:config['max_items']]
                        break

                    # Handle Pagination
                    pagination = config.get('pagination', {})
                    should_paginate = bool(pagination.get('selector')) or max_pages > 1

                    if should_paginate:
                         next_button = None
                         
                         # 1. Try Configured Selector
                         if pagination.get('selector'):
                             next_selector = pagination['selector']
                             try:
                                 next_button = await page.query_selector(next_selector)
                             except Exception as e:
                                 logger.warning(f"Error extracting next selector: {e}")
                         
                         # 2. Fallback: Robust Text/XPath Search
                         if not next_button:
                             # Keywords to search for
                             keywords = ["next", "more", "older", ">", "»"]
                             
                             for tag in ['a', 'button']:
                                 if next_button: break
                                 for kw in keywords:
                                     # Case-insensitive XPath for containing text
                                     xpath = f"//{tag}[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw}')]"
                                     try:
                                         elements = await page.query_selector_all(xpath)
                                         for el in elements:
                                             if not await el.is_visible():
                                                 continue
                                             
                                             txt = await el.text_content()
                                             txt = txt.lower().strip() if txt else ""
                                             
                                             if kw in txt:
                                                  if any(bad in txt for bad in ['prev', 'back', 'newer', '<']):
                                                      continue
                                                  
                                                  logger.info(f"Found next page button by text '{txt}' (tag: {tag})")
                                                  next_button = el
                                                  break
                                     except Exception as e:
                                         logger.debug(f"Error checking xpath {xpath}: {e}")
                                         continue
                                     if next_button: break

                         if next_button:
                             logger.info("Next page button found. Clicking...")
                             await next_button.click()
                             try:
                                 await page.wait_for_load_state("networkidle", timeout=10000)
                             except:
                                 pass # Timeout is okay, we proceed
                             page_num += 1
                         else:
                             logger.info("No next page button found. Stopping.")
                             break
                    else:
                        break # No pagination configured or needed

                return {'items': all_results, 'total_pages': page_num}
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                raise e
            finally:
                await context.close()
                await browser.close()

    async def _detect_captcha(self, page: Page):
        """Detect and handle CAPTCHAs manually."""
        captcha_selectors = [
            'iframe[src*="recaptcha"]', 
            'iframe[src*="captcha"]',
            '#captcha', 
            '.g-recaptcha'
        ]
        
        for selector in captcha_selectors:
            if await page.query_selector(selector):
                logger.warning("🚨 CAPTCHA DETECTED! Pausing for manual solving...")
                print("\n" + "!"*50)
                print("CAPTCHA DETECTED. Please solve it in the browser window.")
                print("Press ENTER in this terminal once solved to continue...")
                print("!"*50 + "\n")
                
                # If headless is True, we can't solve it. Warn user.
                if self.headless:
                     logger.error("Cannot solve CAPTCHA in headless mode! Run with --headful.")
                     return

                # Wait for user input
                await asyncio.get_event_loop().run_in_executor(None, input)
                logger.info("Resuming...")
                break

    async def _create_stealth_context(self, browser) -> BrowserContext:
        """Create a browser context with stealth properties."""
        user_agent = self.ua.random
        
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            permissions=['geolocation']
        )
        return context

    async def _extract_data(self, page: Page, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data using the unified Extractor.
        """
        try:
            html = await page.content()
            data = self.extractor.extract(html, config)
            
            # Handle List vs Dict return
            results = {}
            if isinstance(data, list):
                results = {'items': data}
            else:
                results = data
                
            # Optional: Raw HTML if requested
            if config.get('save_html'):
                results['raw_html'] = html
                
            return results
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return {'error': str(e)}

    async def scrape_multiple(self, urls: List[str], config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Scrape multiple URLs concurrently."""
        tasks = [self.scrape(url, config) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)
