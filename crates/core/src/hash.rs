use anyhow::Result;
use sha2::{Sha256, Digest};
use std::path::Path;

/// Compute the SHA-256 hash of a file's contents.
///
/// Reads in 1 MiB chunks matching app.py:file_sha256() exactly.
pub fn sha256_file(path: &Path) -> Result<[u8; 32]> {
    use std::io::Read;
    let mut file = std::fs::File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buf = vec![0u8; 1024 * 1024];
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(hasher.finalize().into())
}
