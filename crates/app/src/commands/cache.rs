use std::collections::HashMap;
use std::path::{Path, PathBuf};
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager};
use dedupe_core::{grouper, scanner::ScannedFile};
use dedupe_index::{db, file_cache};

use crate::commands::scan::{FileInfo, GroupInfo};

#[derive(Serialize)]
pub struct CachedScanResult {
    pub groups: Vec<GroupInfo>,
    pub total_files: usize,
    pub skipped: usize,
    pub scanned_at: Option<String>,
    pub scan_duration_ms: Option<i64>,
}

/// A cache hit: hashes we already know for a (path, size, mtime_ns) combination.
pub struct CacheHit {
    pub sha256: Option<[u8; 32]>,
    pub pixel_hash: Option<[u8; 32]>,
}

pub type CacheIndex = HashMap<(String, i64, i64), CacheHit>;

pub fn db_path(app: &AppHandle) -> Option<PathBuf> {
    app.path().app_local_data_dir().ok().map(|d| d.join("scan_cache.db"))
}

fn open_conn(app: &AppHandle) -> Result<dedupe_index::Connection, String> {
    let path = db_path(app).ok_or("cannot resolve app data dir")?;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    db::open(&path).map_err(|e| e.to_string())
}

// ── folder persistence ───────────────────────────────────────────────────────

#[tauri::command]
pub fn save_folders(app: AppHandle, folders: Vec<String>) -> Result<(), String> {
    let conn = open_conn(&app)?;
    let json = serde_json::to_string(&folders).map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT OR REPLACE INTO scan_metadata (key, value) VALUES ('folders', ?1)",
        [&json],
    ).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn load_folders(app: AppHandle) -> Result<Vec<String>, String> {
    let path = db_path(&app).ok_or("cannot resolve app data dir")?;
    if !path.exists() {
        return Ok(vec![]);
    }
    let conn = db::open(&path).map_err(|e| e.to_string())?;
    let json: Option<String> = conn
        .query_row(
            "SELECT value FROM scan_metadata WHERE key = 'folders'",
            [],
            |r| r.get(0),
        )
        .ok();
    match json {
        None => Ok(vec![]),
        Some(j) => serde_json::from_str(&j).map_err(|e| e.to_string()),
    }
}

// ── scan timing ──────────────────────────────────────────────────────────────

pub fn record_scan_start(app: &AppHandle) -> Result<(), String> {
    let conn = open_conn(app)?;
    conn.execute(
        "INSERT OR REPLACE INTO scan_metadata (key, value) VALUES ('scan_started_at', datetime('now'))",
        [],
    ).map_err(|e| e.to_string())?;
    Ok(())
}

pub fn record_scan_end(app: &AppHandle, duration_ms: i64) -> Result<(), String> {
    let conn = open_conn(app)?;
    conn.execute_batch(&format!(
        "INSERT OR REPLACE INTO scan_metadata (key, value) VALUES ('last_scan_at', datetime('now'));
         INSERT OR REPLACE INTO scan_metadata (key, value) VALUES ('scan_duration_ms', '{duration_ms}');"
    )).map_err(|e| e.to_string())?;
    Ok(())
}

// ── cache index for resume ───────────────────────────────────────────────────

/// Load a HashMap of (path, size, mtime_ns) → hashes for cache-aware scanning.
/// Files already in cache with matching size+mtime don't need re-hashing.
pub fn load_cache_index(app: &AppHandle) -> CacheIndex {
    let path = match db_path(app) {
        Some(p) => p,
        None => return HashMap::new(),
    };
    if !path.exists() {
        return HashMap::new();
    }
    let conn = match db::open(&path) {
        Ok(c) => c,
        Err(_) => return HashMap::new(),
    };
    let records = match file_cache::load_all(&conn) {
        Ok(r) => r,
        Err(_) => return HashMap::new(),
    };
    records
        .into_iter()
        .map(|r| {
            let sha256 = r.sha256.and_then(|b| b.as_slice().try_into().ok());
            let pixel_hash = r.pixel_hash.and_then(|b| b.as_slice().try_into().ok());
            ((r.path, r.size, r.mtime_ns), CacheHit { sha256, pixel_hash })
        })
        .collect()
}

// ── load cached results ──────────────────────────────────────────────────────

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
    let scan_duration_ms = conn
        .query_row("SELECT value FROM scan_metadata WHERE key='scan_duration_ms'", [], |r| r.get::<_, String>(0))
        .ok()
        .and_then(|s| s.parse().ok());

    let files = records_to_scanned(&records);
    let mut result = build_result(files, scanned_at);
    result.scan_duration_ms = scan_duration_ms;
    Ok(Some(result))
}

// ── save after scan ──────────────────────────────────────────────────────────

pub fn save_to_cache(app: &AppHandle, files: &[&ScannedFile]) -> Result<(), String> {
    let conn = open_conn(app)?;
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
    Ok(())
}

// ── python import ────────────────────────────────────────────────────────────

#[tauri::command]
pub fn import_python_cache(app: AppHandle, python_db_path: String) -> Result<usize, String> {
    let src = Path::new(&python_db_path);
    if !src.exists() {
        return Err(format!("Python cache not found: {python_db_path}"));
    }
    let conn = open_conn(&app)?;
    conn.execute_batch(&format!(
        "ATTACH DATABASE '{src}' AS py;
         INSERT OR REPLACE INTO file_cache (path, size, mtime_ns, analyzer_version, sha256, pixel_hash, error, scanned_at)
         SELECT path,
                size,
                CAST(mtime * 1000000000 AS INTEGER),
                1,
                CASE WHEN sha256 IS NOT NULL AND LENGTH(sha256) = 64 THEN unhex(sha256) END,
                CASE WHEN pixel_hash IS NOT NULL AND LENGTH(pixel_hash) = 64 THEN unhex(pixel_hash) END,
                error,
                datetime(scanned_at, 'unixepoch')
         FROM py.images
         WHERE error IS NULL AND sha256 IS NOT NULL;
         DETACH DATABASE py;",
        src = src.display()
    )).map_err(|e| e.to_string())?;

    file_cache::set_scanned_at(&conn).map_err(|e| e.to_string())?;

    let count: usize = conn
        .query_row("SELECT COUNT(*) FROM file_cache", [], |r| r.get(0))
        .unwrap_or(0);
    Ok(count)
}

// ── helpers ──────────────────────────────────────────────────────────────────

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
    CachedScanResult { groups, total_files, skipped, scanned_at, scan_duration_ms: None }
}

// suppress unused import warning — Manager is needed for app.path()
#[allow(dead_code)]
fn _use_manager(_: &impl Manager<tauri::Wry>) {}

// needed for serde in load_folders
#[allow(dead_code)]
fn _use_deserialize<'de, T: Deserialize<'de>>() {}
