from datetime import datetime
import uuid
from typing import Optional

# ISO 8601 format with Z timezone indicator (UTC)
ISO_8601_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def format_datetime(dt: datetime) -> str:
    """
    Format datetime consistently across the application
    Format: ISO 8601 with Z timezone indicator (UTC)
    Example: 2023-01-01T00:00:00Z
    """
    # If the datetime is naive (no timezone), assume it's UTC
    # Return in the format YYYY-MM-DDThh:mm:ssZ (no microseconds, Z for UTC)
    return dt.strftime(ISO_8601_UTC_FORMAT)


def create_error_response(
    detail: str,
    criticality: str = "critical",
    recovery_suggestion: Optional[str] = None,
    **kwargs
):
    """
    Create a standardized error response following the common error format

    Args:
        detail: The main error message
        criticality: Indicates if the process was stopped (critical, non-critical, unknown)
        recovery_suggestion: Optional human-readable suggestion for resolving the error
        kwargs: Any additional fields to include in the error

    Returns:
        Dict with error information in the common error format
    """
    error = {"criticality": criticality, "id": str(uuid.uuid4()), "detail": detail}

    # Add optional fields if provided
    if recovery_suggestion:
        error["recoverySuggestion"] = recovery_suggestion

    # Include any additional fields
    for key, value in kwargs.items():
        if key not in error:
            error[key] = value

    return error
