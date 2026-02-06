mod db;
mod models;
mod scanner;

use anyhow::Result;
use db::Database;
use scanner::Scanner;
use std::env;
use std::sync::mpsc;
use std::thread;
use std::time::Instant;

fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("Usage: {} <scan_path> <db_path>", args[0]);
        std::process::exit(1);
    }

    let scan_path = &args[1];
    let db_path = &args[2];

    println!("Starting scan of: {}", scan_path);
    println!("Database: {}", db_path);

    let start_time = Instant::now();

    // Initialize DB
    let mut db = Database::new(db_path)?;
    db.init()?;

    // Create Channel
    let (tx, rx) = mpsc::channel();

    // Spawn DB Writer Thread
    let db_handle = thread::spawn(move || -> Result<usize> {
        let mut batch = Vec::with_capacity(1000);
        let mut total_inserted = 0;

        for entry in rx {
            batch.push(entry);
            if batch.len() >= 1000 {
                db.insert_files(&batch)?;
                total_inserted += batch.len();
                batch.clear();

                // Simple progress report to stdout
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

    // Start Scan (Blocking in main thread? No, scanner spawns threads but 'scan' method blocks?
    // Wait, scanner.scan uses par_bridge but for_each_with blocks the caller until done.
    // So we can run scanner in main thread or spawn another.)
    // Scanner runs recursively and uses Rayon. The call to `scan` blocks until directory walk is filtering.
    // Actually WalkDir is serial, par_bridge makes processing parallel.
    // So `scanner.scan` WILL block until all files are walked.
    let scanner = Scanner::new(scan_path);
    scanner.scan(tx); // This drops tx when done

    // Wait for DB thread
    let total = db_handle.join().unwrap()?;

    let duration = start_time.elapsed();
    println!("Scan complete in {:.2?}", duration);
    println!("Total file indexed: {}", total);

    Ok(())
}
