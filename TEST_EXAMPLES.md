# 🧪 Web Scraper - Test Examples

Quick reference guide with ready-to-run test commands for the Universal Web Scraper.

---

## 📋 Quick Tests

### 1. Quotes Website (Simple Static Content)
```bash
python main.py "https://quotes.toscrape.com" --config quotes_toscrape_com --verbose
```
**Expected Output**: 10 quotes with text, author, and tags  
**Export Formats**: CSV, JSON, Excel (default)

### 2. Books E-commerce (Pagination)
```bash
python main.py "http://books.toscrape.com" --config books_toscrape --max-items 20 --verbose
```
**Expected Output**: 20 books with title, price, and availability  
**Features Tested**: Pagination, product extraction

### 3. COVID Statistics (Data Tables)
```bash
python main.py "https://www.worldometers.info/coronavirus/" --config covid_worldometers --max-items 10 --export-format csv
```
**Expected Output**: Country statistics with cases, deaths, recoveries  
**Features Tested**: Table extraction, multiple fields

### 4. WebScraper.io Test Site
```bash
python main.py "https://webscraper.io/test-sites/e-commerce/allinone" --config webscraper_io --verbose
```
**Expected Output**: Product listings with name, price, description  
**Features Tested**: E-commerce scraping, reviews

---

## ⚡ Async & Performance Tests

### 5. Async Scraping with Concurrency
```bash
python main.py "http://books.toscrape.com" --config books_toscrape --async --concurrency 5 --max-items 30
```
**Features Tested**: High-speed async scraping, concurrent requests

### 6. Rate Limited Scraping
```bash
python main.py "https://quotes.toscrape.com" --config quotes_toscrape_com --rate-limit 0.5 --verbose
```
**Features Tested**: Rate limiting (2 requests per second)

---

## 🧠 Smart Extraction Tests

### 7. Fallback Extraction (No Config)
```bash
python main.py "https://quotes.toscrape.com" --verbose
```
**Expected Output**: Smart extraction detects quotes automatically  
**Features Tested**: Intelligent fallback when no config provided

### 8. Custom Selectors via CLI
```bash
python main.py "http://books.toscrape.com" --container "article.product_pod" --fields "title:h3 a,price:.price_color" --max-items 10
```
**Features Tested**: CLI selector override, custom field mapping

---

## 🎯 Export Format Tests

### 9. Multiple Export Formats
```bash
python main.py "https://quotes.toscrape.com" --config quotes_toscrape_com --export-format csv,json,excel --output-name quotes_export
```
**Output Files**: 
- `output/quotes_export.csv`
- `output/quotes_export.json`
- `output/quotes_export.xlsx`

### 10. JSON Only Export
```bash
python main.py "http://books.toscrape.com" --config books_toscrape --export-format json --max-items 15
```
**Output**: Clean JSON file with structured data

---

## 🔍 Debug & Inspection Tests

### 11. Headful Mode (See Browser)
```bash
python main.py "https://quotes.toscrape.com/js/" --config quotes_toscrape_com --headful --verbose
```
**Features Tested**: Visual browser inspection, JavaScript rendering

### 12. Screenshot Capture
```bash
python main.py "https://quotes.toscrape.com" --config quotes_toscrape_com --screenshot --verbose
```
**Output**: Screenshot saved for debugging

---

## 🌐 Real-World Examples

### 13. Goodreads Book Lists
```bash
python main.py "https://www.goodreads.com/list/show/1.Best_Books_Ever" --config goodreads_list --max-items 20 --verbose
```
**Expected Output**: Book titles, authors, ratings, votes

### 14. Amazon Products (Advanced)
```bash
python main.py "https://www.amazon.com/s?k=laptop" --config amazon_products --headful --max-items 10 --verbose
```
**Features Tested**: Anti-bot handling, dynamic content, complex selectors

---

## 📊 Batch Processing

### 15. Multiple Pages with State Management
```bash
python main.py "http://books.toscrape.com" --config books_toscrape --async --concurrency 3 --verbose
```
**Features Tested**: State management, resume capability, pagination

---

## 🛠️ Troubleshooting Tests

### 16. Verbose Logging
```bash
python main.py "https://quotes.toscrape.com" --config quotes_toscrape_com --verbose
```
**Use When**: Debugging extraction issues, checking selector matches

### 17. No State Management
```bash
python main.py "http://books.toscrape.com" --config books_toscrape --no-state --max-items 10
```
**Use When**: Fresh scraping without resume capability

---

## 📝 Expected Results

After running any test, check the `output/` directory:

```bash
# View results
Get-Content output/results.csv
Get-Content output/results.json
```

### Success Indicators:
- ✅ "Successfully extracted X items" in console
- ✅ Files created in `output/` directory
- ✅ No error messages in logs
- ✅ Data matches expected structure

### Common Issues:
- ❌ "0 items found" → Check selectors or use `--verbose`
- ❌ "Browser timeout" → Use `--headful` to inspect
- ❌ "Import error" → Run `pip install -r requirements.txt`

---

## 🚀 Quick Start Workflow

1. **Start Simple**:
   ```bash
   python main.py "https://quotes.toscrape.com" --config quotes_toscrape_com --verbose
   ```

2. **Check Output**:
   ```bash
   Get-Content output/results.csv
   ```

3. **Try Async**:
   ```bash
   python main.py "http://books.toscrape.com" --config books_toscrape --async --concurrency 5
   ```

4. **Custom Site**:
   - Add config to `config/selectors.json`
   - Test with `--verbose` flag
   - Adjust selectors as needed

---

## 💡 Pro Tips

- **Always start with `--verbose`** to see what's happening
- **Use `--headful`** when debugging new sites
- **Start with small `--max-items`** values for testing
- **Check `config/selectors_example.json`** for selector patterns
- **Use `--screenshot`** to capture page state for debugging

---

**Happy Testing! 🎉**
