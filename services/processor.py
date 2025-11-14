"""
Document processor service
Handles file processing, document parsing, and library operations
"""

import os
from pathlib import Path
from config import Config
from config.exceptions import ServiceError, FileOperationError

# Import parser - use preprocess module which has all parsers
from services.preprocess import extract_text
from services.ollama_client import run_model

# File extension handlers - all use preprocess.extract_text which handles all formats
EXT_HANDLERS = {
    ".pdf": extract_text,
    ".docx": extract_text,
    ".xlsx": extract_text,  # Note: preprocess may not support XLSX, will raise error if used
    ".txt": extract_text,
}

# Data directories - Use centralized config
BASE_DIR = Config.DATA_DIR
DATA_DIR = Config.DATA_DIR
INCOMING_DIR = Config.INCOMING_DIR
PROCESSED_DIR = Config.PROCESSED_DIR
ERRORS_DIR = Config.ERRORS_DIR
LIBRARY_PDF = BASE_DIR / 'SAFE_VOFC_Library.pdf'  # Optional reference PDF

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
    except (PermissionError, OSError) as e:
        raise FileOperationError(f"Failed to list files: {e}") from e
    except Exception as e:
        raise ServiceError(f"Unexpected error listing files: {e}") from e

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
    except FileNotFoundError:
        raise
    except (PermissionError, OSError) as e:
        raise FileOperationError(f"Failed to get file info: {e}") from e
    except Exception as e:
        raise ServiceError(f"Unexpected error getting file info: {e}") from e

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
    except (PermissionError, OSError, FileNotFoundError) as e:
        raise FileOperationError(f"Failed to move file: {e}") from e
    except Exception as e:
        raise ServiceError(f"Unexpected error moving file: {e}") from e

def process_file(file_path):
    """
    Process a file by extracting text and analyzing with Ollama model.
    
    Args:
        file_path: Path to file (can be string or Path object)
    
    Returns:
        Analysis result from Ollama model
    """
    try:
        # Convert to Path object if string
        if isinstance(file_path, str):
            # If it's just a filename, assume it's in incoming directory
            if not os.path.isabs(file_path) and not os.path.dirname(file_path):
                file_path = INCOMING_DIR / file_path
            else:
                file_path = Path(file_path)
        else:
            file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file extension
        ext = file_path.suffix.lower()
        
        # Check if extension is supported
        if ext not in EXT_HANDLERS:
            raise ValueError(f"Unsupported file type: {ext}")
        
        # Extract text using appropriate parser
        text = EXT_HANDLERS[ext](str(file_path))
        
        # Limit text length for prompt (first 4000 characters)
        text_sample = text[:4000] if len(text) > 4000 else text
        
        # Run Ollama model analysis
        result = run_model(
            model="psa-engine:latest",
            prompt=f"Analyze this document for vulnerabilities and options for consideration:\n\n{text_sample}"
        )
        
        return result
        
    except (ServiceError, FileOperationError):
        raise
    except Exception as e:
        raise ServiceError(f"Failed to process file: {e}") from e

def process_document(file_path, document_type='pdf'):
    """
    Process a document (PDF, DOCX, etc.) - wrapper for process_file
    
    Args:
        file_path: Path to document file
        document_type: Type hint (not used, determined from extension)
    
    Returns:
        Analysis result from Ollama model
    """
    # Use process_file which handles all document types
    return process_file(file_path)

def search_library(query):
    """Search the VOFC library using Supabase"""
    try:
        from services.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Search vulnerabilities and OFCs in Supabase
        # This is a simple text search - can be enhanced with full-text search
        vuln_res = supabase.table('vulnerabilities').select('*').ilike('vulnerability', f'%{query}%').limit(50).execute()
        ofc_res = supabase.table('options_for_consideration').select('*').ilike('option_text', f'%{query}%').limit(50).execute()
        
        results = []
        if vuln_res.data:
            results.extend([{'type': 'vulnerability', 'data': v} for v in vuln_res.data])
        if ofc_res.data:
            results.extend([{'type': 'ofc', 'data': o} for o in ofc_res.data])
        
        return {
            "query": query,
            "results": results
        }
    except ServiceError:
        raise
    except Exception as e:
        raise ServiceError(f"Failed to search library: {e}") from e

def get_library_entry(entry_id):
    """Get a specific library entry from Supabase"""
    try:
        from services.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Try to find in vulnerabilities first
        vuln_res = supabase.table('vulnerabilities').select('*').eq('id', entry_id).execute()
        if vuln_res.data and len(vuln_res.data) > 0:
            return {"id": entry_id, "type": "vulnerability", "data": vuln_res.data[0]}
        
        # Try OFCs
        ofc_res = supabase.table('options_for_consideration').select('*').eq('id', entry_id).execute()
        if ofc_res.data and len(ofc_res.data) > 0:
            return {"id": entry_id, "type": "ofc", "data": ofc_res.data[0]}
        
        return {"id": entry_id, "data": None}
    except ServiceError:
        raise
    except Exception as e:
        raise ServiceError(f"Failed to get library entry: {e}") from e

def write_file_to_folder(filename, content, folder='processed'):
    """Write content to a file in specified folder"""
    try:
        folder_map = {
            'processed': PROCESSED_DIR,
            'library': BASE_DIR / 'library',  # Use library subdirectory
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
    except (PermissionError, OSError) as e:
        raise FileOperationError(f"Failed to write file: {e}") from e
    except Exception as e:
        raise ServiceError(f"Unexpected error writing file: {e}") from e

def get_progress():
    """Get current processing progress"""
    try:
        progress_file = DATA_DIR / 'processing_progress.json'
        if progress_file.exists():
            import json
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (FileNotFoundError, PermissionError, OSError):
        # Non-critical - return default progress
        pass
    except Exception as e:
        # Log unexpected errors but don't fail
        import logging
        logging.debug(f"Unexpected error reading progress: {e}")
    
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
    except (PermissionError, OSError) as e:
        # Log but don't fail - progress writing is non-critical
        import logging
        logging.warning(f"Could not write progress file: {e}")
    except Exception as e:
        import logging
        logging.debug(f"Unexpected error writing progress: {e}")

# Add more processing functions as needed from your old server.py

