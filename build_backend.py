#!/usr/bin/env python3
"""
Build the Distillery Python backend into a standalone binary using PyInstaller,
then rename it with the Rust target triple suffix for Tauri sidecar packaging.
"""
import os
import platform
import shutil
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SIDECAR_NAME = "distillery-server"
BINARIES_DIR = os.path.join(PROJECT_DIR, "src-tauri", "binaries")


def get_target_triple():
    """Get the Rust target triple for the current platform."""
    result = subprocess.run(
        ["rustc", "--print", "host-tuple"],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def build():
    print(f"[build] Building {SIDECAR_NAME} with PyInstaller...")

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", SIDECAR_NAME,
        "--distpath", os.path.join(PROJECT_DIR, "dist"),
        "--workpath", os.path.join(PROJECT_DIR, "build", "pyinstaller"),
        "--specpath", os.path.join(PROJECT_DIR, "build"),
        "--add-data", f"{os.path.join(PROJECT_DIR, 'static')}{os.pathsep}static",
        "--add-data", f"{os.path.join(PROJECT_DIR, 'extension')}{os.pathsep}extension",
        "--add-data", f"{os.path.join(PROJECT_DIR, 'audio_cache')}{os.pathsep}audio_cache",
        "--hidden-import", "main",
        "--hidden-import", "reader",
        "--hidden-import", "summarize",
        "--hidden-import", "tts",
        "--collect-all", "kokoro",
        "--hidden-import", "uvicorn",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "trafilatura",
        "--collect-data", "trafilatura",
        "--hidden-import", "soundfile",
        "--collect-data", "soundfile",
        "--collect-all", "_soundfile_data",
        "--collect-data", "language_tags",
        "--collect-data", "misaki",
        "--collect-all", "espeakng_loader",
        "--collect-all", "en_core_web_sm",
        "--collect-all", "spacy",
        "--hidden-import", "huggingface_hub",
        os.path.join(PROJECT_DIR, "sidecar_main.py"),
    ]

    subprocess.run(cmd, check=True, cwd=PROJECT_DIR)

    # Get target triple and rename
    triple = get_target_triple()
    ext = ".exe" if platform.system() == "Windows" else ""
    src = os.path.join(PROJECT_DIR, "dist", f"{SIDECAR_NAME}{ext}")
    dst = os.path.join(BINARIES_DIR, f"{SIDECAR_NAME}-{triple}{ext}")

    os.makedirs(BINARIES_DIR, exist_ok=True)
    shutil.copy2(src, dst)
    # Make executable
    os.chmod(dst, 0o755)

    print(f"[build] Sidecar binary: {dst}")
    print(f"[build] Target triple: {triple}")
    print(f"[build] Size: {os.path.getsize(dst) / (1024*1024):.1f} MB")


if __name__ == "__main__":
    build()
