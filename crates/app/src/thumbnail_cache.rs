use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::path::PathBuf;
use image::imageops::FilterType;

pub fn cache_root() -> PathBuf {
    dirs::cache_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("Arcitae/thumbnails")
}

fn path_hash(path: &str) -> u64 {
    let mut hasher = DefaultHasher::new();
    path.hash(&mut hasher);
    hasher.finish()
}

/// Returns the expected disk cache path for a given source file + display size.
pub fn cache_path(source: &str, max_px: u32) -> PathBuf {
    let h = path_hash(source);
    let prefix = format!("{:02x}", (h >> 56) as u8);
    let filename = format!("{:016x}_{max_px}.jpg", h);
    cache_root().join(prefix).join(filename)
}

/// Returns the path to a JPEG thumbnail, generating and caching it on first call.
/// Subsequent calls for the same (source, max_px) return instantly from disk.
pub fn get_or_generate(source: &str, max_px: u32) -> Result<PathBuf, String> {
    let out = cache_path(source, max_px);
    if out.exists() {
        return Ok(out);
    }

    let img = image::open(source).map_err(|e| format!("open failed: {e}"))?;

    let thumb = if img.width() > max_px || img.height() > max_px {
        img.resize(max_px, max_px, FilterType::Triangle)
    } else {
        img
    };

    if let Some(parent) = out.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("mkdir failed: {e}"))?;
    }

    thumb
        .save_with_format(&out, image::ImageFormat::Jpeg)
        .map_err(|e| format!("save failed: {e}"))?;

    Ok(out)
}

/// Remove all cached thumbnails for a given source path (call on permanent delete).
pub fn remove_for_path(source: &str) {
    let h = path_hash(source);
    let prefix = format!("{:02x}", (h >> 56) as u8);
    let dir = cache_root().join(prefix);
    let stem = format!("{:016x}_", h);
    if let Ok(entries) = std::fs::read_dir(&dir) {
        for entry in entries.flatten() {
            let name = entry.file_name();
            if name.to_str().map_or(false, |n| n.starts_with(&stem)) {
                let _ = std::fs::remove_file(entry.path());
            }
        }
    }
}
