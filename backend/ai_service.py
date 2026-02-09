"""
AI Service (Heuristics Engine)
Provides smart suggestions for file organization and cleanup without LLM dependency.
"""

import os
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from database import Database

@dataclass
class Suggestion:
    path: str
    type: str  # 'file' | 'folder'
    reason: str
    action: str  # 'delete' | 'archive' | 'ignore'
    size_bytes: int
    confidence: float = 1.0  # 1.0 for exact rules, <1.0 for heuristics

class AIService:
    def __init__(self, db_path: str):
        self.db = Database(db_path)
    
    def get_suggestions(self) -> List[Dict[str, Any]]:
        """Run all heuristic rules and return suggestions."""
        suggestions = []
        
        # 1. Temporary Files Rule
        suggestions.extend(self._find_temp_files())
        
        # 2. Old Log/Backup Files Rule
        suggestions.extend(self._find_old_logs())
        
        # 3. Development Build Folders Rule
        suggestions.extend(self._find_dev_folders())
        
        # 4. Cache Directories Rule
        suggestions.extend(self._find_cache_folders())
        
        return [asdict(s) for s in suggestions]

    def _find_temp_files(self) -> List[Suggestion]:
        """Find temporary files (.tmp, .temp, .chk)."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT path, size_bytes
            FROM files
            WHERE extension IN ('tmp', 'temp', 'chk')
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append(Suggestion(
                path=row['path'],
                type='file',
                reason='Arquivo temporário detectado',
                action='delete',
                size_bytes=row['size_bytes']
            ))
        
        conn.close()
        return results

    def _find_old_logs(self) -> List[Suggestion]:
        """Find old log and backup files (> 30 days)."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        thirty_days_ago = time.time() - (30 * 24 * 60 * 60)
        
        cursor.execute("""
            SELECT path, size_bytes
            FROM files
            WHERE extension IN ('log', 'bak', 'old', 'dmp')
            AND modified_at < ?
        """, (thirty_days_ago,))
        
        results = []
        for row in cursor.fetchall():
            results.append(Suggestion(
                path=row['path'],
                type='file',
                reason='Arquivo de log/backup antigo (> 30 dias)',
                action='archive',
                size_bytes=row['size_bytes']
            ))
        
        conn.close()
        return results

    def _find_dev_folders(self) -> List[Suggestion]:
        """Find node_modules, venv, target, dist folders."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        target_folders = ['node_modules', 'venv', '.venv', 'target', 'dist', 'build']
        results = []
        
        for folder in target_folders:
            like_pattern_win = f'%\\{folder}\\%'
            like_pattern_unix = f'%/{folder}/%'
            
            cursor.execute("""
                SELECT path, size_bytes
                FROM files
                WHERE path LIKE ? OR path LIKE ?
            """, (like_pattern_win, like_pattern_unix))
            
            rows = cursor.fetchall()
            folder_groups = {}
            
            for row in rows:
                path = row['path']
                size = row['size_bytes']
                
                start_idx = -1
                if f"\\{folder}\\" in path:
                    start_idx = path.find(f"\\{folder}\\")
                elif f"/{folder}/" in path:
                    start_idx = path.find(f"/{folder}/")
                
                if start_idx != -1:
                    # Include the folder name in root path
                    # e.g., C:\Project\node_modules
                    root = path[:start_idx + len(folder) + 1]
                    if root not in folder_groups:
                        folder_groups[root] = 0
                    folder_groups[root] += size
            
            for root, total_size in folder_groups.items():
                results.append(Suggestion(
                    path=root,
                    type='folder',
                    reason=f'Pasta de dependências/build ({folder})',
                    action='ignore',
                    size_bytes=total_size
                ))
        
        conn.close()
        return results

    def _find_cache_folders(self) -> List[Suggestion]:
        """Find cache folders (__pycache__, .cache)."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cache_folders = ['__pycache__', '.cache', '.pytest_cache', '.mypy_cache']
        results = []
        
        for folder in cache_folders:
            like_pattern_win = f'%\\{folder}\\%'
            like_pattern_unix = f'%/{folder}/%'
            
            cursor.execute("""
                SELECT path, size_bytes
                FROM files
                WHERE path LIKE ? OR path LIKE ?
            """, (like_pattern_win, like_pattern_unix))
            
            rows = cursor.fetchall()
            folder_groups = {}
            
            for row in rows:
                path = row['path']
                size = row['size_bytes']
                
                start_idx = -1
                if f"\\{folder}\\" in path:
                    start_idx = path.find(f"\\{folder}\\")
                elif f"/{folder}/" in path:
                    start_idx = path.find(f"/{folder}/")
                
                if start_idx != -1:
                    root = path[:start_idx + len(folder) + 1]
                    if root not in folder_groups:
                        folder_groups[root] = 0
                    folder_groups[root] += size
            
            for root, total_size in folder_groups.items():
                results.append(Suggestion(
                    path=root,
                    type='folder',
                    reason=f'Pasta de cache ({folder})',
                    action='delete',
                    size_bytes=total_size
                ))
        
        conn.close()
        return results
