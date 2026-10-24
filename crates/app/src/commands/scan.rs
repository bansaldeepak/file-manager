use std::collections::HashMap;
use std::path::PathBuf;
use serde::Serialize;
use tauri::{AppHandle, Emitter};
use dedupe_core::{grouper, hash, scanner};
use crate::commands::cache;

/// How many files to full-hash per batch before emitting groups to the frontend.
const HASH_BATCH: usize = 500;
const PREHASH_BYTES: usize = 4096;
const MIN_FILE_SIZE: u64 = 1;
const MAX_FILE_SIZE: u64 = 500 * 1024 * 1024;

#[derive(Serialize, Clone)]
pub struct ScanProgress {
    pub scanned: usize,
    pub total: usize,
    pub path: String,
}

#[derive(Serialize, Clone)]
pub struct FileInfo {
    pub path: String,
    pub size: u64,
    pub is_keeper: bool,
    pub error: Option<String>,
}

#[derive(Serialize, Clone)]
pub struct GroupInfo {
    pub group_id: usize,
    pub match_type: String,
    pub files: Vec<FileInfo>,
}

#[derive(Serialize, Clone)]
pub struct ScanGroups {
    pub groups: Vec<GroupInfo>,
    pub scanned: usize,
    pub total: usize,
}

#[derive(Serialize, Clone)]
pub struct ScanResult {
    pub total_files: usize,
    pub skipped: usize,
}

#[tauri::command]
pub async fn pick_folder(app: AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;
    let (tx, rx) = tokio::sync::oneshot::channel();
    app.dialog()
        .file()
        .pick_folder(move |folder| {
            let path = folder.map(|p| p.to_string());
            let _ = tx.send(path);
        });
    rx.await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn scan_folders(
    paths: Vec<String>,
    app: AppHandle,
    window: tauri::Window,
) -> Result<ScanResult, String> {
    // Phase 1: walk all directories — metadata only, very fast
    let _ = window.emit("scan-progress", ScanProgress { scanned: 0, total: 0, path: "Walking folders…".into() });

    let all_paths: Vec<PathBuf> = tokio::task::spawn_blocking({
        let paths = paths.clone();
        move || {
            paths.iter()
                .flat_map(|p| scanner::list_entries(std::path::Path::new(p)))
                .collect()
        }
    }).await.map_err(|e| e.to_string())?;

    // Phase 2: stat + size filter — keep only files whose size appears 2+ times (no reads)
    let candidates: Vec<(PathBuf, u64, i64)> = tokio::task::spawn_blocking({
        let all_paths = all_paths.clone();
        move || {
            use rayon::prelude::*;
            let metas: Vec<(PathBuf, u64, i64)> = all_paths
                .par_iter()
                .filter_map(|p| {
                    let m = std::fs::metadata(p).ok()?;
                    let size = m.len();
                    if size < MIN_FILE_SIZE || size > MAX_FILE_SIZE { return None; }
                    let mtime_ns = m.modified().ok()
                        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                        .map(|d| d.as_nanos() as i64)
                        .unwrap_or(0);
                    Some((p.clone(), size, mtime_ns))
                })
                .collect();

            // Size filter — drop unique sizes
            let mut by_size: HashMap<u64, u32> = HashMap::new();
            for (_, size, _) in &metas { *by_size.entry(*size).or_default() += 1; }
            metas.into_iter().filter(|(_, size, _)| by_size[size] > 1).collect()
        }
    }).await.map_err(|e| e.to_string())?;

    let after_size = candidates.len();
    let total_files = all_paths.len();

    let _ = window.emit("scan-progress", ScanProgress {
        scanned: 0,
        total: after_size,
        path: format!("{total_files} files found, {} need checking", after_size),
    });

    if candidates.is_empty() {
        return Ok(ScanResult { total_files, skipped: 0 });
    }

    // Phase 3: prehash first 4 KB — filter to groups with matching prehash
    let prehash_candidates: Vec<(PathBuf, u64, i64)> = tokio::task::spawn_blocking({
        let candidates = candidates.clone();
        move || {
            use rayon::prelude::*;
            let with_ph: Vec<(PathBuf, u64, i64, Option<[u8; 32]>)> = candidates
                .par_iter()
                .map(|(p, size, mtime_ns)| {
                    let ph = hash::sha256_prefix(p, PREHASH_BYTES).ok();
                    (p.clone(), *size, *mtime_ns, ph)
                })
                .collect();

            let mut by_ph: HashMap<(u64, [u8; 32]), u32> = HashMap::new();
            for (_, size, _, ph) in &with_ph {
                if let Some(h) = ph { *by_ph.entry((*size, *h)).or_default() += 1; }
            }
            with_ph.into_iter()
                .filter(|(_, size, _, ph)| ph.map_or(false, |h| by_ph[&(*size, h)] > 1))
                .map(|(p, s, m, _)| (p, s, m))
                .collect()
        }
    }).await.map_err(|e| e.to_string())?;

    let after_prehash = prehash_candidates.len();
    let _ = window.emit("scan-progress", ScanProgress {
        scanned: 0,
        total: after_prehash,
        path: format!("{after_prehash} candidates after pre-filter"),
    });

    if prehash_candidates.is_empty() {
        return Ok(ScanResult { total_files, skipped: 0 });
    }

    // Phase 4: full SHA-256 + pixel hash in batches, emitting groups as we go
    let mut all_files: Vec<scanner::ScannedFile> = Vec::new();

    for (batch_idx, chunk) in prehash_candidates.chunks(HASH_BATCH).enumerate() {
        let chunk_paths: Vec<PathBuf> = chunk.iter().map(|(p, _, _)| p.clone()).collect();
        let new_files = tokio::task::spawn_blocking(move || {
            scanner::scan_chunk(&chunk_paths)
        }).await.map_err(|e| e.to_string())?;

        all_files.extend(new_files);

        let scanned = (batch_idx + 1) * HASH_BATCH.min(after_prehash);
        let groups = build_group_infos(&all_files);

        let _ = window.emit("scan-groups", ScanGroups {
            groups,
            scanned: scanned.min(after_prehash),
            total: after_prehash,
        });
    }

    let skipped = all_files.iter().filter(|f| f.error.is_some()).count();

    if let Err(e) = cache::save_to_cache(&app, &all_files) {
        tracing::warn!("cache write failed: {e}");
    }

    Ok(ScanResult { total_files, skipped })
}

fn build_group_infos(files: &[scanner::ScannedFile]) -> Vec<GroupInfo> {
    grouper::build_groups(files)
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
        .collect()
}
