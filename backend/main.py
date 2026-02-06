from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from database import Database

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

# Mount frontend static files
if os.path.exists("../frontend"):
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
