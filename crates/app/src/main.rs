// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;

mod commands;

fn main() {
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
        .invoke_handler(tauri::generate_handler![])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
