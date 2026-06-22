// src-tauri/src/main.rs
use serde_json;
use std::io::{BufRead, BufReader, Write};
use std::process::{Command, Stdio};
use std::sync::Mutex;
use tauri::State;

struct PythonBackend {
    process: Mutex<std::process::Child>,
    stdin: Mutex<std::process::ChildStdin>,
    stdout: Mutex<BufReader<std::process::ChildStdout>>,
}

fn init_python() -> Result<PythonBackend, String> {
    let python_path = std::env::current_exe()
        .unwrap()
        .parent()
        .unwrap()
        .join("python-backend/main.py");

    let mut child = Command::new("python3")
        .arg(python_path)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
        .map_err(|e| format!("Failed to start Python: {}", e))?;

    Ok(PythonBackend {
        process: Mutex::new(child),
        stdin: Mutex::new(child.stdin.take().unwrap()),
        stdout: Mutex::new(BufReader::new(child.stdout.take().unwrap())),
    })
}

fn send_command(
    backend: &PythonBackend,
    command: &str,
    data: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    let request = serde_json::json!({
        "command": command,
        "data": data
    });

    // Send to Python
    let mut stdin = backend.stdin.lock().unwrap();
    stdin
        .write_all(request.to_string().as_bytes())
        .map_err(|e| e.to_string())?;
    stdin.write_all(b"\n").map_err(|e| e.to_string())?;
    stdin.flush().map_err(|e| e.to_string())?;

    // Read response
    let mut stdout = backend.stdout.lock().unwrap();
    let mut response = String::new();
    stdout.read_line(&mut response).map_err(|e| e.to_string())?;

    serde_json::from_str(&response).map_err(|e| e.to_string())
}

#[tauri::command]
fn check_onboarding(backend: State<PythonBackend>) -> Result<bool, String> {
    let response = send_command(&backend, "check_onboarding", None)?;
    Ok(response["onboarding_done"].as_bool().unwrap_or(false))
}

#[tauri::command]
fn save_onboarding(
    backend: State<PythonBackend>,
    profile: serde_json::Value,
) -> Result<String, String> {
    let response = send_command(&backend, "save_onboarding", Some(profile))?;
    Ok(response["message"].as_str().unwrap_or("Saved").to_string())
}

#[tauri::command]
fn get_profile(backend: State<PythonBackend>) -> Result<Option<serde_json::Value>, String> {
    let response = send_command(&backend, "get_profile", None)?;
    Ok(response["profile"].as_object().cloned())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let python_backend = init_python().expect("Failed to start Python backend");

    tauri::Builder::default()
        .manage(python_backend)
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            check_onboarding,
            save_onboarding,
            get_profile
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
