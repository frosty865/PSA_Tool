"""
API Contract Definitions
TypedDict definitions for all API responses to ensure consistency
"""

from typing import TypedDict, List, Optional, Dict, Any


class ProgressResponse(TypedDict):
    """Contract for /api/system/progress response"""
    status: str
    timestamp: str
    message: Optional[str]
    incoming: int
    incoming_label: str
    incoming_description: str
    processed: int
    processed_label: str
    processed_description: str
    library: int
    library_label: str
    library_description: str
    errors: int
    errors_label: str
    errors_description: str
    review: int
    review_label: str
    review_description: str
    watcher_status: str


class HealthComponent(TypedDict):
    """Individual component health status"""
    status: str  # 'ok', 'offline', 'error', 'unknown'


class HealthResponse(TypedDict):
    """Contract for /api/system/health response"""
    status: str
    components: Dict[str, str]  # flask, ollama, supabase, tunnel, watcher
    service: str
    urls: Optional[Dict[str, str]]
    timestamp: str
    error: Optional[str]
    hint: Optional[str]


class LogsResponse(TypedDict):
    """Contract for /api/system/logs response"""
    lines: List[str]
    error: Optional[str]
    message: Optional[str]


class ControlResponse(TypedDict):
    """Contract for /api/system/control response"""
    status: str  # 'ok', 'error'
    message: str
    action: Optional[str]
    hint: Optional[str]
    troubleshooting: Optional[Dict[str, str]]


def validate_progress_response(data: dict) -> ProgressResponse:
    """Validate and normalize progress response"""
    required_fields = {
        'status': 'idle',
        'timestamp': '',
        'incoming': 0,
        'incoming_label': 'Pending Processing',
        'incoming_description': '',
        'processed': 0,
        'processed_label': 'Processed JSON',
        'processed_description': '',
        'library': 0,
        'library_label': 'Archived (Complete)',
        'library_description': '',
        'errors': 0,
        'errors_label': 'Processing Errors',
        'errors_description': '',
        'review': 0,
        'review_label': 'Review Queue',
        'review_description': '',
        'watcher_status': 'unknown'
    }
    
    # Ensure all required fields exist with defaults
    for field, default in required_fields.items():
        if field not in data:
            data[field] = default
    
    # Ensure counts are integers
    for field in ['incoming', 'processed', 'library', 'errors', 'review']:
        try:
            data[field] = int(data[field])
        except (ValueError, TypeError):
            data[field] = 0
    
    return data


def validate_health_response(data: dict) -> HealthResponse:
    """Validate and normalize health response"""
    required_components = ['flask', 'ollama', 'supabase', 'tunnel', 'watcher']
    
    if 'components' not in data:
        data['components'] = {}
    
    # Ensure all components exist
    for component in required_components:
        if component not in data['components']:
            data['components'][component] = 'unknown'
    
    # Ensure status exists
    if 'status' not in data:
        data['status'] = 'unknown'
    
    return data


def validate_logs_response(data: dict) -> LogsResponse:
    """Validate and normalize logs response"""
    if 'lines' not in data:
        data['lines'] = []
    
    # Ensure lines is a list
    if not isinstance(data['lines'], list):
        data['lines'] = []
    
    # Filter out None/empty lines
    data['lines'] = [line for line in data['lines'] if line and isinstance(line, str)]
    
    return data


def validate_control_response(data: dict) -> ControlResponse:
    """Validate and normalize control response"""
    if 'status' not in data:
        data['status'] = 'error'
    
    if 'message' not in data:
        data['message'] = 'Unknown error'
    
    return data

