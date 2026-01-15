import logging
import re
import os
from datetime import datetime
from typing import Optional

def setup_logging(level=logging.INFO, log_file="scraper.log"):
    """Configure logging for the application (Console + File)."""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File Handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def clean_text(text):
    """Clean whitespace and normalize text."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def normalize_price(price_str):
    """Extract numeric value from price string."""
    if not price_str:
        return None
    clean_str = re.sub(r'[^\d.]', '', price_str.replace(',', ''))
    try:
        return float(clean_str)
    except ValueError:
        return None

def normalize_rating(rating_str):
    """Convert star ratings to numerical values."""
    if not rating_str:
        return None
    score = 0.0
    s = str(rating_str)
    score += s.count('★')
    if '½' in s:
        score += 0.5
    if score == 0:
        match = re.search(r'(\d+(\.\d+)?)', s)
        if match: score = float(match.group(1))
    return score if score > 0 else None

def validate_url(url: str) -> bool:
    """Validate if string is a valid URL."""
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def format_number(num: int) -> str:
    """Format number with thousands separator."""
    return f"{num:,}"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.replace(' ', '_')
    return filename[:200]

