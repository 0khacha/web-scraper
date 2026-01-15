"""
State management for crawl persistence and deduplication.
Tracks visited URLs and allows resuming interrupted scrapes.
"""
import sqlite3
import logging
import hashlib
from pathlib import Path
from typing import Set, Optional, Dict, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages scraping state with SQLite persistence.
    Tracks visited URLs, sessions, and allows crawl resumption.
    """
    
    def __init__(self, db_path: str = "output/scraper_state.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session_id: Optional[str] = None
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for visited URLs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visited_urls (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                session_id TEXT,
                visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'success'
            )
        """)
        
        # Table for sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                start_url TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'active',
                metadata TEXT
            )
        """)
        
        # Table for scraped items (optional, for recovery)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraped_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                url TEXT,
                data TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_visited_urls_session 
            ON visited_urls(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scraped_items_session 
            ON scraped_items(session_id)
        """)
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"State database initialized at {self.db_path}")
    
    def _hash_url(self, url: str) -> str:
        """Generate a hash for a URL."""
        return hashlib.md5(url.encode('utf-8')).hexdigest()
    
    def start_session(self, start_url: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Start a new scraping session.
        
        Args:
            start_url: The starting URL for this session
            metadata: Optional metadata about the session
            
        Returns:
            Session ID
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.session_id = session_id
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute("""
            INSERT INTO sessions (session_id, start_url, metadata)
            VALUES (?, ?, ?)
        """, (session_id, start_url, metadata_json))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Started session: {session_id}")
        return session_id
    
    def end_session(self, session_id: Optional[str] = None):
        """Mark a session as completed."""
        session_id = session_id or self.session_id
        if not session_id:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sessions 
            SET completed_at = CURRENT_TIMESTAMP, status = 'completed'
            WHERE session_id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Ended session: {session_id}")
    
    def is_visited(self, url: str, session_id: Optional[str] = None) -> bool:
        """
        Check if a URL has been visited.
        
        Args:
            url: The URL to check
            session_id: Optional session ID to check within. If None, checks globally.
            
        Returns:
            True if URL has been visited, False otherwise
        """
        url_hash = self._hash_url(url)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if session_id:
            cursor.execute("""
                SELECT COUNT(*) FROM visited_urls 
                WHERE url_hash = ? AND session_id = ?
            """, (url_hash, session_id))
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM visited_urls 
                WHERE url_hash = ?
            """, (url_hash,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def mark_visited(self, url: str, session_id: Optional[str] = None, status: str = 'success'):
        """
        Mark a URL as visited.
        
        Args:
            url: The URL to mark as visited
            session_id: Optional session ID. Uses current session if None.
            status: Status of the visit (success, failed, etc.)
        """
        url_hash = self._hash_url(url)
        session_id = session_id or self.session_id
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO visited_urls (url_hash, url, session_id, status)
                VALUES (?, ?, ?, ?)
            """, (url_hash, url, session_id, status))
            
            conn.commit()
            self.logger.debug(f"Marked as visited: {url}")
        except sqlite3.IntegrityError:
            # URL already visited, update status
            cursor.execute("""
                UPDATE visited_urls 
                SET status = ?, visited_at = CURRENT_TIMESTAMP
                WHERE url_hash = ?
            """, (status, url_hash))
            conn.commit()
            self.logger.debug(f"Updated visit status: {url}")
        finally:
            conn.close()
    
    def save_item(self, url: str, data: Dict[str, Any], session_id: Optional[str] = None):
        """
        Save a scraped item to the database.
        
        Args:
            url: The URL the item was scraped from
            data: The scraped data
            session_id: Optional session ID. Uses current session if None.
        """
        session_id = session_id or self.session_id
        data_json = json.dumps(data, ensure_ascii=False)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scraped_items (session_id, url, data)
            VALUES (?, ?, ?)
        """, (session_id, url, data_json))
        
        conn.commit()
        conn.close()
        
        self.logger.debug(f"Saved item from: {url}")
    
    def get_session_items(self, session_id: Optional[str] = None) -> list:
        """
        Retrieve all items from a session.
        
        Args:
            session_id: Optional session ID. Uses current session if None.
            
        Returns:
            List of scraped items
        """
        session_id = session_id or self.session_id
        if not session_id:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT url, data FROM scraped_items 
            WHERE session_id = ?
            ORDER BY scraped_at
        """, (session_id,))
        
        items = []
        for row in cursor.fetchall():
            url, data_json = row
            data = json.loads(data_json)
            data['_source_url'] = url
            items.append(data)
        
        conn.close()
        
        return items
    
    def get_visited_count(self, session_id: Optional[str] = None) -> int:
        """
        Get the count of visited URLs.
        
        Args:
            session_id: Optional session ID. If None, counts all URLs.
            
        Returns:
            Count of visited URLs
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if session_id:
            cursor.execute("""
                SELECT COUNT(*) FROM visited_urls 
                WHERE session_id = ?
            """, (session_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM visited_urls")
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def clear_session(self, session_id: str):
        """
        Clear all data for a specific session.
        
        Args:
            session_id: The session ID to clear
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM visited_urls WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM scraped_items WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Cleared session: {session_id}")
    
    def clear_all(self):
        """Clear all state data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM visited_urls")
        cursor.execute("DELETE FROM scraped_items")
        cursor.execute("DELETE FROM sessions")
        
        conn.commit()
        conn.close()
        
        self.logger.info("Cleared all state data")
    
    def get_active_sessions(self) -> list:
        """Get all active (incomplete) sessions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, start_url, started_at, metadata
            FROM sessions 
            WHERE status = 'active'
            ORDER BY started_at DESC
        """)
        
        sessions = []
        for row in cursor.fetchall():
            session_id, start_url, started_at, metadata_json = row
            sessions.append({
                'session_id': session_id,
                'start_url': start_url,
                'started_at': started_at,
                'metadata': json.loads(metadata_json) if metadata_json else None
            })
        
        conn.close()
        
        return sessions
