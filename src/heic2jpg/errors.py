"""Error definitions for the HEIC to JPG converter."""

import contextlib
import logging
import traceback
from enum import Enum
from pathlib import Path
from typing import Any

from .logging_config import get_logger
from .models import ConversionResult, ConversionStatus


class ConversionError(Exception):
    """Base exception for conversion errors."""

    pass


class InvalidFileError(ConversionError):
    """Raised when input file is invalid."""

    pass


class SecurityError(ConversionError):
    """Raised when security validation fails."""

    pass


class ProcessingError(ConversionError):
    """Raised when image processing fails."""

    pass


class ErrorCategory(Enum):
    """Categories of errors for classification."""

    INPUT_VALIDATION = "input_validation"
    SECURITY = "security"
    PROCESSING = "processing"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class ErrorHandler:
    """Handles errors with appropriate logging and user feedback.

    This class provides centralized error handling for the converter,
    including error classification, user-friendly message generation,
    and comprehensive logging with context.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize the error handler.

        Args:
            logger: Optional logger instance. If None, creates a default logger.
        """
        self.logger = logger or get_logger(__name__)

    def handle_error(self, error: Exception, context: dict[str, Any]) -> ConversionResult:
        """Handle errors with appropriate logging and user feedback.

        Strategy:
        1. Log error with full context and stack trace
        2. Classify error type
        3. Generate user-friendly error message
        4. Return ConversionResult with FAILED status
        5. Never crash - always return a result

        Args:
            error: The exception that occurred
            context: Context information (e.g., input_path, operation)

        Returns:
            ConversionResult with FAILED status and error message
        """
        # Classify the error
        category = self._classify_error(error)

        # Generate user-friendly message
        user_message = self._generate_user_message(error, category, context)

        # Log the error with full context
        self._log_error(error, category, context)

        # Extract input path from context
        input_path = context.get("input_path")
        if input_path is None:
            input_path = Path("unknown")
        elif not isinstance(input_path, Path):
            input_path = Path(str(input_path))

        # Return a failed conversion result
        return ConversionResult(
            input_path=input_path,
            output_path=None,
            status=ConversionStatus.FAILED,
            error_message=user_message,
            metrics=None,
            optimization_params=None,
            processing_time=context.get("processing_time", 0.0),
        )

    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify error into category for appropriate handling.

        Args:
            error: The exception to classify

        Returns:
            ErrorCategory indicating the type of error
        """
        if isinstance(error, InvalidFileError):
            return ErrorCategory.INPUT_VALIDATION
        elif isinstance(error, SecurityError):
            return ErrorCategory.SECURITY
        elif isinstance(error, ProcessingError):
            return ErrorCategory.PROCESSING
        elif isinstance(error, (ValueError, TypeError)):
            return ErrorCategory.CONFIGURATION
        elif isinstance(error, ConversionError):
            # Generic conversion error - try to infer from message
            error_msg = str(error).lower()
            if any(
                keyword in error_msg for keyword in ["invalid", "not found", "corrupted", "format"]
            ):
                return ErrorCategory.INPUT_VALIDATION
            elif any(keyword in error_msg for keyword in ["security", "permission", "access"]):
                return ErrorCategory.SECURITY
            else:
                return ErrorCategory.PROCESSING
        else:
            return ErrorCategory.UNKNOWN

    def _generate_user_message(
        self, error: Exception, category: ErrorCategory, context: dict[str, Any]
    ) -> str:
        """Generate clear, actionable error message for user.

        Args:
            error: The exception that occurred
            category: The error category
            context: Context information

        Returns:
            User-friendly error message in English
        """
        # Get the input filename for context
        input_path = context.get("input_path")
        filename = "unknown file"
        if input_path:
            with contextlib.suppress(Exception):
                filename = Path(str(input_path)).name
            if filename == "unknown file":
                filename = str(input_path)

        # Base error message from exception
        base_message = str(error)

        # Generate category-specific message
        if category == ErrorCategory.INPUT_VALIDATION:
            if "not found" in base_message.lower():
                return f"File not found: {filename}. Please check the file path and try again."
            elif "invalid" in base_message.lower() or "format" in base_message.lower():
                return f"Invalid file format: {filename}. Only HEIC/HEIF files are supported."
            elif "corrupted" in base_message.lower():
                return f"Corrupted file: {filename}. The file appears to be damaged and cannot be read."
            elif "too large" in base_message.lower():
                return f"File too large: {filename}. Maximum file size is 500MB."
            else:
                return f"Invalid input file: {filename}. {base_message}"

        elif category == ErrorCategory.SECURITY:
            return f"Security error: {filename}. {base_message}. This operation is not allowed for security reasons."

        elif category == ErrorCategory.PROCESSING:
            operation = context.get("operation", "conversion")
            return f"Processing error during {operation}: {filename}. {base_message}"

        elif category == ErrorCategory.CONFIGURATION:
            return f"Configuration error: {base_message}. Please check your settings and try again."

        else:  # UNKNOWN
            return f"Unexpected error processing {filename}: {base_message}. Please report this issue if it persists."

    def _log_error(
        self, error: Exception, category: ErrorCategory, context: dict[str, Any]
    ) -> None:
        """Log error with full context and stack trace.

        Args:
            error: The exception that occurred
            category: The error category
            context: Context information
        """
        # Build context string
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())

        # Log at ERROR level with full details
        self.logger.error(
            f"Error [{category.value}]: {type(error).__name__}: {error}",
            extra={"context": context_str},
        )

        # Log stack trace at DEBUG level for detailed diagnostics
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                f"Stack trace for error in {context.get('input_path', 'unknown')}:\n"
                f"{''.join(traceback.format_exception(type(error), error, error.__traceback__))}"
            )
