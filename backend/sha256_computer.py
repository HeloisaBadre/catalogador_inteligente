#!/usr/bin/env python3
"""
SHA256 Hash Computer
Computes SHA256 hash for given file paths.
Used by the backend API for on-demand verification.
"""

import hashlib
import sys
from pathlib import Path
from typing import List, Dict, Any


def compute_sha256(file_path: str) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    
    try:
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for byte_block in iter(lambda: f.read(8192), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        raise Exception(f"Error hashing {file_path}: {e}")


def compute_multiple(file_paths: List[str]) -> List[Dict[str, Any]]:
    """Compute SHA256 for multiple files."""
    results = []
    
    for path in file_paths:
        try:
            hash_value = compute_sha256(path)
            results.append({
                "path": path,
                "sha256": hash_value,
                "success": True,
                "error": None
            })
        except Exception as e:
            results.append({
                "path": path,
                "sha256": None,
                "success": False,
                "error": str(e)
            })
    
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sha256_computer.py <file1> [file2] ...")
        sys.exit(1)
    
    file_paths = sys.argv[1:]
    results = compute_multiple(file_paths)
    
    for result in results:
        if result["success"]:
            print(f"{result['sha256']}  {result['path']}")
        else:
            print(f"ERROR: {result['path']} - {result['error']}", file=sys.stderr)
