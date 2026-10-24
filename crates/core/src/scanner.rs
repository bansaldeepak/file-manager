use std::path::{Path, PathBuf};
use anyhow::{Context, Result};
use rayon::prelude::*;
use tracing::{debug, info, warn};
use walkdir::WalkDir;

use crate::{decode_semaphore, hash, pixel_hash};

const MIN_FILE_SIZE: u64 = 1;
const MAX_FILE_SIZE: u64 = 500 * 1024 * 1024;

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

pub fn scan_directory(
    root: &Path,
    concurrency: Option<usize>,
    progress: impl Fn(usize) + Send + Sync,
) -> Result<Vec<ScannedFile>> {
    let entries = collect_entries(root);
    info!(
        "Scanning {} files under {} (concurrency={:?})",
        entries.len(),
        root.display(),
        concurrency
    );

    let results = if let Some(n) = concurrency {
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(n)
            .build()
            .context("build thread pool")?;
        pool.install(|| scan_entries_parallel(&entries, &progress))
    } else {
        scan_entries_parallel(&entries, &progress)
    };

    Ok(results)
}

fn collect_entries(root: &Path) -> Vec<PathBuf> {
    WalkDir::new(root)
        .follow_links(false)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .map(|e| e.path().to_path_buf())
        .collect()
}

fn scan_entries_parallel(
    entries: &[PathBuf],
    progress: &(impl Fn(usize) + Send + Sync),
) -> Vec<ScannedFile> {
    entries
        .par_iter()
        .enumerate()
        .map(|(i, path)| {
            progress(i);
            scan_file(path)
        })
        .collect()
}

fn scan_file(path: &Path) -> ScannedFile {
    let meta = match std::fs::metadata(path) {
        Ok(m) => m,
        Err(e) => {
            return ScannedFile {
                path: path.to_path_buf(),
                size: 0,
                mtime_ns: 0,
                sha256: None,
                pixel_hash: None,
                error: Some(format!("stat: {e}")),
            }
        }
    };

    let size = meta.len();
    let mtime_ns = meta
        .modified()
        .ok()
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_nanos() as i64)
        .unwrap_or(0);

    if size < MIN_FILE_SIZE || size > MAX_FILE_SIZE {
        debug!("skipping {} — size {size} out of range", path.display());
        return ScannedFile {
            path: path.to_path_buf(),
            size,
            mtime_ns,
            sha256: None,
            pixel_hash: None,
            error: Some(format!("size {size} out of range")),
        };
    }

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
