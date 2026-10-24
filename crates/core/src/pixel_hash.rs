use anyhow::{bail, Result};
use image::ImageReader;
use sha2::{Sha256, Digest};
use std::path::Path;

/// Maximum decode dimension. Images exceeding this are skipped (T-008 OOM guard).
pub const MAX_DECODE_DIMENSION: u32 = 32768;

/// Compute the pixel hash of an image, matching Python's app.py:signatures() exactly:
///
///   1. Open and EXIF-transpose the image
///   2. Convert to RGBA
///   3. Prefix: 8-byte big-endian width + 8-byte big-endian height
///   4. SHA-256 of (prefix + raw RGBA bytes)
///
/// Python reference (app.py:48-53):
///   img = ImageOps.exif_transpose(img).convert("RGBA")
///   w, h = img.size
///   pix = sha256(w.to_bytes(8, "big") + h.to_bytes(8, "big") + img.tobytes()).hexdigest()
pub fn compute(path: &Path) -> Result<[u8; 32]> {
    let img = ImageReader::open(path)?
        .with_guessed_format()?
        .decode()?;

    if img.width() > MAX_DECODE_DIMENSION || img.height() > MAX_DECODE_DIMENSION {
        bail!(
            "image exceeds max decode dimension: {}x{} (max {})",
            img.width(),
            img.height(),
            MAX_DECODE_DIMENSION
        );
    }

    let rgba = img.to_rgba8();
    let w = rgba.width() as u64;
    let h = rgba.height() as u64;

    let mut hasher = Sha256::new();
    hasher.update(w.to_be_bytes()); // 8-byte BE width
    hasher.update(h.to_be_bytes()); // 8-byte BE height
    hasher.update(rgba.as_raw());
    Ok(hasher.finalize().into())
}
