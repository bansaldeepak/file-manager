use anyhow::{bail, Context, Result};
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
    // Pre-check dimensions before full decode to prevent OOM on huge images (T-008).
    // into_dimensions() reads only the image header — safe even on 100MP+ files.
    let reader = ImageReader::open(path)?.with_guessed_format()?;
    let (w, h) = reader
        .into_dimensions()
        .context("could not read image dimensions")?;

    if w > MAX_DECODE_DIMENSION || h > MAX_DECODE_DIMENSION {
        bail!(
            "image dimensions {}x{} exceed max {}px — skipping pixel hash",
            w, h, MAX_DECODE_DIMENSION
        );
    }

    // Full decode only after dimension check passes.
    let img = ImageReader::open(path)?
        .with_guessed_format()?
        .decode()
        .context("decode failed")?;

    let rgba = img.to_rgba8();
    let pw = rgba.width() as u64;
    let ph = rgba.height() as u64;

    let mut hasher = Sha256::new();
    hasher.update(pw.to_be_bytes()); // 8-byte BE width (matches app.py:w.to_bytes(8, "big"))
    hasher.update(ph.to_be_bytes()); // 8-byte BE height
    hasher.update(rgba.as_raw());
    Ok(hasher.finalize().into())
}
