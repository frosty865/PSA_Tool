"""
Domain-Specific Exception Classes

These exceptions provide clear, actionable error messages and preserve error context.
They follow the Zero-Error Architecture principle: fail-fast with explicit diagnostics.
"""


class ConfigurationError(Exception):
    """
    Raised when configuration is invalid or missing.
    
    This should be raised at startup during Config.validate().
    The system should not start if this exception is raised.
    """
    pass


class DependencyError(Exception):
    """
    Raised when a required dependency is missing or unavailable.
    
    Examples:
    - File or directory does not exist
    - Service is not running
    - Environment variable is not set
    - Network endpoint is unreachable
    
    This should be raised before attempting operations that require the dependency.
    """
    pass


class ValidationError(Exception):
    """
    Raised when data validation fails.
    
    Examples:
    - API request does not match expected schema
    - Response does not match API contract
    - File format is invalid
    
    This should be raised at API boundaries and data processing boundaries.
    """
    pass


class ServiceError(Exception):
    """
    Raised when a service operation fails.
    
    Examples:
    - Ollama API call fails
    - Supabase operation fails
    - Windows service control fails
    
    This should preserve the original exception as the cause.
    """
    pass


class FileOperationError(Exception):
    """
    Raised when a file system operation fails.
    
    Examples:
    - File cannot be read (permissions, missing)
    - Directory cannot be created
    - File move/copy fails
    
    This should include the file path and operation type in the message.
    """
    pass

