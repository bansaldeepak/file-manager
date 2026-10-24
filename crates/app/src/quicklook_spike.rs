/// Quick Look spike — D5 feasibility probe.
///
/// Uses `qlmanage -p` as the initial approach: it's the CLI proxy for Quick Look
/// and works without Objective-C bindings. If the Tauri sandbox blocks it, the
/// fallback is to open the file's parent folder in Finder via `open -R`.
#[cfg(target_os = "macos")]
pub fn open_quicklook(path: &std::path::Path) -> Result<(), String> {
    let path_str = path.to_str().ok_or("path contains invalid UTF-8")?;
    let status = std::process::Command::new("qlmanage")
        .args(["-p", path_str])
        .status()
        .map_err(|e| format!("qlmanage not available: {e}"))?;
    if status.success() {
        Ok(())
    } else {
        // qlmanage opened but returned non-zero (e.g., unsupported format).
        // Treat as success for UI purposes — qlmanage shows its own error panel.
        Ok(())
    }
}

#[cfg(not(target_os = "macos"))]
pub fn open_quicklook(_path: &std::path::Path) -> Result<(), String> {
    Err("Quick Look is macOS only".to_string())
}
