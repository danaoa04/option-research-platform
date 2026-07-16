use serde::Serialize;
use std::{
    fs,
    io::Write,
    path::{Path, PathBuf},
};

#[derive(Serialize)]
struct BackendStatus {
    available: bool,
    mode: &'static str,
    api_version: &'static str,
}

#[derive(Serialize)]
struct SaveResult {
    filename: String,
    bytes: usize,
    checksum: String,
}

#[tauri::command]
fn backend_status() -> BackendStatus {
    BackendStatus {
        available: false,
        mode: "offline_demo",
        api_version: "v1",
    }
}

#[tauri::command]
fn backend_log_location() -> Option<String> {
    None
}

fn allowed_extension(path: &Path, expected: &str) -> bool {
    matches!(expected, "json" | "html" | "csv" | "orp-workspace")
        && path.extension().and_then(|value| value.to_str()) == Some(expected)
}

fn content_checksum(content: &[u8]) -> String {
    let mut value: u64 = 0xcbf29ce484222325;
    for byte in content {
        value ^= u64::from(*byte);
        value = value.wrapping_mul(0x100000001b3);
    }
    format!("fnv1a64:{value:016x}")
}

#[tauri::command]
fn save_export(
    path: String,
    content: String,
    expected_extension: String,
    overwrite: bool,
) -> Result<SaveResult, String> {
    if content.len() > 50 * 1024 * 1024 {
        return Err("Export exceeds the 50 MiB desktop limit".into());
    }
    let target = PathBuf::from(path);
    if !target.is_absolute() || !allowed_extension(&target, &expected_extension) {
        return Err("Invalid export destination or extension".into());
    }
    let parent = target.parent().ok_or("Export destination has no parent")?;
    let approved_parent = parent
        .canonicalize()
        .map_err(|_| "Export parent is unavailable")?;
    if target.exists() {
        if !overwrite {
            return Err("Export already exists; overwrite confirmation is required".into());
        }
        let metadata =
            fs::symlink_metadata(&target).map_err(|_| "Export metadata is unavailable")?;
        if metadata.file_type().is_symlink() {
            return Err("Symlink export destinations are not allowed".into());
        }
    }
    let filename = target.file_name().ok_or("Export filename is missing")?;
    let safe_target = approved_parent.join(filename);
    let temporary = approved_parent.join(format!(".{}.tmp", filename.to_string_lossy()));
    let bytes = content.as_bytes();
    let result = (|| -> Result<(), String> {
        let mut file =
            fs::File::create(&temporary).map_err(|_| "Unable to create temporary export")?;
        file.write_all(bytes)
            .map_err(|_| "Unable to write export")?;
        file.sync_all().map_err(|_| "Unable to sync export")?;
        fs::rename(&temporary, &safe_target).map_err(|_| "Unable to finalize export")?;
        Ok(())
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result?;
    Ok(SaveResult {
        filename: filename.to_string_lossy().into_owned(),
        bytes: bytes.len(),
        checksum: content_checksum(bytes),
    })
}

#[tauri::command]
fn read_workspace_metadata(path: String) -> Result<String, String> {
    let target = PathBuf::from(path);
    if !target.is_absolute()
        || target.extension().and_then(|value| value.to_str()) != Some("orp-workspace")
    {
        return Err("Invalid workspace file".into());
    }
    let metadata = fs::symlink_metadata(&target).map_err(|_| "Workspace file is unavailable")?;
    if metadata.file_type().is_symlink() || metadata.len() > 5 * 1024 * 1024 {
        return Err("Workspace file is unsafe or too large".into());
    }
    fs::read_to_string(target).map_err(|_| "Unable to read workspace metadata".into())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            backend_status,
            backend_log_location,
            save_export,
            read_workspace_metadata
        ])
        .run(tauri::generate_context!())
        .expect("desktop runtime failed");
}
