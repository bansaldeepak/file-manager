use std::path::PathBuf;
use serde::Serialize;
use tauri::{AppHandle, Emitter};
use dedupe_core::{grouper, scanner};

#[derive(Serialize, Clone)]
pub struct ScanProgress {
    pub scanned: usize,
    pub total: usize,
    pub path: String,
}

#[derive(Serialize, Clone)]
pub struct FileInfo {
    pub path: String,
    pub size: u64,
    pub is_keeper: bool,
    pub error: Option<String>,
}

#[derive(Serialize, Clone)]
pub struct GroupInfo {
    pub group_id: usize,
    pub match_type: String,
    pub files: Vec<FileInfo>,
}

#[derive(Serialize, Clone)]
pub struct ScanResult {
    pub groups: Vec<GroupInfo>,
    pub total_files: usize,
    pub skipped: usize,
}

#[tauri::command]
pub async fn pick_folder(app: AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;
    let (tx, rx) = tokio::sync::oneshot::channel();
    app.dialog()
        .file()
        .pick_folder(move |folder| {
            let path = folder.map(|p| p.to_string());
            let _ = tx.send(path);
        });
    rx.await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn scan_folders(
    paths: Vec<String>,
    window: tauri::Window,
) -> Result<ScanResult, String> {
    let mut all_files: Vec<scanner::ScannedFile> = Vec::new();

    for path_str in &paths {
        let root = PathBuf::from(path_str);
        let label = root
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_else(|| path_str.clone());
        let _ = window.emit(
            "scan-progress",
            ScanProgress { scanned: 0, total: 0, path: label.clone() },
        );

        let w = window.clone();
        let l = label.clone();
        let files =
            scanner::scan_directory(&root, Some(2), move |n| {
                let _ = w.emit(
                    "scan-progress",
                    ScanProgress { scanned: n, total: 0, path: l.clone() },
                );
            })
            .map_err(|e| format!("scan failed for {path_str}: {e}"))?;

        all_files.extend(files);
    }

    let total_files = all_files.len();
    let skipped = all_files.iter().filter(|f| f.error.is_some()).count();

    let groups = grouper::build_groups(&all_files);

    let group_infos = groups
        .into_iter()
        .map(|g| {
            let files = g
                .files
                .iter()
                .map(|&idx| {
                    let f = &all_files[idx];
                    FileInfo {
                        path: f.path.to_string_lossy().to_string(),
                        size: f.size,
                        is_keeper: idx == g.keeper,
                        error: f.error.clone(),
                    }
                })
                .collect();
            GroupInfo {
                group_id: g.group_id,
                match_type: match g.match_type {
                    grouper::MatchType::Exact => "exact".to_string(),
                    grouper::MatchType::PixelIdentical => "pixel".to_string(),
                },
                files,
            }
        })
        .collect();

    Ok(ScanResult { groups: group_infos, total_files, skipped })
}
