"""
Advanced data exporters supporting multiple formats
"""
import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


class BaseExporter:
    """Base class for all exporters."""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def export(self, data: List[Dict], filename: str) -> str:
        """Export data. Returns path to exported file."""
        raise NotImplementedError


class CSVExporter(BaseExporter):
    """Export to CSV format."""
    
    def export(self, data: List[Dict], filename: str = "results") -> str:
        if not data:
            self.logger.warning("No data to export to CSV")
            return None
        
        df = pd.DataFrame(data)
        df = df.drop_duplicates()
        
        filepath = self.output_dir / f"{filename}.csv"
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        self.logger.info(f"Exported {len(df)} rows to {filepath}")
        return str(filepath)


class ExcelExporter(BaseExporter):
    """Export to Excel format with formatting."""
    
    def export(self, data: List[Dict], filename: str = "results") -> str:
        if not data:
            self.logger.warning("No data to export to Excel")
            return None
        
        df = pd.DataFrame(data)
        df = df.drop_duplicates()
        
        filepath = self.output_dir / f"{filename}.xlsx"
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Data']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(str(col))
                    )
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
            
            self.logger.info(f"Exported {len(df)} rows to {filepath}")
            return str(filepath)
        except Exception as e:
            self.logger.error(f"Failed to export to Excel: {e}")
            return None


class JSONExporter(BaseExporter):
    """Export to JSON format."""
    
    def export(self, data: List[Dict], filename: str = "results") -> str:
        if not data:
            self.logger.warning("No data to export to JSON")
            return None
        
        filepath = self.output_dir / f"{filename}.json"
        
        # Remove duplicates while preserving order
        seen = set()
        unique_data = []
        for item in data:
            item_str = json.dumps(item, sort_keys=True)
            if item_str not in seen:
                seen.add(item_str)
                unique_data.append(item)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(unique_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Exported {len(unique_data)} items to {filepath}")
        return str(filepath)


class JSONLinesExporter(BaseExporter):
    """Export to JSON Lines format (one JSON object per line)."""
    
    def export(self, data: List[Dict], filename: str = "results") -> str:
        if not data:
            self.logger.warning("No data to export to JSONL")
            return None
        
        filepath = self.output_dir / f"{filename}.jsonl"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        self.logger.info(f"Exported {len(data)} items to {filepath}")
        return str(filepath)


class XMLExporter(BaseExporter):
    """Export to XML format."""
    
    def export(self, data: List[Dict], filename: str = "results") -> str:
        if not data:
            self.logger.warning("No data to export to XML")
            return None
        
        filepath = self.output_dir / f"{filename}.xml"
        
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<items>']
        
        for item in data:
            xml_lines.append('  <item>')
            for key, value in item.items():
                # Sanitize key for XML
                safe_key = key.replace(' ', '_').replace('-', '_')
                safe_value = str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                xml_lines.append(f'    <{safe_key}>{safe_value}</{safe_key}>')
            xml_lines.append('  </item>')
        
        xml_lines.append('</items>')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(xml_lines))
        
        self.logger.info(f"Exported {len(data)} items to {filepath}")
        return str(filepath)


class SQLiteExporter(BaseExporter):
    """Export to SQLite database."""
    
    def export(self, data: List[Dict], filename: str = "results") -> str:
        if not data:
            self.logger.warning("No data to export to SQLite")
            return None
        
        filepath = self.output_dir / f"{filename}.db"
        
        try:
            df = pd.DataFrame(data)
            df = df.drop_duplicates()
            
            conn = sqlite3.connect(filepath)
            df.to_sql('scraped_data', conn, if_exists='replace', index=False)
            conn.close()
            
            self.logger.info(f"Exported {len(df)} rows to {filepath}")
            return str(filepath)
        except Exception as e:
            self.logger.error(f"Failed to export to SQLite: {e}")
            return None


class ExportManager:
    """Manages multiple export formats."""
    
    EXPORTERS = {
        'csv': CSVExporter,
        'excel': ExcelExporter,
        'xlsx': ExcelExporter,  # Alias
        'json': JSONExporter,
        'jsonl': JSONLinesExporter,
        'xml': XMLExporter,
        'sqlite': SQLiteExporter,
    }
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def export(self, data: List[Dict], formats: List[str] = None, filename: str = "results") -> Dict[str, str]:
        """
        Export data to multiple formats.
        
        Args:
            data: List of dictionaries to export
            formats: List of format names (csv, excel, json, etc.)
            filename: Base filename without extension
            
        Returns:
            Dictionary mapping format to filepath
        """
        if formats is None:
            formats = ['csv', 'excel']  # Default formats
        
        results = {}
        
        for fmt in formats:
            fmt_key = fmt.lower().strip()
            if fmt_key not in self.EXPORTERS:
                self.logger.warning(f"Unknown export format: {fmt}")
                continue
            
            try:
                exporter = self.EXPORTERS[fmt](self.output_dir)
                filepath = exporter.export(data, filename)
                if filepath:
                    results[fmt] = filepath
            except Exception as e:
                self.logger.error(f"Failed to export to {fmt}: {e}")
        
        return results
    
    @classmethod
    def get_available_formats(cls) -> List[str]:
        """Get list of available export formats."""
        return list(cls.EXPORTERS.keys())
