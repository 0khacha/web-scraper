import sys
import argparse
import asyncio
import logging
import json
from pathlib import Path
from scraper.universal_scraper import UniversalScraper
from scraper.async_scraper import AsyncScraper
from scraper.utils import setup_logging, validate_url
from scraper.exporters import ExportManager

logger = logging.getLogger(__name__)

def print_banner():
    banner = """
+----------------------------------------------------------+
|      Universal Web Scraper - Professional Edition        |
|               Powered by Playwright                      |
+----------------------------------------------------------+
"""
    try:
        print(banner)
    except:
        pass

async def run_scraper(args):
    """Run the scraper based on configuration."""
    
    # Determine config
    config = {}
    config_loader = None
    
    # Try to load named config if specified
    if args.config:
        from scraper.config_loader import ConfigLoader
        config_loader = ConfigLoader()
        loaded_config = config_loader.get_config_by_name(args.config)
        if loaded_config:
            print(f"Loaded named configuration: {args.config}")
            # Merge loaded config into config dict
            config.update(loaded_config)
        else:
            print(f"Configuration '{args.config}' not found. Falling back to auto-detection.")
            
    # CLI overrides
    if args.container:
        config['container'] = args.container
    if args.fields:
        fields_dict = dict(item.split(":") for item in args.fields.split(","))
        config['fields'] = fields_dict
    if args.max_items:
        config['max_items'] = args.max_items
    if args.max_pages:
        if 'pagination' not in config:
            config['pagination'] = {}
        config['pagination']['max_pages'] = args.max_pages
        
    print(f"Starting scraper for: {args.url}")
    
    # Choose Scraper Implementation
    if args.enable_async:
        print(f"Mode: Async (Concurrency: {args.concurrency})")
        scraper = AsyncScraper(
            config=config,
            concurrency=args.concurrency,
            rate_limit=args.rate_limit,
            use_state_manager=not args.no_state
        )
        
        # Determine if pagination is needed/configured
        pagination_config = config.get('pagination')
        # Check if max_pages passed via CLI, else use config or default
        max_pages = args.max_pages if args.max_pages else (pagination_config.get('max_pages', 50) if pagination_config else 50)
        
        if pagination_config:
            if args.max_items:
                pass
            
            print(f"Pagination detected (Type: {pagination_config.get('type')}, Max Pages: {max_pages})")
            result = await scraper.scrape_with_pagination(args.url, max_pages=max_pages)
        else:
            # If no pagination config but max_pages is set explicitly high, we might want to try auto-pagination?
            # For now, just stick to config-based.
            result = await scraper.scrape(args.url)
        
        if isinstance(result, list):
            results_list = [r for r in result if r.get('status') == 'success']
            failed_count = len([r for r in result if r.get('status') == 'failed'])
            skipped_count = len([r for r in result if r.get('status') == 'skipped'])
        else:
            if result.get('status') == 'success':
                results_list = [result]
                failed_count = 0
                skipped_count = 0
            else:
                results_list = []
                failed_count = 1 if result.get('status') == 'failed' else 0
                skipped_count = 1 if result.get('status') == 'skipped' else 0
                
        if failed_count > 0:
            print(f"{failed_count} items failed")
        if skipped_count > 0:
            print(f"{skipped_count} items skipped (already visited)")
            
    else:
        print("Mode: Universal (Playwright)")
        scraper = UniversalScraper(headless=not args.headful)
        result = await scraper.scrape(args.url, config, screenshot=args.screenshot)
        
        if 'items' in result:
            results_list = result['items']
        else:
            results_list = [result]
            
    try:
        print(f"Successfully scraped {len(results_list)} items")
        
        # Export
        if results_list:
            export_manager = ExportManager()
            formats = [fmt.strip() for fmt in args.export_format.split(',')]
            files = export_manager.export(results_list, formats, args.output_name)
            
            print("\nExported files:")
            for fmt, path in files.items():
                print(f"   - {fmt.upper()}: {path}")
        else:
            print("No structure detected. Check screenshots/logs.")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

def main(args):
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    setup_logging(level=logging.INFO if not args.verbose else logging.DEBUG)
    print_banner()
    
    if not validate_url(args.url):
        print(f"ERROR: Invalid URL: {args.url}")
        return
        
    asyncio.run(run_scraper(args))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal Web Scraper")
    
    # Scraper Options
    parser.add_argument("url", help="Target URL")
    parser.add_argument("--config", help="Configuration key from selectors.json")
    parser.add_argument("--async", dest="enable_async", action="store_true", help="Enable high-speed async scraping")
    
    # Extraction Options
    extraction_group = parser.add_argument_group('Extraction')
    extraction_group.add_argument("--container", help="CSS Selector for container")
    extraction_group.add_argument("--fields", help="Fields mapping (e.g. title:h1,price:.price)")
    extraction_group.add_argument("--max-items", type=int, help="Maximum number of items to scrape")
    extraction_group.add_argument("--max-pages", type=int, help="Maximum number of pages to scrape (default: 50)")
    
    # Performance Options
    perf_group = parser.add_argument_group('Performance')
    perf_group.add_argument("--concurrency", type=int, default=5, help="Number of parallel requests (Async mode)")
    perf_group.add_argument("--rate-limit", type=float, default=1.0, help="Requests per second")
    perf_group.add_argument("--no-state", action="store_true", help="Disable state management")
    
    # Output Options
    output_group = parser.add_argument_group('Output')
    output_group.add_argument("--output-name", default="results", help="Output filename")
    output_group.add_argument("--export-format", default="csv,json", help="Export formats (csv,json,excel,xml,sqlite)")
    
    # Debug Options
    debug_group = parser.add_argument_group('Debug')
    debug_group.add_argument("--headful", action="store_true", help="Run browser in headful mode (Playwright)")
    debug_group.add_argument("--screenshot", action="store_true", help="Take screenshot of page")
    debug_group.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    try:
        main(args)
    except KeyboardInterrupt:
        print("\nInterrupted")

