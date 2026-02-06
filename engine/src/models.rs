use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FileEntry {
    pub path: String,
    pub filename: String,
    pub extension: Option<String>,
    pub size_bytes: u64,
    pub created_at: i64,  // Unix timestamp
    pub modified_at: i64, // Unix timestamp
    pub md5_hash: String,
    pub sha256_hash: Option<String>,
}

impl FileEntry {
    pub fn new(path: PathBuf, size: u64, created: i64, modified: i64, md5: String) -> Self {
        let filename = path
            .file_name()
            .unwrap_or_default()
            .to_string_lossy()
            .to_string();
        let extension = path.extension().map(|e| e.to_string_lossy().to_string());

        Self {
            path: path.to_string_lossy().to_string(),
            filename,
            extension,
            size_bytes: size,
            created_at: created,
            modified_at: modified,
            md5_hash: md5,
            sha256_hash: None,
        }
    }
}
