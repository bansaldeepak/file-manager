use std::path::{Path, PathBuf};
use serde::Serialize;
use tauri::{AppHandle, Manager};
use dedupe_core::{grouper, scanner::ScannedFile};
use dedupe_index::{db, file_cache};

use crate::commands::scan::{GroupInfo, FileInfo};

#[derive(Serialize)]
pub struct CachedScanResult {
    pub groups: Vec<GroupInfo>,
    pub total_files: usize,
    pub skipped: usize,
    pub scanned_at: Option<String>,
}

fn db_path(app: &AppHandle) -> Option<PathBuf> {
    app.path().app_local_data_dir().ok().map(|d| d.join("scan_cache.db"))
}

#[allow(dead_code)]
fn _assert_manager_trait_used(_: &impl Manager<tauri::Wry>) {}

#[tauri::command]
pub fn load_cached(app: AppHandle) -> Result<Option<CachedScanResult>, String> {
    let path = db_path(&app).ok_or("cannot resolve app data dir")?;
    if !path.exists() {
        return Ok(None);
    }
    let conn = db::open(&path).map_err(|e| e.to_string())?;
    let records = file_cache::load_all(&conn).map_err(|e| e.to_string())?;
    if records.is_empty() {
        return Ok(None);
    }
    let scanned_at = file_cache::get_scanned_at(&conn);
    let files = records_to_scanned(&records);
    Ok(Some(build_result(files, scanned_at)))
}

/// Persist newly scanned files into the native cache and update last_scan_at.
pub fn save_to_cache(app: &AppHandle, files: &[ScannedFile]) -> Result<(), String> {
    let path = db_path(app).ok_or("cannot resolve app data dir")?;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let conn = db::open(&path).map_err(|e| e.to_string())?;
    for f in files {
        let rec = file_cache::FileCacheRecord {
            path: f.path.to_str().unwrap_or(""),
            size: f.size as i64,
            mtime_ns: f.mtime_ns,
            analyzer_version: 1,
            sha256: f.sha256.as_ref().map(|h| h.as_slice()),
            pixel_hash: f.pixel_hash.as_ref().map(|h| h.as_slice()),
            error: f.error.as_deref(),
        };
        file_cache::upsert(&conn, &rec).map_err(|e| e.to_string())?;
    }
    file_cache::set_scanned_at(&conn).map_err(|e| e.to_string())?;
    Ok(())
}

/// Import the Python dedupe_cache.sqlite3 into the native cache (one-time migration).
#[tauri::command]
pub fn import_python_cache(app: AppHandle, python_db_path: String) -> Result<usize, String> {
    let src = Path::new(&python_db_path);
    if !src.exists() {
        return Err(format!("Python cache not found: {python_db_path}"));
    }

    let native_path = db_path(&app).ok_or("cannot resolve app data dir")?;
    if let Some(parent) = native_path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let native = db::open(&native_path).map_err(|e| e.to_string())?;

    // Attach the Python DB and copy rows
    native
        .execute_batch(&format!(
            "ATTACH DATABASE '{}' AS py;
             INSERT OR REPLACE INTO file_cache (path, size, mtime_ns, analyzer_version, sha256, pixel_hash, error, scanned_at)
             SELECT path,
                    size,
                    CAST(mtime * 1e9 AS INTEGER),
                    1,
                    CASE WHEN sha256 IS NOT NULL THEN unhex(sha256) END,
                    CASE WHEN pixel_hash IS NOT NULL THEN unhex(pixel_hash) END,
                    error,
                    datetime(scanned_at, 'unixepoch')
             FROM py.images
             WHERE error IS NULL AND sha256 IS NOT NULL;
             DETACH DATABASE py;",
            src.to_str().unwrap_or("")
        ))
        .map_err(|e| e.to_string())?;

    file_cache::set_scanned_at(&native).map_err(|e| e.to_string())?;

    let count: usize = native
        .query_row("SELECT COUNT(*) FROM file_cache", [], |r| r.get(0))
        .unwrap_or(0);
    Ok(count)
}

// ── helpers ─────────────────────────────────────────────────────────────────

fn records_to_scanned(records: &[file_cache::CachedFile]) -> Vec<ScannedFile> {
    records
        .iter()
        .map(|r| {
            let sha256 = r.sha256.as_ref().and_then(|b| b.as_slice().try_into().ok());
            let pixel_hash = r.pixel_hash.as_ref().and_then(|b| b.as_slice().try_into().ok());
            ScannedFile {
                path: PathBuf::from(&r.path),
                size: r.size as u64,
                mtime_ns: r.mtime_ns,
                sha256,
                pixel_hash,
                error: r.error.clone(),
            }
        })
        .collect()
}

fn build_result(files: Vec<ScannedFile>, scanned_at: Option<String>) -> CachedScanResult {
    let total_files = files.len();
    let skipped = files.iter().filter(|f| f.error.is_some()).count();
    let groups = grouper::build_groups(&files)
        .into_iter()
        .map(|g| {
            let file_infos = g.files.iter().map(|&idx| {
                let f = &files[idx];
                FileInfo {
                    path: f.path.to_string_lossy().to_string(),
                    size: f.size,
                    is_keeper: idx == g.keeper,
                    error: f.error.clone(),
                }
            }).collect();
            GroupInfo {
                group_id: g.group_id,
                match_type: match g.match_type {
                    grouper::MatchType::Exact => "exact".to_string(),
                    grouper::MatchType::PixelIdentical => "pixel".to_string(),
                },
                files: file_infos,
            }
        })
        .collect();
    CachedScanResult { groups, total_files, skipped, scanned_at }
}
