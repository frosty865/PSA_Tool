"""VOFC Processor Module - Reliable Extraction Version"""
import sys
import importlib.util
from pathlib import Path

# Import from the processor package
from .processor.run_processor import process_pdf

# Also import from services.processor module (the .py file, not the package)
# Use importlib to load the module file directly to avoid package/module conflict
_processor_module_path = Path(__file__).parent.parent / "processor.py"
if _processor_module_path.exists():
    spec = importlib.util.spec_from_file_location("services.processor_module", _processor_module_path)
    if spec and spec.loader:
        processor_module = importlib.util.module_from_spec(spec)
        sys.modules["services.processor_module"] = processor_module
        spec.loader.exec_module(processor_module)
        
        # Re-export functions and constants from the module
        process_file = processor_module.process_file
        process_document = processor_module.process_document
        INCOMING_DIR = processor_module.INCOMING_DIR
        search_library = processor_module.search_library
        get_library_entry = processor_module.get_library_entry
        list_incoming_files = processor_module.list_incoming_files
        get_file_info = processor_module.get_file_info
        move_file = processor_module.move_file
        write_file_to_folder = processor_module.write_file_to_folder
        get_progress = processor_module.get_progress
        update_progress = processor_module.update_progress
        
        __all__ = [
            'process_pdf',  # From package
            'process_file', 'process_document', 'INCOMING_DIR',  # From module
            'search_library', 'get_library_entry',  # From module
            'list_incoming_files', 'get_file_info', 'move_file',  # From module
            'write_file_to_folder', 'get_progress', 'update_progress'  # From module
        ]
    else:
        # Fallback if importlib fails
        __all__ = ['process_pdf']
else:
    # Fallback if module file doesn't exist
    __all__ = ['process_pdf']

