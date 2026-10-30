use base64::{engine::general_purpose::STANDARD, Engine};
use tokio::sync::Semaphore;
use tauri::State;
use crate::thumbnail_cache;

/// Caps concurrent image-decode threads for cache misses (cold paths only).
/// Cached reads skip the semaphore entirely — they're just a disk read + b64 encode.
const MAX_CONCURRENT: usize = 4;

pub struct ThumbnailThrottle(pub Semaphore);

impl ThumbnailThrottle {
    pub fn new() -> Self {
        Self(Semaphore::new(MAX_CONCURRENT))
    }
}

/// Returns a base64 JPEG data URL for `path` resized to fit within `max_px × max_px`.
///
/// First call generates a JPEG to the disk thumbnail cache and reads it back.
/// Subsequent calls for the same (path, max_px) read from disk only — no decode.
/// The JS side caches the data URL so each key is requested at most once per session.
#[tauri::command]
pub async fn get_thumbnail(
    path: String,
    max_px: u32,
    throttle: State<'_, ThumbnailThrottle>,
) -> Result<String, String> {
    // Fast path: cache hit — read JPEG from disk, no decode needed
    let cached = thumbnail_cache::cache_path(&path, max_px);
    if cached.exists() {
        let bytes = std::fs::read(&cached).map_err(|e| format!("read cache failed: {e}"))?;
        return Ok(format!("data:image/jpeg;base64,{}", STANDARD.encode(bytes)));
    }

    // Slow path: decode + resize + write to disk, throttled to cap OS threads
    let _permit = throttle
        .0
        .acquire()
        .await
        .map_err(|e| format!("semaphore error: {e}"))?;

    let data_url = tokio::task::spawn_blocking(move || -> Result<String, String> {
        let out = thumbnail_cache::get_or_generate(&path, max_px)?;
        let bytes = std::fs::read(&out).map_err(|e| format!("read after generate failed: {e}"))?;
        Ok(format!("data:image/jpeg;base64,{}", STANDARD.encode(bytes)))
    })
    .await
    .map_err(|e| format!("task join error: {e}"))??;

    Ok(data_url)
}

/// Pre-generate thumbnails for a list of paths in the background.
/// Returns immediately; work runs on the rayon thread pool.
/// Called after scan completes so thumbnails are on disk before the user scrolls.
#[tauri::command]
pub async fn prefetch_thumbnails(paths: Vec<String>) {
    let _ = tokio::task::spawn_blocking(move || {
        use rayon::prelude::*;
        let n = paths.len();
        paths.par_iter().for_each(|path| {
            if let Err(e) = thumbnail_cache::get_or_generate(path, 400) {
                tracing::debug!("prefetch skip {path}: {e}");
            }
        });
        tracing::info!("prefetch_thumbnails: {n} paths processed");
    });
}
