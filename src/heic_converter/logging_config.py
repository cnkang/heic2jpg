"""Logging configuration for the HEIC to JPG converter.

This module provides centralized logging configuration with:
- Configurable logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- English-only log messages
- Operation logging (conversions, errors)
- Verbose logging mode
- Platform-independent line endings
- Structured log formatting
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class PlatformIndependentFormatter(logging.Formatter):
    """Custom formatter that ensures platform-independent line endings.

    This formatter normalizes line endings to LF (\\n) regardless of platform,
    ensuring consistent log output across Windows, macOS, and Linux.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with platform-independent line endings.

        Args:
            record: The log record to format

        Returns:
            Formatted log message with normalized line endings
        """
        # Format the record using the parent formatter
        formatted = super().format(record)

        # Normalize line endings to LF
        # Replace CRLF (Windows) with LF, then ensure consistent LF
        formatted = formatted.replace("\r\n", "\n").replace("\r", "\n")

        return formatted


def setup_logging(
    level: int = logging.INFO,
    verbose: bool = False,
    log_file: Path | None = None,
) -> logging.Logger:
    """Set up logging configuration for the HEIC converter.

    This function configures the root logger with:
    - Appropriate logging level (DEBUG if verbose, otherwise specified level)
    - Console handler with formatted output
    - Optional file handler for persistent logs
    - Platform-independent line endings
    - English-only messages

    Args:
        level: Base logging level (default: INFO)
        verbose: Enable verbose logging (sets level to DEBUG)
        log_file: Optional path to log file for persistent logging

    Returns:
        Configured logger instance for the heic_converter package
    """
    # Determine effective logging level
    effective_level = logging.DEBUG if verbose else level

    # Get the root logger for the heic_converter package
    logger = logging.getLogger("heic_converter")
    logger.setLevel(effective_level)

    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(effective_level)

    # Create formatter with platform-independent line endings
    if verbose:
        # Verbose format includes more details
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
    else:
        # Standard format is more concise
        format_string = "%(asctime)s - %(levelname)s - %(message)s"

    formatter = PlatformIndependentFormatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)

    # Add console handler to logger
    logger.addHandler(console_handler)

    # Add file handler if log file is specified
    if log_file:
        try:
            # Ensure parent directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)

            # Create file handler with UTF-8 encoding
            file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8", delay=False)
            file_handler.setLevel(effective_level)
            file_handler.setFormatter(formatter)

            # Add file handler to logger
            logger.addHandler(file_handler)

            logger.debug(f"Logging to file: {log_file}")

        except Exception as e:
            # If file logging fails, log to console but don't crash
            logger.warning(f"Failed to set up file logging: {str(e)}")

    # Log initial configuration
    logger.debug(
        f"Logging configured: level={logging.getLevelName(effective_level)}, "
        f"verbose={verbose}, log_file={log_file}"
    )

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    This function returns a child logger under the heic_converter namespace,
    ensuring consistent configuration across all modules.

    Args:
        name: Name of the module (typically __name__)

    Returns:
        Logger instance for the specified module
    """
    # Ensure the name is under the heic_converter namespace
    if not name.startswith("heic_converter"):
        name = f"heic_converter.{name}"

    return logging.getLogger(name)


def set_log_level(level: int | str) -> None:
    """Change the logging level for the heic_converter package.

    This function allows dynamic adjustment of the logging level
    after initial configuration.

    Args:
        level: New logging level (can be int or string like 'DEBUG', 'INFO', etc.)

    Raises:
        ValueError: If the level string is invalid
    """
    logger = logging.getLogger("heic_converter")

    # Convert string level to int if necessary
    if isinstance(level, str):
        numeric_level = getattr(logging, level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {level}")
        level = numeric_level

    # Update logger and all handlers
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)

    logger.debug(f"Log level changed to {logging.getLevelName(level)}")


def log_operation_start(logger: logging.Logger, operation: str, **context: str) -> None:
    """Log the start of an operation with context.

    This is a convenience function for consistent operation logging.

    Args:
        logger: Logger instance to use
        operation: Name of the operation (e.g., "conversion", "analysis")
        **context: Additional context as keyword arguments (e.g., filename="test.heic")
    """
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())
    logger.info(f"Starting {operation}: {context_str}")


def log_operation_complete(
    logger: logging.Logger,
    operation: str,
    success: bool,
    duration: float | None = None,
    **context: str,
) -> None:
    """Log the completion of an operation with context.

    This is a convenience function for consistent operation logging.

    Args:
        logger: Logger instance to use
        operation: Name of the operation (e.g., "conversion", "analysis")
        success: Whether the operation succeeded
        duration: Optional duration in seconds
        **context: Additional context as keyword arguments
    """
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())
    status = "completed successfully" if success else "failed"

    if duration is not None:
        message = f"{operation.capitalize()} {status} in {duration:.2f}s: {context_str}"
    else:
        message = f"{operation.capitalize()} {status}: {context_str}"

    if success:
        logger.info(message)
    else:
        logger.error(message)


def log_operation_error(
    logger: logging.Logger, operation: str, error: Exception, **context: str
) -> None:
    """Log an operation error with context.

    This is a convenience function for consistent error logging.

    Args:
        logger: Logger instance to use
        operation: Name of the operation that failed
        error: The exception that occurred
        **context: Additional context as keyword arguments
    """
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())
    logger.error(f"Error during {operation}: {type(error).__name__}: {str(error)} - {context_str}")

    # Log stack trace at DEBUG level
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Stack trace for {operation} error:", exc_info=error)
