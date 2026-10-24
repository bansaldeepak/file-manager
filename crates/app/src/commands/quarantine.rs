use std::path::{Path, PathBuf};
use std::sync::Mutex;
use serde::{Deserialize, Serialize};
use tauri::AppHandle;
use tauri::Manager;
use dedupe_core::{hash::sha256_file, quarantine as core_q};
use dedupe_index::{op_journal, Connection};
use crate::thumbnail_cache;

// ── types ─────────────────────────────────────────────────────────────────────

#[derive(Serialize, Clone)]
pub struct MovedEntry {
    pub original: String,
    pub quarantine_path: String,
    pub journal_id: i64,
    pub bytes: u64,
}

#[derive(Serialize)]
pub struct FileError {
    pub path: String,
    pub message: String,
}

#[derive(Serialize)]
pub struct QuarantineResult {
    pub moved: Vec<MovedEntry>,
    pub errors: Vec<FileError>,
    pub total_bytes: u64,
}

#[derive(Deserialize)]
pub struct RestoreEntry {
    pub original: String,
    pub quarantine_path: String,
    pub journal_id: i64,
}

#[derive(Serialize)]
pub struct RestoreResult {
    pub restored: Vec<String>,
    pub errors: Vec<FileError>,
}

// ── helpers ───────────────────────────────────────────────────────────────────

fn quarantine_root() -> PathBuf {
    dirs::data_local_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("Arcitae/Quarantine")
}

/// Mirror the absolute source path under the quarantine root, then apply
/// collision_safe so two files with the same name never clobber each other.
fn quarantine_dest(source: &Path, root: &Path) -> PathBuf {
    let rel = source.strip_prefix("/").unwrap_or(source);
    core_q::collision_safe(&root.join(rel))
}

// ── commands ──────────────────────────────────────────────────────────────────

#[tauri::command]
pub async fn quarantine_files(
    paths: Vec<String>,
    app: AppHandle,
) -> Result<QuarantineResult, String> {
    let conn_state = app.state::<Mutex<Connection>>();
    let q_root = quarantine_root();

    let mut moved: Vec<MovedEntry> = Vec::new();
    let mut errors: Vec<FileError> = Vec::new();
    let mut total_bytes: u64 = 0;

    for path_str in &paths {
        let source = Path::new(path_str);

        let file_size = match std::fs::metadata(source) {
            Ok(m) => m.len(),
            Err(e) => {
                errors.push(FileError { path: path_str.clone(), message: e.to_string() });
                continue;
            }
        };

        let sha256 = match sha256_file(source) {
            Ok(h) => h,
            Err(e) => {
                errors.push(FileError { path: path_str.clone(), message: format!("hash failed: {e}") });
                continue;
            }
        };

        let dest = quarantine_dest(source, &q_root);
        let dest_str = dest.to_string_lossy().into_owned();

        // Write PENDING before touching the filesystem
        let journal_id = {
            let guard = conn_state.lock().map_err(|e| e.to_string())?;
            op_journal::write_pending(&guard, path_str, &dest_str, &sha256, "", false)
                .map_err(|e| e.to_string())?
        };

        match core_q::move_file(source, &dest, &sha256) {
            Ok(_) => {
                let guard = conn_state.lock().map_err(|e| e.to_string())?;
                let _ = op_journal::mark_completed(&guard, journal_id);
                tracing::info!("quarantined {} → {}", path_str, dest_str);
                total_bytes += file_size;
                moved.push(MovedEntry {
                    original: path_str.clone(),
                    quarantine_path: dest_str,
                    journal_id,
                    bytes: file_size,
                });
            }
            Err(e) => {
                let guard = conn_state.lock().map_err(|e| e.to_string())?;
                let _ = op_journal::mark_failed(&guard, journal_id);
                errors.push(FileError { path: path_str.clone(), message: e.to_string() });
            }
        }
    }

    Ok(QuarantineResult { moved, errors, total_bytes })
}

#[derive(Serialize)]
pub struct QuarantineItem {
    pub id: i64,
    pub original_path: String,
    pub quarantine_path: String,
    pub quarantined_at: String,
    pub file_size: u64,
}

