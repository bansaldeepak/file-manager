use std::path::PathBuf;
use serde::Serialize;
use tauri::{AppHandle, Emitter};
use dedupe_core::{grouper, scanner};

const CHUNK_SIZE: usize = 300;

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
pub struct ScanGroups {
    pub groups: Vec<GroupInfo>,
    pub scanned: usize,
    pub total: usize,
}

#[derive(Serialize, Clone)]
pub struct ScanResult {
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
    // Phase 1: collect all entries (fast — just filesystem walk, no hashing)
    let mut all_entries: Vec<PathBuf> = Vec::new();
    for path_str in &paths {
        let root = PathBuf::from(path_str);
        let entries = scanner::list_entries(&root);
        all_entries.extend(entries);
    }
    let total = all_entries.len();

    // Emit total so frontend can show X/Y progress
    let _ = window.emit("scan-progress", ScanProgress {
        scanned: 0,
        total,
        path: String::new(),
    });

    // Phase 2: hash in chunks, building groups progressively
    let mut all_files: Vec<scanner::ScannedFile> = Vec::new();

    for chunk in all_entries.chunks(CHUNK_SIZE) {
        let new_files = tokio::task::spawn_blocking({
            let chunk: Vec<PathBuf> = chunk.to_vec();
            move || scanner::scan_chunk(&chunk)
        })
        .await
        .map_err(|e| e.to_string())?;

        all_files.extend(new_files);

        let scanned = all_files.len();
        let groups = build_group_infos(&all_files);

        let _ = window.emit("scan-groups", ScanGroups {
            groups,
            scanned,
            total,
        });
    }

    let total_files = all_files.len();
    let skipped = all_files.iter().filter(|f| f.error.is_some()).count();
    Ok(ScanResult { total_files, skipped })
}

fn build_group_infos(files: &[scanner::ScannedFile]) -> Vec<GroupInfo> {
    grouper::build_groups(files)
        .into_iter()
        .map(|g| {
            let file_infos = g.files.iter().map(|&idx| {
                let f = &files[idx];
                FileInfo {
                    path: f.path.to_string_lossy().to_string(),
                    size: f.size,
                    is_keeper: idx == g.keeper,
                    error: f.error.clone(),
                }
            }).collect();
            GroupInfo {
                group_id: g.group_id,
                match_type: match g.match_type {
                    grouper::MatchType::Exact => "exact".to_string(),
                    grouper::MatchType::PixelIdentical => "pixel".to_string(),
                },
                files: file_infos,
            }
        })
        .collect()
}
