// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandChild;
use std::sync::{Arc, Mutex};
use tauri::Manager;

type SidecarState = Arc<Mutex<Option<CommandChild>>>;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            // Start the sidecar (Python Agent)
            let sidecar_command = app.shell().sidecar("cortex-agent").unwrap();
            let (mut rx, child) = sidecar_command.spawn().expect("Failed to spawn sidecar");
            
            // Pipe sidecar output to stdout/stderr
            let _app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                use tauri_plugin_shell::process::CommandEvent;
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            println!("[Sidecar STDOUT] {}", String::from_utf8_lossy(&line).trim());
                        }
                        CommandEvent::Stderr(line) => {
                            eprintln!("[Sidecar STDERR] {}", String::from_utf8_lossy(&line).trim());
                        }
                        _ => {}
                    }
                }
            });
            
            // Store the child process for later cleanup
            app.manage(Arc::new(Mutex::new(Some(child))) as SidecarState);
            
            println!("Sidecar spawned successfully.");
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                if let Some(state) = window.try_state::<SidecarState>() {
                    let mut child_lock = state.lock().unwrap();
                    if let Some(child) = child_lock.take() {
                        println!("Window closing: killing sidecar...");
                        let _ = child.kill();
                    }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![greet])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| match event {
            tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit => {
                if let Some(state) = app_handle.try_state::<SidecarState>() {
                    let mut child_lock = state.lock().unwrap();
                    if let Some(child) = child_lock.take() {
                        println!("Gracefully stopping sidecar...");
                        let _ = child.kill();
                        std::thread::sleep(std::time::Duration::from_millis(500));
                    }
                }
            }
            _ => {}
        });
}
