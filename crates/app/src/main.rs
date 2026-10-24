// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;

mod commands;
mod quicklook_spike;
mod thumbnail_cache;

fn run_smoke_test(fixture_dir: &std::path::Path) -> i32 {
    use dedupe_core::{grouper, scanner};
    eprintln!("smoke-test: scanning {}", fixture_dir.display());
    let files = match scanner::scan_directory(fixture_dir, Some(2), |_| {}) {
        Ok(f) => f,
        Err(e) => { eprintln!("smoke-test: scan error: {e}"); return 1; }
    };
    let groups = grouper::build_groups(&files);
    let dup_count = groups.len();
    eprintln!("smoke-test: found {dup_count} duplicate group(s)");
    if dup_count > 0 { 0 } else { 1 }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.get(1).map(|s| s.as_str()) == Some("--smoke-test") {
        let fixture_dir = args.get(2)
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| std::path::PathBuf::from("tests/fixtures/images"));
        std::process::exit(run_smoke_test(&fixture_dir));
    }

    let log_dir = dirs::data_local_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("Arcitae/logs");

    let _log_guard = dedupe_app::logging::init(&log_dir);
    tracing::info!("Arcitae Dedupe starting");

    let db_path = dirs::data_local_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("Arcitae/dedupe.db");

    let conn = match dedupe_app::startup::init_database(&db_path) {
        Ok(c) => c,
        Err(e) => {
            tracing::error!("startup failed: {e}");
            std::process::exit(1);
        }
    };

    let alerts = dedupe_app::startup::reconcile_on_startup(&conn);
    if !alerts.is_empty() {
        tracing::warn!("reconcile alerts: {:?}", alerts);
    }

    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(Mutex::new(conn))
        .manage(commands::thumbnail::ThumbnailThrottle::new())
        .invoke_handler(tauri::generate_handler![
            commands::preview::preview_file,
            commands::scan::pick_folder,
            commands::scan::scan_folders,
            commands::cache::load_cached,
            commands::cache::import_python_cache,
            commands::cache::save_folders,
            commands::cache::load_folders,
            commands::quarantine::quarantine_files,
            commands::quarantine::restore_files,
            commands::quarantine::list_quarantine,
            commands::quarantine::delete_permanently,
            commands::thumbnail::get_thumbnail,
            commands::thumbnail::prefetch_thumbnails,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
