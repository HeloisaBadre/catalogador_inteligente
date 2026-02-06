use crate::models::FileEntry;
use anyhow::Result;
use md5::{Digest, Md5};
use rayon::prelude::*;
use std::fs::File;
use std::io::{BufReader, Read};
use std::path::Path;
use std::sync::mpsc::Sender;
use walkdir::WalkDir;

pub struct Scanner {
    root: String,
}

impl Scanner {
    pub fn new(root: &str) -> Self {
        Self {
            root: root.to_string(),
        }
    }

    pub fn scan(&self, tx: Sender<FileEntry>) {
        WalkDir::new(&self.root)
            .into_iter()
            .par_bridge() // Parallelize the iterator
            .filter_map(|e| e.ok())
            .filter(|e| e.file_type().is_file())
            .for_each_with(tx, |tx, entry| {
                let path = entry.path();

                // Skip if we can't read metadata
                let metadata = match path.metadata() {
                    Ok(m) => m,
                    Err(_) => return,
                };

                let size = metadata.len();
                // Basic Unix timestamps (or 0 if unavailable)
                let created = metadata
                    .created()
                    .unwrap_or(std::time::SystemTime::UNIX_EPOCH)
                    .duration_since(std::time::SystemTime::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs() as i64;

                let modified = metadata
                    .modified()
                    .unwrap_or(std::time::SystemTime::UNIX_EPOCH)
                    .duration_since(std::time::SystemTime::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs() as i64;

                // Calculate MD5
                if let Ok(hash) = compute_md5(path) {
                    let entry = FileEntry::new(path.to_path_buf(), size, created, modified, hash);

                    // Send to DB thread (ignore errors if receiver dropped)
                    let _ = tx.send(entry);
                }
            });
    }
}

fn compute_md5(path: &Path) -> Result<String> {
    let file = File::open(path)?;
    let mut reader = BufReader::new(file);
    let mut hasher = Md5::new();

    // Read in chunks to avoid loading large files entirely into RAM
    let mut buffer = [0; 8192];
    loop {
        let count = reader.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        hasher.update(&buffer[..count]);
    }

    let result = hasher.finalize();
    Ok(format!("{:x}", result))
}
