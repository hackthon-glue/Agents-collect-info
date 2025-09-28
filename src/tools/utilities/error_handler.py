"""
Error handling utilities for the Strands Data Pipeline

Provides centralized error handling, logging, and recovery mechanisms.
"""

import logging
import traceback
import sys
from typing import Dict, Any, Optional, Type, Union
from datetime import datetime
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""

    API_ERROR = "api_error"
    DATABASE_ERROR = "database_error"
    STORAGE_ERROR = "storage_error"
    VALIDATION_ERROR = "validation_error"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    PROCESSING_ERROR = "processing_error"
    UNKNOWN_ERROR = "unknown_error"


class StrandsError(Exception):
    """Base exception class for Strands Data Pipeline"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization"""
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "timestamp": self.timestamp,
            "type": self.__class__.__name__,
        }


class APIError(StrandsError):
    """API-related errors"""

    def __init__(
        self,
        message: str,
        api_name: str = "",
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        details = {
            "api_name": api_name,
            "status_code": status_code,
            "response_body": response_body,
        }
        super().__init__(
            message, ErrorCategory.API_ERROR, ErrorSeverity.MEDIUM, details
        )


class DatabaseError(StrandsError):
    """Database-related errors"""

    def __init__(self, message: str, operation: str = "", table: str = ""):
        details = {"operation": operation, "table": table}
        super().__init__(
            message, ErrorCategory.DATABASE_ERROR, ErrorSeverity.HIGH, details
        )


class StorageError(StrandsError):
    """Storage-related errors"""

    def __init__(self, message: str, storage_type: str = "", path: str = ""):
        details = {"storage_type": storage_type, "path": path}
        super().__init__(
            message, ErrorCategory.STORAGE_ERROR, ErrorSeverity.MEDIUM, details
        )


class ValidationError(StrandsError):
    """Data validation errors"""

    def __init__(
        self, message: str, field: str = "", value: Any = None, schema: str = ""
    ):
        details = {
            "field": field,
            "value": str(value) if value is not None else None,
            "schema": schema,
        }
        super().__init__(
            message, ErrorCategory.VALIDATION_ERROR, ErrorSeverity.LOW, details
        )


class ConfigurationError(StrandsError):
    """Configuration-related errors"""

    def __init__(self, message: str, config_key: str = "", config_file: str = ""):
        details = {"config_key": config_key, "config_file": config_file}
        super().__init__(
            message, ErrorCategory.CONFIGURATION_ERROR, ErrorSeverity.HIGH, details
        )


class ErrorHandler:
    """Centralized error handling and logging"""

    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, datetime] = {}

    def handle_error(
        self,
        error: Union[Exception, StrandsError],
        context: str = "",
        reraise: bool = False,
    ) -> Dict[str, Any]:
        """
        Handle an error with logging and optional re-raising

        Args:
            error: The exception to handle
            context: Additional context about where the error occurred
            reraise: Whether to re-raise the exception after handling

        Returns:
            Dictionary containing error information
        """
        # Convert to StrandsError if needed
        if not isinstance(error, StrandsError):
            strands_error = self._convert_to_strands_error(error)
        else:
            strands_error = error

        # Add context to details
        if context:
            strands_error.details["context"] = context

        # Log the error
        self._log_error(strands_error, context)

        # Update error tracking
        self._track_error(strands_error)

        # Create error response
        error_response = {
            "error_id": self._generate_error_id(strands_error),
            "message": strands_error.message,
            "category": strands_error.category.value,
            "severity": strands_error.severity.value,
            "timestamp": strands_error.timestamp,
            "details": strands_error.details,
            "traceback": (
                self._get_traceback()
                if strands_error.severity
                in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
                else None
            ),
        }

        # Re-raise if requested
        if reraise:
            raise strands_error

        return error_response

    def _convert_to_strands_error(self, error: Exception) -> StrandsError:
        """Convert a generic exception to a StrandsError"""
        error_type = type(error).__name__
        message = str(error)

        # Map common exception types to categories
        category_mapping = {
            "ConnectionError": ErrorCategory.NETWORK_ERROR,
            "TimeoutError": ErrorCategory.NETWORK_ERROR,
            "HTTPError": ErrorCategory.API_ERROR,
            "DatabaseError": ErrorCategory.DATABASE_ERROR,
            "PermissionError": ErrorCategory.AUTHENTICATION_ERROR,
            "FileNotFoundError": ErrorCategory.STORAGE_ERROR,
            "ValueError": ErrorCategory.VALIDATION_ERROR,
            "KeyError": ErrorCategory.CONFIGURATION_ERROR,
        }

        category = category_mapping.get(error_type, ErrorCategory.UNKNOWN_ERROR)

        # Determine severity based on error type
        severity = ErrorSeverity.MEDIUM
        if error_type in ["DatabaseError", "PermissionError"]:
            severity = ErrorSeverity.HIGH
        elif error_type in ["ConnectionError", "TimeoutError"]:
            severity = ErrorSeverity.MEDIUM
        elif error_type in ["ValueError", "KeyError"]:
            severity = ErrorSeverity.LOW

        return StrandsError(
            message=message,
            category=category,
            severity=severity,
            details={"original_type": error_type},
        )

    def _log_error(self, error: StrandsError, context: str):
        """Log the error with appropriate level"""
        log_message = f"{error.message}"
        if context:
            log_message = f"{context}: {log_message}"

        # Add details to log message
        if error.details:
            details_str = ", ".join(
                [f"{k}={v}" for k, v in error.details.items() if v is not None]
            )
            if details_str:
                log_message += f" ({details_str})"

        # Log with appropriate level based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=True)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, exc_info=True)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

    def _track_error(self, error: StrandsError):
        """Track error occurrence for monitoring"""
        error_key = f"{error.category.value}:{error.message[:50]}"

        # Update error count
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        # Update last occurrence
        self.last_errors[error_key] = datetime.utcnow()

    def _generate_error_id(self, error: StrandsError) -> str:
        """Generate a unique error ID for tracking"""
        import hashlib

        error_string = f"{error.category.value}:{error.message}:{error.timestamp}"
        return hashlib.md5(error_string.encode()).hexdigest()[:8]

    def _get_traceback(self) -> str:
        """Get current traceback as string"""
        return traceback.format_exc()

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_types": len(self.error_counts),
            "error_counts": dict(self.error_counts),
            "recent_errors": {
                k: v.isoformat()
                for k, v in self.last_errors.items()
                if (datetime.utcnow() - v).total_seconds() < 3600  # Last hour
            },
        }

    def clear_error_stats(self):
        """Clear error statistics"""
        self.error_counts.clear()
        self.last_errors.clear()
        self.logger.info("Error statistics cleared")

    def create_error_context(self, operation: str, **kwargs) -> "ErrorContext":
        """Create an error context manager for automatic error handling"""
        return ErrorContext(self, operation, **kwargs)


class ErrorContext:
    """Context manager for automatic error handling"""

    def __init__(self, error_handler: ErrorHandler, operation: str, **kwargs):
        self.error_handler = error_handler
        self.operation = operation
        self.kwargs = kwargs
        self.reraise = kwargs.get("reraise", True)

    def __enter__(self):
        return self

    def __exit__(
        self, exc_type: Optional[Type[Exception]], exc_val: Optional[Exception], exc_tb
    ):
        if exc_val is not None:
            self.error_handler.handle_error(
                exc_val, context=self.operation, reraise=self.reraise
            )
            return not self.reraise  # Suppress exception if not re-raising
        return False
