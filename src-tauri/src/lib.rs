use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let handle = app.handle().clone();

            // Spawn the Python backend sidecar
            let sidecar_command = handle
                .shell()
                .sidecar("distillery-server")
                .expect("failed to create sidecar command")
                .args(["--host", "127.0.0.1", "--port", "8000"]);

            let (mut rx, child) = sidecar_command
                .spawn()
                .expect("failed to spawn distillery-server sidecar");

            // Store the child process so we can kill it on exit
            app.manage(SidecarChild(std::sync::Mutex::new(Some(child))));

            // Log sidecar output
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            let line = String::from_utf8_lossy(&line);
                            println!("[sidecar stdout] {}", line);
                        }
                        CommandEvent::Stderr(line) => {
                            let line = String::from_utf8_lossy(&line);
                            eprintln!("[sidecar stderr] {}", line);
                        }
                        CommandEvent::Terminated(status) => {
                            eprintln!("[sidecar] terminated with status: {:?}", status);
                            break;
                        }
                        _ => {}
                    }
                }
            });

            // Wait for the server to be ready, then load URL in webview
            let handle2 = handle.clone();
            tauri::async_runtime::spawn(async move {
                wait_for_server("http://127.0.0.1:8000", 30).await;

                // Navigate the main window to the server
                if let Some(window) = handle2.get_webview_window("main") {
                    let _ = window.navigate("http://127.0.0.1:8000".parse().unwrap());
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Kill the sidecar when the window is closed
                if let Some(child) = window.app_handle().try_state::<SidecarChild>() {
                    if let Ok(mut guard) = child.0.lock() {
                        if let Some(child_process) = guard.take() {
                            let _ = child_process.kill();
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

struct SidecarChild(std::sync::Mutex<Option<tauri_plugin_shell::process::CommandChild>>);

async fn wait_for_server(url: &str, max_seconds: u64) {
    let client = reqwest::Client::new();
    for _ in 0..max_seconds * 2 {
        match client.get(url).send().await {
            Ok(resp) if resp.status().is_success() => {
                println!("[Distillery] Server is ready at {}", url);
                return;
            }
            _ => {}
        }
        tokio::time::sleep(std::time::Duration::from_millis(500)).await;
    }
    eprintln!("[Distillery] Warning: Server did not respond within {} seconds", max_seconds);
}
