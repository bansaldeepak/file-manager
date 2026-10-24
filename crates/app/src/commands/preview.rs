#[tauri::command]
pub fn preview_file(path: String) -> Result<(), String> {
    crate::quicklook_spike::open_quicklook(std::path::Path::new(&path))
}
