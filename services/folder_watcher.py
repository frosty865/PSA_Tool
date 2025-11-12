"""
Folder Watcher Service
Monitors incoming directory for new files and processes them via VOFC-Processor service.

This module provides watcher functionality that can be controlled via Flask API.
The actual processing is handled by the VOFC-Processor Windows service.
"""

import os
import time
import logging
import threading
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

# Configuration
DATA_DIR = os.getenv("VOFC_DATA_DIR", r"C:\Tools\Ollama\Data")
INCOMING_DIR = Path(DATA_DIR) / "incoming"
AUTOMATION_DIR = Path(DATA_DIR) / "automation"
STOP_FILE = AUTOMATION_DIR / "watcher.stop"
LOG_FILE = AUTOMATION_DIR / "folder_watcher.log"

# Ensure directories exist
INCOMING_DIR.mkdir(parents=True, exist_ok=True)
AUTOMATION_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global watcher state
_watcher_thread: Optional[threading.Thread] = None
_watcher_observer: Optional[Observer] = None
_watcher_running = False
_watcher_status = "stopped"  # 'running' | 'stopped' | 'unknown'


class PDFHandler(FileSystemEventHandler):
    """Handler for PDF file events in incoming directory."""
    
    def __init__(self):
        super().__init__()
        self.processed_files = set()
    
    def on_created(self, event: FileSystemEvent):
        """Called when a new file is created."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Only process PDF files
        if file_path.suffix.lower() != '.pdf':
            return
        
        # Avoid duplicate processing
        if file_path in self.processed_files:
            return
        
        logger.info(f"New PDF detected: {file_path.name}")
        self.processed_files.add(file_path)
        
        # Note: Actual processing is handled by VOFC-Processor service
        # This watcher just monitors and logs file detection
        logger.info(f"File {file_path.name} will be processed by VOFC-Processor service")


def check_stop_signal() -> bool:
    """Check if watcher should stop."""
    return STOP_FILE.exists()


def clear_stop_signal():
    """Clear the stop signal file."""
    if STOP_FILE.exists():
        try:
            STOP_FILE.unlink()
            logger.info("Stop signal cleared")
        except Exception as e:
            logger.warning(f"Could not clear stop signal: {e}")


def start_folder_watcher():
    """
    Start the folder watcher in a background thread.
    This monitors the incoming directory and logs file detection.
    Actual processing is handled by VOFC-Processor service.
    """
    global _watcher_thread, _watcher_observer, _watcher_running, _watcher_status
    
    if _watcher_running:
        logger.warning("Watcher is already running")
        return
    
    def watcher_loop():
        global _watcher_observer, _watcher_running, _watcher_status
        
        try:
            logger.info("Starting folder watcher...")
            logger.info(f"Monitoring directory: {INCOMING_DIR}")
            
            # Clear any existing stop signal
            clear_stop_signal()
            
            # Create event handler
            event_handler = PDFHandler()
            
            # Create observer
            observer = Observer()
            observer.schedule(event_handler, str(INCOMING_DIR), recursive=False)
            observer.start()
            
            _watcher_observer = observer
            _watcher_running = True
            _watcher_status = "running"
            
            logger.info("Folder watcher started successfully")
            
            # Monitor loop
            while _watcher_running and not check_stop_signal():
                time.sleep(1)
            
            # Stop observer
            if observer:
                observer.stop()
                observer.join(timeout=5)
            
            _watcher_running = False
            _watcher_status = "stopped"
            logger.info("Folder watcher stopped")
            
        except Exception as e:
            logger.error(f"Error in watcher loop: {e}", exc_info=True)
            _watcher_running = False
            _watcher_status = "stopped"
    
    # Start watcher in background thread
    _watcher_thread = threading.Thread(target=watcher_loop, daemon=True)
    _watcher_thread.start()
    
    # Wait a moment to verify it started
    time.sleep(0.5)
    if _watcher_running:
        logger.info("Watcher thread started")
    else:
        logger.warning("Watcher thread may not have started properly")


def stop_folder_watcher():
    """Stop the folder watcher gracefully."""
    global _watcher_observer, _watcher_running, _watcher_status
    
    if not _watcher_running:
        logger.info("Watcher is not running")
        return
    
    try:
        # Create stop signal file
        STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STOP_FILE, "w") as f:
            f.write("1")
        
        logger.info("Stop signal sent to watcher")
        
        # Stop observer if it exists
        if _watcher_observer:
            _watcher_observer.stop()
            _watcher_observer.join(timeout=5)
            _watcher_observer = None
        
        _watcher_running = False
        _watcher_status = "stopped"
        
        logger.info("Folder watcher stopped")
        
    except Exception as e:
        logger.error(f"Error stopping watcher: {e}", exc_info=True)


def get_watcher_status() -> str:
    """Get current watcher status."""
    global _watcher_status, _watcher_running
    
    # Update status based on actual state
    if _watcher_running:
        _watcher_status = "running"
    elif check_stop_signal():
        _watcher_status = "stopped"
    else:
        _watcher_status = "stopped"
    
    return _watcher_status


def is_watcher_running() -> bool:
    """Check if watcher is currently running."""
    return _watcher_running and _watcher_status == "running"

