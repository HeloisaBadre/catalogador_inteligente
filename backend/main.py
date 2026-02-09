from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import List
import os
from database import Database
from sha256_computer import compute_multiple
from export_service import ExportService
from ai_service import AIService
import json
import time
from datetime import datetime

app = FastAPI(title="Smart File Cataloger API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path - default to ../data/catalog.db
DB_PATH = os.environ.get("DB_PATH", "../data/catalog.db")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Smart Cataloger Backend"}

@app.get("/api/stats")
async def get_stats():
    """Get overall statistics."""
    db = Database(DB_PATH)
    return db.get_stats()

@app.get("/api/search")
async def search_files(
    query: str = Query("", description="Search term for filename or path"),
    extension: str = Query(None, description="Filter by extension"),
    min_size: int = Query(None, description="Minimum file size in bytes"),
    max_size: int = Query(None, description="Maximum file size in bytes")
):
    """Search files with filters."""
    db = Database(DB_PATH)
    return db.search_files(query, extension, min_size, max_size)

@app.get("/api/duplicates")
async def get_duplicates():
    """Get duplicate files."""
    db = Database(DB_PATH)
    return db.get_duplicates()

@app.get("/api/largest")
async def get_largest_files(limit: int = Query(100, description="Number of files to return")):
    """Get largest files sorted by size."""
    db = Database(DB_PATH)
    return db.get_largest_files(limit)

@app.get("/api/oldest")
async def get_oldest_files(limit: int = Query(100, description="Number of files to return")):
    """Get oldest files sorted by modification date."""
    db = Database(DB_PATH)
    return db.get_oldest_files(limit)

class VerifyRequest(BaseModel):
    md5_hash: str
    file_ids: List[int]
    file_paths: List[str]

@app.post("/api/duplicates/verify")
async def verify_duplicates(request: VerifyRequest):
    """Verify duplicates using SHA256 hash."""
    db = Database(DB_PATH)
    
    # Compute SHA256 for all files
    results = compute_multiple(request.file_paths)
    
    # Update database with SHA256 hashes
    for i, result in enumerate(results):
        if result["success"]:
            file_id = request.file_ids[i]
            db.update_sha256_hash(file_id, result["sha256"])
    
    # Group by SHA256 to find true duplicates
    sha256_groups = {}
    for i, result in enumerate(results):
        if result["success"]:
            sha256 = result["sha256"]
            if sha256 not in sha256_groups:
                sha256_groups[sha256] = []
            sha256_groups[sha256].append({
                "path": result["path"],
                "file_id": request.file_ids[i]
            })
    
    # Return verification results
    verified_groups = []
    for sha256, files in sha256_groups.items():
        verified_groups.append({
            "sha256_hash": sha256,
            "files": files,
            "is_duplicate": len(files) > 1,
            "count": len(files)
        })
    
    return {
        "md5_hash": request.md5_hash,
        "verified_groups": verified_groups,
        "total_files": len(results),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"])
    }

@app.get("/api/duplicates/candidates")
async def get_duplicate_candidates():
    """Get MD5 duplicate candidates for SHA256 verification."""
    db = Database(DB_PATH)
    return db.get_duplicate_candidates()

@app.get("/api/export/json")
async def export_json():
    """Export catalog data as JSON."""
    exporter = ExportService(DB_PATH)
    json_data = exporter.export_json()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=json_data,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=catalog_export_{timestamp}.json"
        }
    )

@app.get("/api/export/csv")
async def export_csv():
    """Export catalog data as CSV."""
    exporter = ExportService(DB_PATH)
    csv_data = exporter.export_csv()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=catalog_export_{timestamp}.csv"
        }
    )

@app.get("/api/export/html")
async def export_html():
    """Export catalog report as HTML."""
    exporter = ExportService(DB_PATH)
    html_data = exporter.export_html()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=html_data,
        media_type="text/html",
        headers={
            "Content-Disposition": f"attachment; filename=catalog_report_{timestamp}.html"
        }
    )

@app.get("/api/tree")
async def get_tree(
    path: str = Query("", description="Parent directory path"),
    depth: int = Query(1, description="Depth to load (always 1 for lazy loading)")
):
    """Get directory tree structure with lazy loading."""
    db = Database(DB_PATH)
    return db.get_tree_structure(path, depth)

@app.get("/api/suggestions")
async def get_suggestions():
    """Get smart heuristic suggestions for file cleanup."""
    service = AIService(DB_PATH)
    return service.get_suggestions()

@app.get("/api/scan_progress")
async def get_scan_progress():
    """Get real-time scan progress from the engine."""
    # Assuming DB_PATH is in data/catalog.db, status is in data/scan_status.json
    db_dir = os.path.dirname(DB_PATH)
    status_path = os.path.join(db_dir, "scan_status.json")
    
    if not os.path.exists(status_path):
        return {
            "scanned": 0,
            "total": None,
            "current_file": None,
            "status": "idle"
        }
        
    try:
        # Check for stale file (older than 30 seconds)
        mtime = os.path.getmtime(status_path)
        if time.time() - mtime > 30:
             return {
                "scanned": 0,
                "total": None,
                "current_file": None,
                "status": "idle" # Treat as idle if engine died
            }

        with open(status_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error reading status file: {e}")
        return {
            "scanned": 0,
            "total": None,
            "current_file": None,
            "status": "error"
        }

# Mount frontend static files
if os.path.exists("../frontend"):
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
