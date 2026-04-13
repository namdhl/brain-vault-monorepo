# Desktop app skeleton

This folder is a placeholder for a Tauri-based Windows wrapper around the web app.

Recommended strategy:
- during development, point Tauri to `http://localhost:3000`
- in production, either wrap a deployed web build or export a dedicated frontend build

Files included:
- `src-tauri/Cargo.toml`
- `src-tauri/tauri.conf.json`
- `src-tauri/src/main.rs`

You can initialize a full Tauri app later after the web app stabilizes.
