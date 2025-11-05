"""
Document processor service
Handles file processing, document parsing, and library operations
"""

import os
import pandas as pd
from pathlib import Path

# Data directories
DATA_DIR = Path(__file__).parent.parent / 'data'
INCOMING_DIR = DATA_DIR / 'incoming'
PROCESSED_DIR = DATA_DIR / 'processed'
ERRORS_DIR = DATA_DIR / 'errors'
LIBRARY_XLSX = DATA_DIR / 'VOFC_Library.xlsx'
LIBRARY_PDF = DATA_DIR / 'SAFE_VOFC_Library.pdf'

# Ensure directories exist
for dir_path in [INCOMING_DIR, PROCESSED_DIR, ERRORS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

def list_incoming_files():
    """List all files in the incoming directory"""
    try:
        files = []
        for file_path in INCOMING_DIR.iterdir():
            if file_path.is_file():
                files.append({
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "modified": file_path.stat().st_mtime
                })
        return files
    except Exception as e:
        raise Exception(f"Failed to list files: {str(e)}")

def get_file_info(filename):
    """Get information about a specific file"""
    try:
        file_path = INCOMING_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"File {filename} not found")
        
        return {
            "filename": filename,
            "size": file_path.stat().st_size,
            "modified": file_path.stat().st_mtime,
            "path": str(file_path)
        }
    except Exception as e:
        raise Exception(f"Failed to get file info: {str(e)}")

def move_file(filename, destination='processed'):
    """Move a file from incoming to processed or errors"""
    try:
        source = INCOMING_DIR / filename
        if not source.exists():
            raise FileNotFoundError(f"File {filename} not found")
        
        if destination == 'processed':
            target = PROCESSED_DIR / filename
        elif destination == 'errors':
            target = ERRORS_DIR / filename
        else:
            raise ValueError(f"Invalid destination: {destination}")
        
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        return {"success": True, "destination": str(target)}
    except Exception as e:
        raise Exception(f"Failed to move file: {str(e)}")

def process_file(filename):
    """Process a file (extract text, analyze, etc.)"""
    try:
        file_path = INCOMING_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"File {filename} not found")
        
        # Add your file processing logic here
        # This is a placeholder - implement based on your old server.py
        
        return {
            "success": True,
            "filename": filename,
            "processed": True
        }
    except Exception as e:
        raise Exception(f"Failed to process file: {str(e)}")

def process_document(file_path, document_type='pdf'):
    """Process a document (PDF, DOCX, etc.)"""
    try:
        # Add your document processing logic here
        # This is a placeholder - implement based on your old server.py
        
        return {
            "success": True,
            "file_path": file_path,
            "type": document_type,
            "processed": True
        }
    except Exception as e:
        raise Exception(f"Failed to process document: {str(e)}")

def search_library(query):
    """Search the VOFC library"""
    try:
        if not LIBRARY_XLSX.exists():
            raise FileNotFoundError("VOFC_Library.xlsx not found")
        
        # Load library and search
        df = pd.read_excel(LIBRARY_XLSX)
        # Add search logic here
        
        return {
            "query": query,
            "results": []
        }
    except Exception as e:
        raise Exception(f"Failed to search library: {str(e)}")

def get_library_entry(entry_id):
    """Get a specific library entry"""
    try:
        if not LIBRARY_XLSX.exists():
            raise FileNotFoundError("VOFC_Library.xlsx not found")
        
        # Load library and get entry
        df = pd.read_excel(LIBRARY_XLSX)
        # Add lookup logic here
        
        return {"id": entry_id, "data": {}}
    except Exception as e:
        raise Exception(f"Failed to get library entry: {str(e)}")

def write_file_to_folder(filename, content, folder='processed'):
    """Write content to a file in specified folder"""
    try:
        folder_map = {
            'processed': PROCESSED_DIR,
            'library': LIBRARY_XLSX.parent,  # Use data/ directory
            'errors': ERRORS_DIR,
            'incoming': INCOMING_DIR
        }
        
        target_dir = folder_map.get(folder, PROCESSED_DIR)
        target_path = target_dir / filename
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target_path, 'w', encoding='utf-8') as f:
            if isinstance(content, dict):
                import json
                json.dump(content, f, indent=2)
            else:
                f.write(str(content))
        
        return {"path": str(target_path)}
    except Exception as e:
        raise Exception(f"Failed to write file: {str(e)}")

def get_progress():
    """Get current processing progress"""
    try:
        progress_file = DATA_DIR / 'processing_progress.json'
        if progress_file.exists():
            import json
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    
    return {
        "status": "idle",
        "message": "No active processing",
        "current_file": None,
        "progress_percent": 0
    }

def update_progress(status, message, current_file=None, total_files=0, current_step=None, step_total=None):
    """Update processing progress"""
    try:
        from datetime import datetime
        progress_file = DATA_DIR / 'processing_progress.json'
        
        progress_data = {
            "status": status,
            "message": message,
            "current_file": current_file,
            "total_files": total_files,
            "current_step": current_step,
            "step_total": step_total,
            "timestamp": datetime.now().isoformat(),
            "progress_percent": 0
        }
        
        if step_total and current_step:
            progress_data["progress_percent"] = min(100, int((current_step / step_total) * 100))
        elif total_files > 0 and current_step:
            progress_data["progress_percent"] = min(100, int((current_step / total_files) * 100))
        
        import json
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2)
    except Exception:
        pass  # Silently fail if progress file can't be written

# Add more processing functions as needed from your old server.py

