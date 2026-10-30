use std::collections::HashMap;
use std::path::{Path, PathBuf};
use anyhow::{Context, Result};
use rayon::prelude::*;
use tracing::{debug, info, warn};
use walkdir::WalkDir;

use crate::{decode_semaphore, hash, pixel_hash};

const MIN_FILE_SIZE: u64 = 1;
const MAX_FILE_SIZE: u64 = 500 * 1024 * 1024;
const PREHASH_BYTES: usize = 4096;

static IMAGE_EXTENSIONS: &[&str] = &[
    "jpg", "jpeg", "png", "heic", "heif", "webp", "tiff", "tif", "bmp",
];

#[derive(Debug)]
pub struct ScannedFile {
    pub path: PathBuf,
    pub size: u64,
    pub mtime_ns: i64,
    pub sha256: Option<[u8; 32]>,
    pub pixel_hash: Option<[u8; 32]>,
    pub error: Option<String>,
}

/// Metadata-only record collected in pass 1.
struct FileMeta {
    path: PathBuf,
    size: u64,
    mtime_ns: i64,
}

/// Walk `root` and return all file paths (no hashing). Fast — metadata only.
pub fn list_entries(root: &Path) -> Vec<PathBuf> {
    WalkDir::new(root)
        .follow_links(false)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .map(|e| e.path().to_path_buf())
        .collect()
}

/// Full scan of a directory using the three-pass strategy:
///   Pass 1 — stat all files, keep only those with duplicate sizes
///   Pass 2 — prehash (first 4 KB), keep only groups with matching prehash
///   Pass 3 — full SHA-256 + pixel hash only survivors
pub fn scan_directory(
    root: &Path,
    _concurrency: Option<usize>,
    progress: impl Fn(usize) + Send + Sync,
) -> Result<Vec<ScannedFile>> {
    let all_entries = list_entries(root);
    let candidates = three_pass_scan(&all_entries, progress);
    info!(
        "scan_directory: {} total files, {} returned after dedup passes",
        all_entries.len(),
        candidates.len()
    );
    Ok(candidates)
}

/// Hash a slice of paths (used by the streaming scan command).
/// Applies the same three-pass strategy across the provided slice.
pub fn scan_chunk(paths: &[PathBuf]) -> Vec<ScannedFile> {
    three_pass_scan(paths, |_| {})
}

// ── three-pass implementation ────────────────────────────────────────────────

fn three_pass_scan(paths: &[PathBuf], progress: impl Fn(usize) + Send + Sync) -> Vec<ScannedFile> {
    // Pass 1: stat — filter by size range, group by size, drop unique-size singletons
    let metas: Vec<FileMeta> = paths
        .par_iter()
        .filter_map(|p| {
            let m = std::fs::metadata(p).ok()?;
            if !m.is_file() {
                return None;
            }
            let size = m.len();
            if size < MIN_FILE_SIZE || size > MAX_FILE_SIZE {
                return None;
            }
            let mtime_ns = m
                .modified()
                .ok()
                .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                .map(|d| d.as_nanos() as i64)
                .unwrap_or(0);
            Some(FileMeta { path: p.clone(), size, mtime_ns })
        })
        .collect();

    // Group by size; anything with count == 1 is guaranteed unique — drop it
    let mut by_size: HashMap<u64, Vec<usize>> = HashMap::new();
    for (i, m) in metas.iter().enumerate() {
        by_size.entry(m.size).or_default().push(i);
    }
    let size_candidates: Vec<usize> = by_size
        .into_values()
        .filter(|v| v.len() > 1)
        .flatten()
        .collect();

    let total_after_size = size_candidates.len();
    debug!(
        "pass1: {}/{} files remain after size dedup",
        total_after_size,
        metas.len()
    );

    if size_candidates.is_empty() {
        return vec![];
    }

    // Pass 2: prehash first 4 KB, drop groups where prehash is unique
    let prehashes: Vec<(usize, Option<[u8; 32]>)> = size_candidates
        .par_iter()
        .enumerate()
        .map(|(prog_i, &meta_idx)| {
            progress(prog_i);
            let ph = hash::sha256_prefix(&metas[meta_idx].path, PREHASH_BYTES).ok();
            (meta_idx, ph)
        })
        .collect();

    // Group by (size, prehash); drop singletons
    let mut by_prehash: HashMap<(u64, [u8; 32]), Vec<usize>> = HashMap::new();
    for (meta_idx, ph) in &prehashes {
        if let Some(h) = ph {
            by_prehash
                .entry((metas[*meta_idx].size, *h))
                .or_default()
                .push(*meta_idx);
        }
    }
    let prehash_candidates: Vec<usize> = by_prehash
        .into_values()
        .filter(|v| v.len() > 1)
        .flatten()
        .collect();

    debug!(
        "pass2: {}/{} files remain after prehash dedup",
        prehash_candidates.len(),
        total_after_size
    );

    if prehash_candidates.is_empty() {
        return vec![];
    }

    // Pass 3: full SHA-256 + pixel hash on survivors only
    let done_count = std::sync::atomic::AtomicUsize::new(0);
    prehash_candidates
        .par_iter()
        .map(|&meta_idx| {
            let n = done_count.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            progress(total_after_size + n);
            let m = &metas[meta_idx];
            full_scan_file(&m.path, m.size, m.mtime_ns)
        })
        .collect()
}

fn full_scan_file(path: &Path, size: u64, mtime_ns: i64) -> ScannedFile {
    let sha256 = match hash::sha256_file(path) {
        Ok(h) => h,
        Err(e) => {
            return ScannedFile {
                path: path.to_path_buf(),
                size,
                mtime_ns,
                sha256: None,
                pixel_hash: None,
                error: Some(format!("sha256: {e}")),
            }
        }
    };

    let is_image = path
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| IMAGE_EXTENSIONS.contains(&e.to_ascii_lowercase().as_str()))
        .unwrap_or(false);

    let (pixel_hash_val, pixel_err) = if is_image {
        let _permit = decode_semaphore::semaphore().acquire();
        match pixel_hash::compute(path) {
            Ok(h) => (Some(h), None),
            Err(e) => {
                warn!("pixel hash failed for {}: {e}", path.display());
                (None, Some(e.to_string()))
            }
        }
    } else {
        (None, None)
    };

    ScannedFile {
        path: path.to_path_buf(),
        size,
        mtime_ns,
        sha256: Some(sha256),
        pixel_hash: pixel_hash_val,
        error: pixel_err,
    }
}
