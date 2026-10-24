// Tauri command handlers — wired in as they're implemented

use std::path::PathBuf;

#[allow(dead_code)]
pub fn validate_path_scope(path: &str, allowed_roots: &[&str]) -> Result<(), String> {
    let abs = std::fs::canonicalize(path)
        .map_err(|e| format!("path not accessible: {e}"))?;
    for root in allowed_roots {
        let root_abs = std::fs::canonicalize(root)
            .unwrap_or_else(|_| PathBuf::from(root));
        if abs.starts_with(&root_abs) {
            return Ok(());
        }
    }
    Err(format!("path {} is outside authorized scope", path))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn path_within_root_passes() {
        let tmp = env::temp_dir();
        let child = tmp.join("test.txt");
        let result = validate_path_scope(
            child.to_str().unwrap(),
            &[tmp.to_str().unwrap()],
        );
        // child may not exist — canonicalize fails, which is expected
        // test the success case with a path that does exist
        let result = validate_path_scope(
            tmp.to_str().unwrap(),
            &[tmp.to_str().unwrap()],
        );
        assert!(result.is_ok());
    }

    #[test]
    fn path_outside_root_fails() {
        let tmp = env::temp_dir();
        let other = Path::new("/");
        let result = validate_path_scope(
            tmp.to_str().unwrap(),
            &[other.to_str().unwrap()],
        );
        // /tmp IS under / on most systems; use a more specific case
        let fake_root = tmp.join("fake_quarantine");
        let result = validate_path_scope(
            tmp.to_str().unwrap(),
            &[fake_root.to_str().unwrap()],
        );
        assert!(result.is_err());
    }
}
