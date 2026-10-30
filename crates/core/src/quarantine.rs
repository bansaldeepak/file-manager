use std::path::{Path, PathBuf};
use anyhow::{bail, Context, Result};

use crate::hash::sha256_file;

#[derive(Debug)]
pub struct MoveResult {
    pub dest_path: PathBuf,
    pub cross_volume: bool,
}

/// Move source to dest, using rename on same volume or copy+verify+remove across volumes.
///
/// `expected_sha256` is the hash of the source file computed before calling this function.
/// On cross-volume moves, the destination hash is verified against it before removing source.
/// If verification fails, the destination copy is deleted and source is preserved.
pub fn move_file(source: &Path, dest: &Path, expected_sha256: &[u8; 32]) -> Result<MoveResult> {
    let src_dev = dev_id(source).context("stat source")?;

    let dest_parent = dest.parent().unwrap_or(Path::new("."));
    std::fs::create_dir_all(dest_parent).context("create dest parent dirs")?;
    let dst_dev = dev_id(dest_parent).context("stat dest parent")?;

    let cross_volume = src_dev != dst_dev;

    if cross_volume {
        move_cross_volume(source, dest, expected_sha256)?;
    } else {
        std::fs::rename(source, dest).context("rename")?;
    }

    Ok(MoveResult {
        dest_path: dest.to_path_buf(),
        cross_volume,
    })
}

/// Copy source → dest, verify dest hash, then remove source.
/// On any failure after the copy, removes the destination and preserves source.
/// Exposed for unit testing the hash-mismatch branch.
pub fn move_cross_volume(source: &Path, dest: &Path, expected_sha256: &[u8; 32]) -> Result<()> {
    let dest_parent = dest.parent().unwrap_or(Path::new("."));
    std::fs::create_dir_all(dest_parent).context("create dest dirs")?;

    std::fs::copy(source, dest).context("copy to dest")?;

    let dest_hash = match sha256_file(dest) {
        Ok(h) => h,
        Err(e) => {
            let _ = std::fs::remove_file(dest);
            return Err(e).context("hash dest after copy");
        }
    };

    if dest_hash != *expected_sha256 {
        let _ = std::fs::remove_file(dest);
        bail!("cross-volume copy verification failed: hash mismatch");
    }

    std::fs::remove_file(source).context("remove source after verified copy")?;
    Ok(())
}

/// Returns dest unchanged if it does not exist, otherwise appends _2, _3, … until unique.
pub fn collision_safe(dest: &Path) -> PathBuf {
    if !dest.exists() {
        return dest.to_path_buf();
    }
    let stem = dest
        .file_stem()
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned();
    let ext = dest
        .extension()
        .map(|e| format!(".{}", e.to_string_lossy()))
        .unwrap_or_default();
    let parent = dest.parent().unwrap_or(Path::new("."));
    for n in 2u32.. {
        let candidate = parent.join(format!("{stem}_{n}{ext}"));
        if !candidate.exists() {
            return candidate;
        }
    }
    unreachable!()
}

#[cfg(unix)]
fn dev_id(path: &Path) -> Result<u64> {
    use std::os::unix::fs::MetadataExt;
    Ok(std::fs::metadata(path)?.dev())
}

#[cfg(not(unix))]
fn dev_id(_path: &Path) -> Result<u64> {
    Ok(0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn same_volume_rename() {
        let dir = tempdir().unwrap();
        let src = dir.path().join("src.txt");
        let dst = dir.path().join("dst.txt");
        std::fs::write(&src, b"hello").unwrap();
        let sha = sha256_file(&src).unwrap();
        let r = move_file(&src, &dst, &sha).unwrap();
        assert!(!r.cross_volume);
        assert!(!src.exists(), "source must be gone after rename");
        assert!(dst.exists(), "dest must exist after rename");
    }

    #[test]
    fn hash_mismatch_preserves_source_and_cleans_dest() {
        let dir = tempdir().unwrap();
        let src = dir.path().join("src.txt");
        let dst = dir.path().join("subdir").join("dst.txt");
        std::fs::write(&src, b"hello").unwrap();
        let wrong_hash = [0u8; 32];
        let result = move_cross_volume(&src, &dst, &wrong_hash);
        assert!(result.is_err(), "should fail on hash mismatch");
        assert!(src.exists(), "source must be preserved on hash mismatch");
        assert!(!dst.exists(), "bad dest copy must be cleaned up");
    }

    #[test]
    fn cross_volume_copy_verify_removes_source() {
        let dir = tempdir().unwrap();
        let src = dir.path().join("src.txt");
        let dst = dir.path().join("subdir").join("dst.txt");
        std::fs::write(&src, b"hello verified").unwrap();
        let sha = sha256_file(&src).unwrap();
        move_cross_volume(&src, &dst, &sha).unwrap();
        assert!(!src.exists(), "source must be gone after verified copy");
        assert!(dst.exists(), "dest must exist after verified copy");
    }

    #[test]
    fn collision_safe_suffixes_existing_file() {
        let dir = tempdir().unwrap();
        let base = dir.path().join("img.jpg");
        std::fs::write(&base, b"").unwrap();
        let safe = collision_safe(&base);
        assert_eq!(safe, dir.path().join("img_2.jpg"));
        assert!(!safe.exists());
    }

    #[test]
    fn collision_safe_no_op_when_free() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("free.jpg");
        assert_eq!(collision_safe(&path), path);
    }
}
