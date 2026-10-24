use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Instant;
use serde::Serialize;
use tauri::{AppHandle, Emitter};
use dedupe_core::{grouper, hash, scanner};
use crate::commands::cache;

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
    /// How many files were served from cache (not re-read)
    pub cache_hits: usize,
}

#[derive(Serialize, Clone)]
pub struct ScanResult {
    pub total_files: usize,
    pub skipped: usize,
    pub duration_ms: u64,
    pub cache_hits: usize,
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
    let started = Instant::now();

    // Load cache index before spawning blocking tasks (cheap — one DB read)
    let cache_index = cache::load_cache_index(&app);
    let cache_index_size = cache_index.len();
    tracing::info!("scan starting with {cache_index_size} entries in cache index");

    let _ = cache::record_scan_start(&app);
    let _ = window.emit("scan-progress", ScanProgress { scanned: 0, total: 0, path: "Walking folders…".into() });

    // Phase 1: walk directories — metadata only, very fast
    let all_paths: Vec<PathBuf> = tokio::task::spawn_blocking({
        let paths = paths.clone();
        move || {
            paths.iter()
                .flat_map(|p| scanner::list_entries(std::path::Path::new(p)))
                .collect()
        }
    }).await.map_err(|e| e.to_string())?;

    // Phase 2: stat + size filter — keep only files whose size appears 2+ times
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

            let mut by_size: HashMap<u64, u32> = HashMap::new();
            for (_, size, _) in &metas { *by_size.entry(*size).or_default() += 1; }
            metas.into_iter().filter(|(_, size, _)| by_size[size] > 1).collect()
        }
    }).await.map_err(|e| e.to_string())?;

    let total_files = all_paths.len();
    let after_size = candidates.len();

    let _ = window.emit("scan-progress", ScanProgress {
        scanned: 0,
        total: after_size,
        path: format!("{total_files} files · {after_size} candidates after size filter"),
    });

    if candidates.is_empty() {
        let duration_ms = started.elapsed().as_millis() as u64;
        let _ = cache::record_scan_end(&app, duration_ms as i64);
        return Ok(ScanResult { total_files, skipped: 0, duration_ms, cache_hits: 0 });
    }

    // Phase 3: separate cache hits from files needing prehash
    // A cache hit = path is in index with matching size AND mtime_ns
    let (mut cache_hit_files, needs_prehash): (Vec<_>, Vec<_>) = {
        let idx = &cache_index;
        candidates.into_iter().partition(|(path, size, mtime_ns)| {
            let key = (path.to_string_lossy().to_string(), *size as i64, *mtime_ns);
            idx.contains_key(&key)
        })
    };

    let cache_hit_count = cache_hit_files.len();
    tracing::info!(
        "scan: {} cache hits, {} need prehash/full hash",
        cache_hit_count, needs_prehash.len()
    );

    // Phase 4: prehash only non-cached files
    let prehash_candidates: Vec<(PathBuf, u64, i64)> = tokio::task::spawn_blocking({
        let needs_prehash = needs_prehash.clone();
        move || {
            use rayon::prelude::*;
            let with_ph: Vec<(PathBuf, u64, i64, Option<[u8; 32]>)> = needs_prehash
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
    let total_to_hash = after_prehash; // cache hits resolve without hashing

    let _ = window.emit("scan-progress", ScanProgress {
        scanned: 0,
        total: total_to_hash,
        path: format!(
            "{cache_hit_count} from cache · {after_prehash} need full hash"
        ),
    });

    // Phase 5: full hash in batches — emit groups as we go
    // Start with cache-hit files converted to ScannedFile
    let mut all_files: Vec<scanner::ScannedFile> = cache_hit_files
        .drain(..)
        .map(|(path, size, mtime_ns)| {
            let key = (path.to_string_lossy().to_string(), size as i64, mtime_ns);
            let hit = cache_index.get(&key);
            scanner::ScannedFile {
                path,
                size,
                mtime_ns,
                sha256: hit.and_then(|h| h.sha256),
                pixel_hash: hit.and_then(|h| h.pixel_hash),
                error: None,
            }
        })
        .collect();

    // Emit initial groups from cache hits alone
    if !all_files.is_empty() {
        let groups = build_group_infos(&all_files);
        let _ = window.emit("scan-groups", ScanGroups {
            groups,
            scanned: 0,
            total: total_to_hash,
            cache_hits: cache_hit_count,
        });
    }

    for (batch_idx, chunk) in prehash_candidates.chunks(HASH_BATCH).enumerate() {
        let chunk_paths: Vec<PathBuf> = chunk.iter().map(|(p, _, _)| p.clone()).collect();
        let new_files = tokio::task::spawn_blocking(move || {
            scanner::scan_chunk(&chunk_paths)
        }).await.map_err(|e| e.to_string())?;

        all_files.extend(new_files);

        let scanned = ((batch_idx + 1) * HASH_BATCH).min(total_to_hash);
        let groups = build_group_infos(&all_files);
        let _ = window.emit("scan-groups", ScanGroups {
            groups,
            scanned,
            total: total_to_hash,
            cache_hits: cache_hit_count,
        });
    }

    let skipped = all_files.iter().filter(|f| f.error.is_some()).count();
    let duration_ms = started.elapsed().as_millis() as u64;

    let _ = cache::record_scan_end(&app, duration_ms as i64);

    // Persist newly-hashed files to cache (skip cache hits — already there)
    let new_files: Vec<&scanner::ScannedFile> = all_files
        .iter()
        .filter(|f| {
            let key = (f.path.to_string_lossy().to_string(), f.size as i64, f.mtime_ns);
            !cache_index.contains_key(&key)  // only save new files
        })
        .collect();

    if !new_files.is_empty() {
        if let Err(e) = cache::save_to_cache(&app, new_files.iter().map(|f| *f).collect::<Vec<_>>().as_slice()) {
            tracing::warn!("cache write failed: {e}");
        }
    }

    tracing::info!(
        "scan complete: {} files, {} groups, {} cache hits, {}ms",
        total_files,
        build_group_infos(&all_files).len(),
        cache_hit_count,
        duration_ms
    );

    Ok(ScanResult { total_files, skipped, duration_ms, cache_hits: cache_hit_count })
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
