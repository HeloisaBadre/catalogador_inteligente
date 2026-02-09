use crate::models::FileEntry;
use rusqlite::{params, Connection, Result};

pub struct Database {
    conn: Connection,
}

impl Database {
    pub fn new(path: &str) -> Result<Self> {
        let conn = Connection::open(path)?;

        // Performance Pragmas
        conn.execute_batch(
            "PRAGMA journal_mode = WAL;
             PRAGMA synchronous = NORMAL;
             PRAGMA temp_store = MEMORY;
             PRAGMA cache_size = -64000;", // 64MB cache
        )?;

        Ok(Self { conn })
    }

    pub fn init(&self) -> Result<()> {
        self.conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                extension TEXT,
                size_bytes INTEGER NOT NULL,
                created_at INTEGER,
                modified_at INTEGER,
                md5_hash TEXT NOT NULL,
                sha256_hash TEXT,
                sha256_verified INTEGER DEFAULT 0
            );

            -- Indexes for Search Performance
            CREATE INDEX IF NOT EXISTS idx_path ON files(path);
            CREATE INDEX IF NOT EXISTS idx_filename ON files(filename);
            CREATE INDEX IF NOT EXISTS idx_extension ON files(extension);
            CREATE INDEX IF NOT EXISTS idx_size ON files(size_bytes);
            CREATE INDEX IF NOT EXISTS idx_md5 ON files(md5_hash);
            
            -- Composite Index for fast Duplicate Detection candidates
            CREATE INDEX IF NOT EXISTS idx_dupe_check ON files(size_bytes, md5_hash);
            ",
        )?;
        Ok(())
    }

    pub fn insert_files(&mut self, files: &[FileEntry]) -> Result<()> {
        let tx = self.conn.transaction()?;

        {
            let mut stmt = tx.prepare(
                "INSERT OR REPLACE INTO files 
                (path, filename, extension, size_bytes, created_at, modified_at, md5_hash, sha256_hash, sha256_verified)
                VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, 0)"
            )?;

            for file in files {
                stmt.execute(params![
                    file.path,
                    file.filename,
                    file.extension,
                    file.size_bytes,
                    file.created_at,
                    file.modified_at,
                    file.md5_hash,
                    file.sha256_hash
                ])?;
            }
        }

        tx.commit()?;
        Ok(())
    }
}
