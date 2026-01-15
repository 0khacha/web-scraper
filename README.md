# Universal Web Scraper


**Intelligent • High-Performance • Production-Ready**

A powerful web scraping tool with smart extraction, async performance, and multi-format export capabilities.

---

## 📋 Table of Contents
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Usage Examples](#-usage-examples)
- [Command Options](#-command-options)
- [Configuration](#-configuration)
- [Testing](#-testing)
- [Architecture](#-architecture)
- [Troubleshooting](#-troubleshooting)
- [Version History](#-version-history)

---

## Features

- **Smart Extraction**: Automatically detects content structure with intelligent fallback
- **Async Performance**: High-speed concurrent scraping with configurable concurrency
- **Multi-Format Export**: CSV, JSON, Excel, XML, SQLite support
- **State Management**: Resume interrupted scraping sessions
- **Middleware System**: Request/response processing pipeline
- **Pagination Support**: Automatic page traversal
- **Anti-Bot Handling**: Stealth mechanisms and user-agent rotation
- **Comprehensive Logging**: Debug extraction issues easily

---

## Quick Start

### Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Playwright browsers:**
   ```bash
   playwright install
   ```

### Basic Usage

```bash
# Simple scraping
python main.py "https://quotes.toscrape.com"

# With configuration
python main.py "https://quotes.toscrape.com" --config quotes_toscrape_com

# Async mode with concurrency
python main.py "https://example.com" --async --concurrency 5

# Export to specific formats
python main.py "https://example.com" --export-format csv,json,excel
```

---

## Usage Examples

### E-commerce Scraping
```bash
# Extract products from a test site
python main.py "http://books.toscrape.com" --config books_toscrape --verbose
```

### News & Blogs
```bash
# Extract quotes and authors
python main.py "https://quotes.toscrape.com" --config quotes_toscrape_com --export-format json
```

### Data Tables
```bash
# Extract global COVID statistics
python main.py "https://www.worldometers.info/coronavirus/" --config covid_worldometers --export-format csv
```

### Dynamic Content (JavaScript Sites)
```bash
# Scrape JavaScript-rendered content
python main.py "https://quotes.toscrape.com/js/" --headful --verbose
```

### Pagination
```bash
# Scrape multiple pages with async
python main.py "http://books.toscrape.com" --config books_toscrape --async --concurrency 3
```

---

## Command Options

### Required
| Option | Description |
|--------|-------------|
| `url` | Target URL to scrape |

### Scraper Options
| Option | Description |
|--------|-------------|
| `--config` | Configuration key from selectors.json |
| `--async` | Enable high-speed async scraping |

### Extraction Options
| Option | Description |
|--------|-------------|
| `--container` | CSS Selector for container |
| `--fields` | Fields mapping (e.g. title:h1,price:.price) |
| `--max-items` | Maximum number of items to scrape |
| `--max-pages` | Maximum number of pages to scrape |

### Performance Options
| Option | Description |
|--------|-------------|
| `--concurrency` | Number of parallel requests (default: 5) |
| `--rate-limit` | Requests per second (default: 1.0) |
| `--no-state` | Disable state management |

### Output Options
| Option | Description |
|--------|-------------|
| `--output-name` | Output filename (default: results) |
| `--export-format` | Export formats: csv,json,excel,xml,sqlite |

### Debug Options
| Option | Description |
|--------|-------------|
| `--headful` | Run browser in headful mode |
| `--screenshot` | Take screenshot of page |
| `--verbose` | Verbose logging |

---

## Configuration

### Using Selectors Config

Create or edit `config/selectors.json`:

```json
{
    "sites": [
        {
            "domain": "example.com",
            "name": "example",
            "container": ".product",
            "selectors": {
                "title": "h2.title",
                "price": ".price",
                "description": ".desc"
            },
            "pagination": {
                "type": "next_button",
                "selector": "a.next"
            }
        }
    ]
}
```

### CLI Override

```bash
python main.py "https://example.com" --container ".product" --fields "title:h2,price:.price"
```

---

## 🛠️ How to Find Selectors Easily

Don't guess CSS selectors! Use our built-in helper tool to generate them automatically.

### 1. Run the Selector Finder
```bash
python tools/find_selectors.py "https://example.com"
```

### 2. Follow Instructions
The tool will open two windows (Browser and Inspector). 
**Ignore** the big block of Python code (imports, `def run`, etc.).
Look inside the `run()` function for lines like:

```python
# Look for these lines!
page.get_by_text("Quotes to Scrape").click()
page.locator(".author").first.click()
```

### 3. Copy Selectors
Copy the selector part from those lines. Playwright often gives you "smart" chains.

- **Simple:** `page.locator(".author")` -> Copy `.author`
- **Smart:** `page.get_by_role("button", name="Login")` -> Copy `button >> text=Login` or use the specific smart selector syntax if your config supports it.

*Tip: Usually you just want the string inside the quotes if it's a CSS selector.*

### 💡 Tip for Lists
The code generator gives you a selector for the **single specific item** you clicked (e.g., "The world as we created...").
To scrape **all** items (e.g., all quotes):
1. Don't use the text-based selector.
2. Use the **Pick Locator** tool (cursor icon) in the inspector.
3. Look for a shared class name (e.g., `.quote` or `.product_pod`).
4. Use that class as your container selector.

Copy the generated code into your `config/selectors.json`.

### ⚡ Alternative: Automatic Extraction
Don't want to deal with selectors? You can skip the configuration entirely!

**Simply run:**
```bash
python main.py "https://example.com" --verbose
```
The scraper's **Smart Extraction** engine will automatically detect and extract content. Using `--verbose` is recommended to see exactly what data is being found.

---

## Testing

### Quick Tests

**Test 1: Container-based extraction**
```bash
python main.py "https://quotes.toscrape.com" --config quotes_toscrape_com --verbose
```
Expected: Multiple quotes with text, author, and tags

**Test 2: Static content**
```bash
python main.py "http://books.toscrape.com" --config books_toscrape --verbose
```
Expected: Multiple books with title, price, availability

**Test 3: Fallback mechanism**
```bash
python main.py "https://quotes.toscrape.com" --verbose
```
Expected: Falls back to smart extraction and extracts page content

**Test 4: WebScraper.io test site**
```bash
python main.py "https://webscraper.io/test-sites/e-commerce/allinone" --config webscraper_io --verbose
```
Expected: Product listings with name, price, description

### Debugging Tips

- Add `--verbose` to see detailed extraction logs
- Check logs for:
  - "Found X containers matching..."
  - "Successfully extracted X items using configured selectors"
  - "Falling back to smart extraction" (if selectors fail)
- Use `--headful` to see the browser in action
- Use `--screenshot` to capture page state

---

## Architecture

### Project Structure
```
web-scraper/
├── config/
│   ├── default_config.json
│   ├── selectors.json
│   └── selectors_example.json
├── scraper/
│   ├── universal_scraper.py  # Main scraper with smart extraction
│   ├── async_scraper.py      # High-performance async scraper
│   ├── config_loader.py      # Configuration management
│   ├── exporters.py          # Multi-format export
│   ├── middleware.py         # Request/response processing
│   ├── state_manager.py      # Resumable scraping
│   ├── pipelines.py          # Data processing
│   └── utils.py              # Utility functions
├── tests/                    # Comprehensive test suite
├── main.py                   # Main entry point
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

### Key Components

- **Middlewares**: User-Agent rotation, proxy management, request retries
- **Pipelines**: Data cleaning, deduplication, schema validation
- **State Manager**: Tracks processed URLs for resumable scraping
- **Exporters**: Multi-format output (CSV, JSON, Excel, XML, SQLite)

---

## Troubleshooting

### Browser doesn't open
Ensure Playwright browsers are installed:
```bash
playwright install
```

### No items extracted
1. Check selectors in config file
2. Use `--verbose` to see extraction logs
3. Try without config to test fallback extraction
4. Use `--headful` to visually inspect the page

### Import errors
Reinstall dependencies:
```bash
pip install -r requirements.txt --force-reinstall
```

### Slow performance
1. Use `--async` mode for faster scraping
2. Increase `--concurrency` (default: 5)
3. Adjust `--rate-limit` if needed

---

## Version History

### v1.0.0 (2026-01-12) - Production Release

**Status**: ✅ Production Ready

**Key Features**:
- ✅ Universal extraction engine with smart fallback
- ✅ Playwright-based dynamic content handling
- ✅ Async scraping with concurrency control
- ✅ Multiple export formats (CSV, JSON, Excel, XML, SQLite)
- ✅ State management for resumable scraping
- ✅ Middleware system for request/response processing
- ✅ Configurable selectors via JSON
- ✅ Pagination support
- ✅ Anti-bot detection handling
- ✅ Comprehensive logging

**Improvements**:
- ✅ Fixed extraction quality - proper fallback when selectors fail
- ✅ Enhanced logging for debugging extraction issues
- ✅ Comprehensive documentation
- ✅ Production-ready codebase

**Requirements**:
- Python 3.8+
- See `requirements.txt` for dependencies

---

## License & Support

**Current Version**: 1.0.0  
**Release Date**: 2026-01-12  
**Status**: Production Ready

For issues or questions, refer to the documentation sections above.

---

**Happy Scraping!**
