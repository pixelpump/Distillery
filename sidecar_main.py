#!/usr/bin/env python3
"""
Entry point for the Distillery server when running as a Tauri sidecar.
Accepts --host and --port arguments, then starts the FastAPI app with uvicorn.
"""
import argparse
import sys
import os

# When running as a PyInstaller bundle, ensure the bundled data directory
# is both the working directory and on sys.path so modules can be found.
if getattr(sys, '_MEIPASS', None):
    os.chdir(sys._MEIPASS)
    if sys._MEIPASS not in sys.path:
        sys.path.insert(0, sys._MEIPASS)


def main():
    parser = argparse.ArgumentParser(description="Distillery Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    args = parser.parse_args()

    # Import app object directly — string imports fail inside PyInstaller bundles
    from main import app
    import uvicorn
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
