use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::path::PathBuf;
use image::imageops::FilterType;

pub fn cache_root() -> PathBuf {
    dirs::cache_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("Dedupe/thumbnails")
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

fn is_video(path: &str) -> bool {
    matches!(
        std::path::Path::new(path)
            .extension()
            .and_then(|e| e.to_str())
            .map(|e| e.to_ascii_lowercase())
            .as_deref(),
        Some("mp4" | "mov" | "avi" | "mkv" | "m4v" | "wmv" | "flv" | "webm" | "3gp")
    )
}

fn find_ffmpeg() -> Option<String> {
    for path in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"] {
        if std::path::Path::new(path).exists() {
            return Some(path.to_string());
        }
    }
    // Fall back to PATH lookup via `which`
    std::process::Command::new("which")
        .arg("ffmpeg")
        .output()
        .ok()
        .filter(|o| o.status.success())
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
}

fn ffmpeg_extract(ffmpeg: &str, source: &str, max_px: u32, out_str: &str, seek_secs: u32) -> bool {
    let scale = format!("scale={max_px}:{max_px}:force_original_aspect_ratio=decrease");
    let mut cmd = std::process::Command::new(ffmpeg);
    if seek_secs > 0 {
        cmd.args(["-ss", &seek_secs.to_string()]);
    }
    cmd.args([
        "-i", source,
        "-vframes", "1",
        "-vf", &scale,
        "-q:v", "3",
        "-y",
        out_str,
    ])
    .stdout(std::process::Stdio::null())
    .stderr(std::process::Stdio::null())
    .status()
    .map(|s| s.success())
    .unwrap_or(false)
    && std::path::Path::new(out_str).exists()
}

fn generate_video_thumbnail(source: &str, max_px: u32, out: &std::path::Path) -> Result<(), String> {
    let ffmpeg = find_ffmpeg().ok_or("ffmpeg not found")?;
    let out_str = out.to_str().ok_or("cache path is not valid UTF-8")?;
    if let Some(parent) = out.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("mkdir failed: {e}"))?;
    }
    // Try at 1s first (most videos have content there); fall back to frame 0
    if ffmpeg_extract(&ffmpeg, source, max_px, out_str, 1) || ffmpeg_extract(&ffmpeg, source, max_px, out_str, 0) {
        Ok(())
    } else {
        Err("ffmpeg produced no output".to_string())
    }
}

/// Returns the path to a JPEG thumbnail, generating and caching it on first call.
/// Subsequent calls for the same (source, max_px) return instantly from disk.
pub fn get_or_generate(source: &str, max_px: u32) -> Result<PathBuf, String> {
    let out = cache_path(source, max_px);
    if out.exists() {
        return Ok(out);
    }

    if is_video(source) {
        generate_video_thumbnail(source, max_px, &out)?;
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
