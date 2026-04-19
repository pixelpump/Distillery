#!/usr/bin/env python3
"""
Entry point for the Distillery server when running as a Tauri sidecar.
Accepts --host and --port arguments, then starts the FastAPI app with uvicorn.
"""
import argparse
import sys
import os

# When running as a PyInstaller bundle, the working directory may not be correct.
# Set it to the directory containing the bundled data files.
if getattr(sys, '_MEIPASS', None):
    os.chdir(sys._MEIPASS)


def main():
    parser = argparse.ArgumentParser(description="Distillery Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
