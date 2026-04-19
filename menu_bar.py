#!/usr/bin/env python3
"""
Distillery Menu Bar App for macOS
Runs the FastAPI server in the background with a status bar icon.
"""
import os
import sys
import webbrowser
import subprocess
import threading
import logging
from pathlib import Path

# When running as a PyInstaller bundle
if getattr(sys, '_MEIPASS', None):
    os.chdir(sys._MEIPASS)
    if sys._MEIPASS not in sys.path:
        sys.path.insert(0, sys._MEIPASS)

import rumps
import uvicorn
from main import app

# Configuration
APP_NAME = "Distillery"
DEFAULT_PORT = 8000
DEFAULT_HOST = "127.0.0.1"
LOG_DIR = Path.home() / "Library" / "Logs" / "Distillery"
LOG_FILE = LOG_DIR / "distillery.log"

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DistilleryApp(rumps.App):
    def __init__(self):
        super().__init__(APP_NAME, icon=None, template=True)
        self.server_thread = None
        self.server_running = False
        self.host = DEFAULT_HOST
        self.port = DEFAULT_PORT
        
        # Menu items (rumps adds Quit automatically)
        self.menu = [
            rumps.MenuItem("Open Distillery", callback=self.open_distillery),
            rumps.MenuItem("Server Status: Stopped", callback=None),
            None,  # Separator
            rumps.MenuItem("Start Server", callback=self.start_server),
            rumps.MenuItem("Stop Server", callback=self.stop_server),
            None,  # Separator
            rumps.MenuItem("Auto-start on Login", callback=self.toggle_auto_start),
            rumps.MenuItem("View Logs", callback=self.view_logs),
            None,  # Separator
            rumps.MenuItem("About Distillery", callback=self.show_about),
        ]
        
        # Auto-start server on launch (optional, could be configurable)
        self.start_server(None)
    
    def update_status_menu(self):
        """Update the status menu item and icon state."""
        status_item = self.menu["Server Status: Stopped"]
        
        if self.server_running:
            status_item.title = f"Server Status: Running on {self.host}:{self.port}"
            self.title = "\U0001F70B"  # 🜋 Alchemical alembic symbol
        else:
            status_item.title = "Server Status: Stopped"
            self.title = "\U0001F70B"  # 🜋 Alembic (same icon, server state shown in menu)
    
    def run_server(self):
        """Run the uvicorn server in a thread."""
        try:
            logger.info(f"Starting server on {self.host}:{self.port}")
            uvicorn.run(
                app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=False,
            )
        except Exception as e:
            logger.error(f"Server error: {e}")
            self.server_running = False
            rumps.notification(
                title="Distillery Error",
                subtitle="Server Failed",
                message=str(e),
                sound=True
            )
    
    def start_server(self, _):
        """Start the background server."""
        if self.server_running:
            return
        
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()
        self.server_running = True
        self.update_status_menu()
        
        rumps.notification(
            title="Distillery",
            subtitle="Server Started",
            message=f"Running on http://{self.host}:{self.port}",
            sound=False
        )
        logger.info("Server started")
    
    def stop_server(self, _):
        """Stop the background server."""
        if not self.server_running:
            return
        
        # Note: uvicorn doesn't have a clean shutdown from thread
        # The process will terminate when the menu bar app quits
        self.server_running = False
        self.update_status_menu()
        
        rumps.notification(
            title="Distillery",
            subtitle="Server Stopped",
            message="The server has been stopped",
            sound=False
        )
        logger.info("Server stopped")
    
    def open_distillery(self, _):
        """Open the web interface in browser."""
        if not self.server_running:
            self.start_server(None)
            # Give server a moment to start
            import time
            time.sleep(1)
        
        url = f"http://{self.host}:{self.port}"
        webbrowser.open(url)
        logger.info(f"Opened browser to {url}")
    
    def toggle_auto_start(self, sender):
        """Toggle login item (macOS)."""
        # This is a placeholder - implementing login items requires
        # either SMLoginItemSetEnabled or LaunchAgents
        # For now, just show an info dialog
        rumps.alert(
            title="Auto-start on Login",
            message="To enable auto-start:\n\n1. Open System Settings → General → Login Items\n2. Click '+' and add Distillery.app\n\nOr use the 'Open at Login' option when right-clicking the app in Finder.",
            ok_button="Got it",
            cancel_button=None
        )
    
    def view_logs(self, _):
        """Open the log file in Console.app or default text editor."""
        if LOG_FILE.exists():
            subprocess.run(["open", str(LOG_FILE)])
        else:
            rumps.notification(
                title="Distillery",
                subtitle="No Logs",
                message="Log file not found",
                sound=False
            )
    
    def show_about(self, sender):
        """Show about dialog."""
        logger.info("About clicked")
        # Use notification since rumps.alert can be flaky in menu callbacks
        rumps.notification(
            title="Distillery",
            subtitle="Version 1.0.0",
            message="A clean reading companion. Right-click any link in Chrome to send articles to Distillery.",
            sound=False
        )
    


def main():
    """Entry point for the menu bar app."""
    app = DistilleryApp()
    app.run()


if __name__ == "__main__":
    main()
