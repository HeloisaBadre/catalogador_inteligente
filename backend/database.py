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
    
    def get_duplicate_candidates(self) -> List[Dict[str, Any]]:
        """Get files that share MD5 hash (candidates for SHA256 verification)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT md5_hash, COUNT(*) as count,
                   GROUP_CONCAT(path, '|||') as paths,
                   GROUP_CONCAT(id, ',') as ids,
                   MAX(sha256_verified) as any_verified
            FROM files
            GROUP BY md5_hash
            HAVING count > 1
            ORDER BY count DESC
        """)
        
        candidates = []
        for row in cursor.fetchall():
            candidates.append({
                "md5_hash": row["md5_hash"],
                "count": row["count"],
                "paths": row["paths"].split("|||") if row["paths"] else [],
                "ids": [int(x) for x in row["ids"].split(",")] if row["ids"] else [],
                "any_verified": bool(row["any_verified"])
            })
        
        conn.close()
        return candidates
    
    def update_sha256_hash(self, file_id: int, sha256_hash: str) -> None:
        """Update SHA256 hash for a specific file."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE files
            SET sha256_hash = ?, sha256_verified = 1
            WHERE id = ?
        """, (sha256_hash, file_id))
        
        conn.commit()
        conn.close()
    
    def get_verified_duplicates(self) -> List[Dict[str, Any]]:
        """Get verified duplicate groups based on SHA256."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT sha256_hash, COUNT(*) as count,
                   SUM(size_bytes) as wasted_space,
                   GROUP_CONCAT(path, '|||') as paths
            FROM files
            WHERE sha256_verified = 1 AND sha256_hash IS NOT NULL
            GROUP BY sha256_hash
            HAVING count > 1
            ORDER BY wasted_space DESC
        """)
        
        duplicates = []
        for row in cursor.fetchall():
            duplicates.append({
                "sha256_hash": row["sha256_hash"],
                "count": row["count"],
                "wasted_space": row["wasted_space"],
                "paths": row["paths"].split("|||") if row["paths"] else [],
                "verified": True
            })
        
        conn.close()
        return duplicates
    
    def get_tree_structure(self, path: str = "", depth: int = 1) -> Dict[str, Any]:
        """Get directory tree structure with lazy loading.
        
        Args:
            path: Parent directory path (empty for root detection)
            depth: Number of levels to load (always 1 for lazy loading)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Determine separator based on first file in DB (Windows uses \, Unix uses /)
        cursor.execute("SELECT path FROM files LIMIT 1")
        sample = cursor.fetchone()
        if not sample:
            conn.close()
            return {"path": path, "children": []}
        
        sep = "\\" if "\\" in sample["path"] else "/"
        
        if path == "":
            # Get root drives/directories
            if sep == "\\":
                # Windows: Get unique drive letters (format: "C:\", "D:\", etc.)
                cursor.execute("""
                    SELECT DISTINCT SUBSTR(path, 1, 3) as root_path
                    FROM files
                    WHERE LENGTH(path) > 2 AND SUBSTR(path, 2, 2) = ':\\'
                    ORDER BY root_path
                """)
            else:
                # Unix: Get top-level directories under /
                cursor.execute("""
                    SELECT DISTINCT 
                        '/' || SUBSTR(path, 2, INSTR(SUBSTR(path, 2), '/') - 1) as root_path
                    FROM files
                    WHERE path LIKE '/%'
                    LIMIT 20
                """)
            
            children = []
            for row in cursor.fetchall():
                root = row[0] if isinstance(row, tuple) else row["root_path"]
                if root:
                    children.append({
                        "name": root,
                        "path": root,
                        "type": "dir",
                        "has_children": True,
                        "size": 0
                    })
            
            conn.close()
            return {"path": "", "children": children}
        
        # Normalize path
        path = path.rstrip(sep)
        
        # Get immediate children using path prefix
        # This query finds all files in this directory or subdirectories
        like_pattern = path + sep + "%"
        
        cursor.execute("""
            SELECT path, filename, size_bytes
            FROM files
            WHERE path LIKE ?
        """, (like_pattern,))
        
        items = cursor.fetchall()
        
        # Parse immediate children
        files = []
        dir_map = {}
        
        for item in items:
            item_path = item["path"]
            
            # Extract relative path from parent
            relative = item_path[len(path) + len(sep):]
            
            if sep in relative:
                # Item is in a subdirectory
                dir_name = relative.split(sep)[0]
                dir_path = path + sep + dir_name
                
                if dir_path not in dir_map:
                    dir_map[dir_path] = {
                        "name": dir_name,
                        "path": dir_path,
                        "type": "dir",
                        "size": 0,
                        "has_children": True
                    }
                dir_map[dir_path]["size"] += item["size_bytes"]
            else:
                # Item is directly in this directory
                files.append({
                    "name": item["filename"],
                    "path": item_path,
                    "type": "file",
                    "size": item["size_bytes"],
                    "has_children": False
                })
        
        # Combine and sort: directories first, then files
        children = list(dir_map.values()) + files
        children.sort(key=lambda x: (x["type"] == "file", x["name"].lower()))
        
        conn.close()
        
        return {
            "path": path,
            "children": children
        }