#[tauri::command]
pub async fn list_quarantine(app: AppHandle) -> Result<Vec<QuarantineItem>, String> {
    let conn_state = app.state::<Mutex<Connection>>();
    let guard = conn_state.lock().map_err(|e| e.to_string())?;
    let entries = dedupe_index::op_journal::list_quarantined(&guard)
        .map_err(|e| e.to_string())?;

    let items = entries
        .into_iter()
        .map(|e| {
            let file_size = std::fs::metadata(&e.dest_path)
                .map(|m| m.len())
                .unwrap_or(0);
            QuarantineItem {
                id: e.id,
                original_path: e.source_path,
                quarantine_path: e.dest_path,
                quarantined_at: e.completed_at,
                file_size,
            }
        })
        .collect();

    Ok(items)
}

#[tauri::command]
pub async fn restore_files(
    entries: Vec<RestoreEntry>,
    app: AppHandle,
) -> Result<RestoreResult, String> {
    let conn_state = app.state::<Mutex<Connection>>();
    let mut restored: Vec<String> = Vec::new();
    let mut errors: Vec<FileError> = Vec::new();

    for entry in &entries {
        let q_path = Path::new(&entry.quarantine_path);
        let orig_path = Path::new(&entry.original);

        let sha256 = match sha256_file(q_path) {
            Ok(h) => h,
            Err(e) => {
                errors.push(FileError {
                    path: entry.quarantine_path.clone(),
                    message: format!("hash failed: {e}"),
                });
                continue;
            }
        };

        // If original path is occupied (another file moved there), use collision_safe
        let restore_dest = core_q::collision_safe(orig_path);

        match core_q::move_file(q_path, &restore_dest, &sha256) {
            Ok(_) => {
                let guard = conn_state.lock().map_err(|e| e.to_string())?;
                let _ = op_journal::mark_rolled_back(&guard, entry.journal_id);
                tracing::info!("restored {} → {}", entry.quarantine_path, restore_dest.display());
                restored.push(entry.original.clone());
            }
            Err(e) => {
                errors.push(FileError {
                    path: entry.quarantine_path.clone(),
                    message: e.to_string(),
                });
            }
        }
    }

    Ok(RestoreResult { restored, errors })
}

#[derive(Deserialize)]
pub struct DeleteEntry {
    pub quarantine_path: String,
    pub journal_id: i64,
}

#[derive(Serialize)]
pub struct DeleteResult {
    pub deleted: Vec<String>,
    pub errors: Vec<FileError>,
    pub bytes_freed: u64,
}

/// Permanently delete quarantined files.
/// Restricted to files inside the quarantine root — will refuse to delete originals.
/// Removes the file, removes thumbnail cache, and marks the journal entry DELETED.
#[tauri::command]
pub async fn delete_permanently(
    entries: Vec<DeleteEntry>,
    app: AppHandle,
) -> Result<DeleteResult, String> {
    let q_root = quarantine_root();
    let conn_state = app.state::<Mutex<Connection>>();
    let mut deleted: Vec<String> = Vec::new();
    let mut errors: Vec<FileError> = Vec::new();
    let mut bytes_freed: u64 = 0;

    for entry in &entries {
        let path = Path::new(&entry.quarantine_path);

        // Safety: only delete files that live inside the quarantine root
        if !path.starts_with(&q_root) {
            errors.push(FileError {
                path: entry.quarantine_path.clone(),
                message: "path is not inside quarantine root — refusing to delete".into(),
            });
            continue;
        }

        let file_size = std::fs::metadata(path).map(|m| m.len()).unwrap_or(0);

        if let Err(e) = std::fs::remove_file(path) {
            errors.push(FileError { path: entry.quarantine_path.clone(), message: e.to_string() });
            continue;
        }

        bytes_freed += file_size;

        // Remove thumbnail cache entries for the quarantine path
        thumbnail_cache::remove_for_path(&entry.quarantine_path);

        // Mark journal entry as DELETED
        {
            let guard = conn_state.lock().map_err(|e| e.to_string())?;
            let _ = op_journal::mark_deleted(&guard, entry.journal_id);
        }

        tracing::info!("permanently deleted {} ({}B)", entry.quarantine_path, file_size);
        deleted.push(entry.quarantine_path.clone());
    }

    Ok(DeleteResult { deleted, errors, bytes_freed })
}
