use serde::Serialize;

#[derive(Serialize)]
struct BackendStatus { available: bool, mode: &'static str, api_version: &'static str }

#[tauri::command]
fn backend_status() -> BackendStatus {
    BackendStatus { available: false, mode: "offline", api_version: "v1" }
}

#[tauri::command]
fn backend_log_location() -> Option<String> { None }

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![backend_status, backend_log_location])
        .run(tauri::generate_context!())
        .expect("desktop runtime failed");
}
