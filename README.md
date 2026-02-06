# Smart File Cataloger

Advanced file cataloging and analysis tool with AI-powered organization suggestions.

## 🚀 Quick Start

### 1. Scan a Directory

```bash
cd engine
.\target\release\engine.exe <path_to_scan> ..\data\catalog.db
```

Example:
```bash
.\target\release\engine.exe C:\Users\YourName\Documents ..\data\catalog.db
```

### 2. Start the API Server

```bash
cd backend
py -m uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### 3. Open the Web UI

Open your browser and navigate to:
```
http://localhost:8000
```

## 📁 Project Structure

```
smart_cataloger/
├── engine/          # Rust scanning engine (MD5 hashing, multithreaded)
├── backend/         # Python FastAPI server
├── frontend/        # Web UI (HTML/CSS/JS)
└── data/            # SQLite database storage
```

## 🔧 Features

- ✅ **High-Performance Scanning**: Multithreaded Rust engine
- ✅ **MD5 Hashing**: Fast duplicate detection
- ✅ **Advanced Search**: Filter by name, extension, size, date
- ✅ **Duplicate Detection**: Find and manage duplicate files
- ✅ **Analytics Dashboard**: Visual insights into your file system
- ✅ **Modern UI**: Dark-mode, responsive design

## 🛠️ Technical Stack

- **Engine**: Rust (walkdir, rayon, md-5, rusqlite)
- **Backend**: Python (FastAPI, SQLite)
- **Frontend**: Vanilla JS, Chart.js, CSS3
- **Database**: SQLite with WAL mode

## 📊 Database Schema

The SQLite database uses WAL (Write-Ahead Logging) mode for concurrent access and includes optimized indexes for fast queries.

## 🔒 Safety

- **No automatic deletion**: The system only provides suggestions
- **Read-only UI**: All file modifications require explicit user action
- **Graceful error handling**: Permission errors don't interrupt scans

## 📝 License

MIT
