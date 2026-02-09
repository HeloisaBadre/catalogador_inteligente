mod db;
mod models;
mod scanner;

use anyhow::Result;
use db::Database;
use scanner::Scanner;
use serde::Serialize;
use std::env;
use std::fs::File;
use std::path::Path;
use std::sync::mpsc;
use std::thread;
use std::time::Instant;

#[derive(Serialize)]
struct ScanProgress {
    scanned: usize,
    total: Option<usize>, // Estimate, optional
    current_file: String,
    status: String, // "running", "completed"
}

fn write_status(path: &Path, progress: &ScanProgress) {
    if let Ok(file) = File::create(path) {
        let _ = serde_json::to_writer(file, progress);
    }
}

fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("Usage: {} <scan_path> <db_path>", args[0]);
        std::process::exit(1);
    }

    let scan_path = args[1].clone();
    let db_path = args[2].clone();
    let status_path = Path::new(&db_path)
        .parent()
        .unwrap()
        .join("scan_status.json");

    println!("Starting scan of: {}", scan_path);
    println!("Database: {}", db_path);
    println!("Status file: {:?}", status_path);

    let start_time = Instant::now();

    // Initialize DB
    let mut db = Database::new(&db_path)?;
    db.init()?;

    // Create Channel
    let (tx, rx): (
        mpsc::Sender<crate::models::FileEntry>,
        mpsc::Receiver<crate::models::FileEntry>,
    ) = mpsc::channel();

    // Spawn DB Writer Thread
    let status_path_clone = status_path.clone();
    let db_handle = thread::spawn(move || -> Result<usize> {
        let mut batch = Vec::with_capacity(1000);
        let mut total_inserted = 0;
        let mut last_file = String::new();

        for entry in rx {
            last_file = entry.path.clone();
            batch.push(entry);

            if batch.len() >= 50 { // Commit smaller batches for smoother progress? Keep 1000 for perf, update status more often?
                 // Actually, let's keep DB batch at 1000 but update status every 50
            }

            // Update status every 10 files for smoother UI
            if (total_inserted + batch.len()) % 10 == 0 {
                let progress = ScanProgress {
                    scanned: total_inserted + batch.len(),
                    total: None,
                    current_file: last_file.clone(),
                    status: "running".to_string(),
                };
                write_status(&status_path_clone, &progress);
            }

            if batch.len() >= 1000 {
                db.insert_files(&batch)?;
                total_inserted += batch.len();
                batch.clear();
                println!("Indexed: {} files", total_inserted);
            }
        }

        // Insert remaining
        if !batch.is_empty() {
            db.insert_files(&batch)?;
            total_inserted += batch.len();
        }

        Ok(total_inserted)
    });

    let scanner = Scanner::new(&scan_path);
    scanner.scan(tx);

    let total = db_handle.join().unwrap()?;

    // Write final status
    let final_progress = ScanProgress {
        scanned: total,
        total: Some(total),
        current_file: String::new(),
        status: "completed".to_string(),
    };
    write_status(&status_path, &final_progress);

    let duration = start_time.elapsed();
    println!("Scan complete in {:.2?}", duration);
    println!("Total file indexed: {}", total);

    Ok(())
}
