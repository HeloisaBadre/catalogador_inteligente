import sqlite3
from typing import List, Dict, Any, Optional
import os

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def get_connection(self):
        """Get a read-only connection to the database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total files and size
        cursor.execute("SELECT COUNT(*) as total_files, SUM(size_bytes) as total_size FROM files")
        row = cursor.fetchone()
        
        # Extension distribution
        cursor.execute("""
            SELECT extension, COUNT(*) as count, SUM(size_bytes) as total_size
            FROM files
            GROUP BY extension
            ORDER BY total_size DESC
            LIMIT 10
        """)
        extensions = [dict(row) for row in cursor.fetchall()]
        
        # Top 10 largest files
        cursor.execute("""
            SELECT path, filename, size_bytes
            FROM files
            ORDER BY size_bytes DESC
            LIMIT 10
        """)
        largest_files = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total_files": row["total_files"],
            "total_size": row["total_size"] or 0,
            "extensions": extensions,
            "largest_files": largest_files
        }
    
    def search_files(self, query: str = "", extension: Optional[str] = None, 
                     min_size: Optional[int] = None, max_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search files with filters."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM files WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (filename LIKE ? OR path LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        
        if extension:
            sql += " AND extension = ?"
            params.append(extension)  # type: ignore
        
        if min_size is not None:
            sql += " AND size_bytes >= ?"
            params.append(min_size)  # type: ignore
        
        if max_size is not None:
            sql += " AND size_bytes <= ?"
            params.append(max_size)  # type: ignore
        
        sql += " LIMIT 100"
        
        cursor.execute(sql, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_duplicates(self) -> List[Dict[str, Any]]:
        """Find duplicate files by MD5 hash."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT md5_hash, COUNT(*) as count, SUM(size_bytes) as wasted_space, 
                   GROUP_CONCAT(path, '|||') as paths
            FROM files
            GROUP BY md5_hash
            HAVING count > 1
            ORDER BY wasted_space DESC
        """)
        
        duplicates = []
        for row in cursor.fetchall():
            duplicates.append({
                "md5_hash": row["md5_hash"],
                "count": row["count"],
                "wasted_space": row["wasted_space"],
                "paths": row["paths"].split("|||") if row["paths"] else []
            })
        
        conn.close()
        return duplicates
    
    def get_largest_files(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get largest files sorted by size."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT path, filename, extension, size_bytes, modified_at
            FROM files
            ORDER BY size_bytes DESC
            LIMIT ?
        """, (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_oldest_files(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get oldest files sorted by modification date."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT path, filename, extension, size_bytes, modified_at, created_at
            FROM files
            ORDER BY modified_at ASC
            LIMIT ?
        """, (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
