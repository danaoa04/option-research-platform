use serde::Serialize;
use std::{
    fs,
    io::Write,
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::Mutex,
    thread,
    time::Duration,
};
use tauri::Manager;
use tauri_plugin_dialog::DialogExt;

const BACKEND_PORT: u16 = 8765;

struct SidecarState {
    child: Mutex<Option<Child>>,
    restart_count: Mutex<u8>,
    last_exit_code: Mutex<Option<i32>>,
}

#[derive(Serialize)]
struct BackendStatus {
    available: bool,
    mode: &'static str,
    api_version: &'static str,
    protocol_version: &'static str,
    startup_phase: &'static str,
    restart_available: bool,
    last_exit_code: Option<i32>,
}

#[derive(Serialize)]
struct SaveResult {
    filename: String,
    bytes: usize,
    checksum: String,
}

#[tauri::command]
fn backend_status(state: tauri::State<'_, SidecarState>) -> BackendStatus {
    let mut available = false;
    if let Ok(mut child) = state.child.lock() {
        if let Some(process) = child.as_mut() {
            match process.try_wait() {
                Ok(None) => available = true,
                Ok(Some(status)) => {
                    if let Ok(mut last_exit) = state.last_exit_code.lock() {
                        *last_exit = status.code();
                    }
                    child.take();
                }
                Err(_) => {
                    child.take();
                }
            };
        }
    }
    let restart_count = state.restart_count.lock().map_or(3, |value| *value);
    let last_exit_code = state.last_exit_code.lock().map_or(None, |value| *value);
    BackendStatus {
        available,
        mode: if available {
            "local_backend_offline"
        } else {
            "degraded_backend"
        },
        api_version: "v1",
        protocol_version: "1",
        startup_phase: if available {
            "ready"
        } else {
            "process_stopped"
        },
        restart_available: !available && restart_count < 3,
        last_exit_code,
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

#[tauri::command]
fn select_export_path(
    app: tauri::AppHandle,
    expected_extension: String,
) -> Result<Option<String>, String> {
    if !matches!(
        expected_extension.as_str(),
        "json" | "html" | "csv" | "orp-workspace"
    ) {
        return Err("Unsupported export extension".into());
    }
    let selected = app
        .dialog()
        .file()
        .add_filter("Option Research Platform export", &[&expected_extension])
        .blocking_save_file();
    selected
        .map(|path| {
            path.into_path()
                .map_err(|_| "Selected export path is invalid".to_string())
                .and_then(|path| {
                    if allowed_extension(&path, &expected_extension) {
                        Ok(path.to_string_lossy().into_owned())
                    } else {
                        Err("Selected export extension is invalid".into())
                    }
                })
        })
        .transpose()
}

#[tauri::command]
fn select_workspace_file(app: tauri::AppHandle) -> Result<Option<String>, String> {
    let selected = app
        .dialog()
        .file()
        .add_filter("Option Research Platform workspace", &["orp-workspace"])
        .blocking_pick_file();
    selected
        .map(|path| {
            path.into_path()
                .map_err(|_| "Selected workspace path is invalid".to_string())
                .and_then(|path| {
                    if allowed_extension(&path, "orp-workspace") {
                        Ok(path.to_string_lossy().into_owned())
                    } else {
                        Err("Selected workspace extension is invalid".into())
                    }
                })
        })
        .transpose()
}

fn sidecar_path() -> Result<PathBuf, String> {
    let executable = std::env::current_exe().map_err(|_| "Desktop executable path unavailable")?;
    let directory = executable
        .parent()
        .ok_or("Desktop executable directory unavailable")?;
    let name = if cfg!(windows) {
        "orp-backend.exe"
    } else {
        "orp-backend"
    };
    let candidates = [
        directory.join(name),
        directory.join("../Resources").join(name),
        directory.join("binaries").join(name),
    ];
    candidates
        .into_iter()
        .find(|candidate| candidate.is_file())
        .ok_or_else(|| "Fixed backend sidecar is missing".into())
}

fn start_sidecar(app: &tauri::AppHandle) -> Result<Child, String> {
    let binary = sidecar_path()?;
    let app_data = app
        .path()
        .app_data_dir()
        .map_err(|_| "Application data directory unavailable")?;
    fs::create_dir_all(&app_data).map_err(|_| "Unable to prepare application data directory")?;
    Command::new(binary)
        .args([
            "--host",
            "127.0.0.1",
            "--port",
            &BACKEND_PORT.to_string(),
            "--app-data",
            app_data
                .to_str()
                .ok_or("Application data path is invalid")?,
            "--release-profile",
            "release-candidate",
            "--api-version",
            "v1",
            "--protocol-version",
            "1",
            "--parent-pid",
            &std::process::id().to_string(),
            "--migration-policy",
            "automatic",
            "--fixture-mode",
        ])
        .env_clear()
        .env("PATH", "/usr/bin:/bin")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|_| "Unable to start fixed backend sidecar".into())
}

#[tauri::command]
fn restart_sidecar(app: tauri::AppHandle) -> Result<BackendStatus, String> {
    let state = app.state::<SidecarState>();
    {
        let child = state
            .child
            .lock()
            .map_err(|_| "Sidecar state unavailable")?;
        if child.is_some() {
            return Err("Backend sidecar is already running".into());
        }
    }
    let mut restart_count = state
        .restart_count
        .lock()
        .map_err(|_| "Sidecar restart state unavailable")?;
    if *restart_count >= 3 {
        return Err("Backend restart limit reached; diagnostic recovery is required".into());
    }
    let child = start_sidecar(&app)?;
    *restart_count += 1;
    *state
        .child
        .lock()
        .map_err(|_| "Sidecar state unavailable")? = Some(child);
    drop(restart_count);
    Ok(backend_status(state))
}

fn terminate_sidecar(child: &mut Child) {
    #[cfg(unix)]
    unsafe {
        libc::kill(child.id() as i32, libc::SIGTERM);
    }
    for _ in 0..50 {
        if child.try_wait().ok().flatten().is_some() {
            return;
        }
        thread::sleep(Duration::from_millis(100));
    }
    let _ = child.kill();
    let _ = child.wait();
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(SidecarState {
            child: Mutex::new(None),
            restart_count: Mutex::new(0),
            last_exit_code: Mutex::new(None),
        })
        .setup(|app| {
            let child = start_sidecar(app.handle())?;
            let state = app.state::<SidecarState>();
            *state
                .child
                .lock()
                .map_err(|_| "Sidecar state unavailable")? = Some(child);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            backend_status,
            backend_log_location,
            save_export,
            read_workspace_metadata,
            select_export_path,
            select_workspace_file,
            restart_sidecar
        ])
        .build(tauri::generate_context!())
        .expect("desktop runtime failed")
        .run(|app, event| {
            if matches!(event, tauri::RunEvent::ExitRequested { .. }) {
                if let Ok(mut state) = app.state::<SidecarState>().child.lock() {
                    if let Some(mut child) = state.take() {
                        terminate_sidecar(&mut child);
                    }
                }
            }
        });
}
