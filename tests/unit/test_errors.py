"""Unit tests for error handling."""

import logging
from pathlib import Path
from unittest.mock import MagicMock

from heic2jpg.errors import (
    ConversionError,
    ErrorCategory,
    ErrorHandler,
    InvalidFileError,
    ProcessingError,
    SecurityError,
)
from heic2jpg.models import ConversionStatus


class TestErrorClasses:
    """Tests for error exception classes."""

    def test_conversion_error_is_exception(self):
        """Test that ConversionError is an Exception."""
        error = ConversionError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_invalid_file_error_is_conversion_error(self):
        """Test that InvalidFileError inherits from ConversionError."""
        error = InvalidFileError("invalid file")
        assert isinstance(error, ConversionError)
        assert isinstance(error, Exception)
        assert str(error) == "invalid file"

    def test_security_error_is_conversion_error(self):
        """Test that SecurityError inherits from ConversionError."""
        error = SecurityError("security violation")
        assert isinstance(error, ConversionError)
        assert isinstance(error, Exception)
        assert str(error) == "security violation"

    def test_processing_error_is_conversion_error(self):
        """Test that ProcessingError inherits from ConversionError."""
        error = ProcessingError("processing failed")
        assert isinstance(error, ConversionError)
        assert isinstance(error, Exception)
        assert str(error) == "processing failed"


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_enum_values(self):
        """Test that ErrorCategory has the expected values."""
        assert ErrorCategory.INPUT_VALIDATION.value == "input_validation"
        assert ErrorCategory.SECURITY.value == "security"
        assert ErrorCategory.PROCESSING.value == "processing"
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.UNKNOWN.value == "unknown"

    def test_enum_members(self):
        """Test that ErrorCategory has exactly five members."""
        assert len(ErrorCategory) == 5
        assert ErrorCategory.INPUT_VALIDATION in ErrorCategory
        assert ErrorCategory.SECURITY in ErrorCategory
        assert ErrorCategory.PROCESSING in ErrorCategory
        assert ErrorCategory.CONFIGURATION in ErrorCategory
        assert ErrorCategory.UNKNOWN in ErrorCategory


class TestErrorClassification:
    """Tests for error classification in ErrorHandler."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler()

    def test_classify_invalid_file_error(self):
        """Test classification of InvalidFileError."""
        error = InvalidFileError("File not found")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.INPUT_VALIDATION

    def test_classify_security_error(self):
        """Test classification of SecurityError."""
        error = SecurityError("Path traversal detected")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.SECURITY

    def test_classify_processing_error(self):
        """Test classification of ProcessingError."""
        error = ProcessingError("Failed to decode HEIC")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.PROCESSING

    def test_classify_value_error(self):
        """Test classification of ValueError as configuration error."""
        error = ValueError("Invalid quality value")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.CONFIGURATION

    def test_classify_type_error(self):
        """Test classification of TypeError as configuration error."""
        error = TypeError("Expected int, got str")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.CONFIGURATION

    def test_classify_generic_conversion_error_with_invalid_keyword(self):
        """Test classification of generic ConversionError with 'invalid' keyword."""
        error = ConversionError("Invalid HEIC format")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.INPUT_VALIDATION

    def test_classify_generic_conversion_error_with_not_found_keyword(self):
        """Test classification of generic ConversionError with 'not found' keyword."""
        error = ConversionError("File not found")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.INPUT_VALIDATION

    def test_classify_generic_conversion_error_with_corrupted_keyword(self):
        """Test classification of generic ConversionError with 'corrupted' keyword."""
        error = ConversionError("Corrupted file data")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.INPUT_VALIDATION

    def test_classify_generic_conversion_error_with_format_keyword(self):
        """Test classification of generic ConversionError with 'format' keyword."""
        error = ConversionError("Unsupported format")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.INPUT_VALIDATION

    def test_classify_generic_conversion_error_with_security_keyword(self):
        """Test classification of generic ConversionError with 'security' keyword."""
        error = ConversionError("Security check failed")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.SECURITY

    def test_classify_generic_conversion_error_with_permission_keyword(self):
        """Test classification of generic ConversionError with 'permission' keyword."""
        error = ConversionError("Permission denied")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.SECURITY

    def test_classify_generic_conversion_error_with_access_keyword(self):
        """Test classification of generic ConversionError with 'access' keyword."""
        error = ConversionError("Access denied")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.SECURITY

    def test_classify_generic_conversion_error_without_keywords(self):
        """Test classification of generic ConversionError without specific keywords."""
        error = ConversionError("Something went wrong")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.PROCESSING

    def test_classify_unknown_error(self):
        """Test classification of unknown error types."""
        error = RuntimeError("Unexpected runtime error")
        category = self.handler._classify_error(error)
        assert category == ErrorCategory.UNKNOWN


class TestErrorMessageGeneration:
    """Tests for error message generation in ErrorHandler."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler()

    def test_generate_message_input_validation_not_found(self):
        """Test message generation for file not found error."""
        error = InvalidFileError("File not found")
        context = {"input_path": Path("test.heic")}
        message = self.handler._generate_user_message(
            error, ErrorCategory.INPUT_VALIDATION, context
        )
        assert "File not found: test.heic" in message
        assert "check the file path" in message

    def test_generate_message_input_validation_invalid_format(self):
        """Test message generation for invalid format error."""
        error = InvalidFileError("Invalid HEIC format")
        context = {"input_path": Path("test.jpg")}
        message = self.handler._generate_user_message(
            error, ErrorCategory.INPUT_VALIDATION, context
        )
        assert "Invalid file format: test.jpg" in message
        assert "HEIC/HEIF files are supported" in message

    def test_generate_message_input_validation_corrupted(self):
        """Test message generation for corrupted file error."""
        error = InvalidFileError("Corrupted HEIC data")
        context = {"input_path": Path("corrupt.heic")}
        message = self.handler._generate_user_message(
            error, ErrorCategory.INPUT_VALIDATION, context
        )
        assert "Corrupted file: corrupt.heic" in message
        assert "damaged" in message

    def test_generate_message_input_validation_too_large(self):
        """Test message generation for file too large error."""
        error = InvalidFileError("File too large")
        context = {"input_path": Path("huge.heic")}
        message = self.handler._generate_user_message(
            error, ErrorCategory.INPUT_VALIDATION, context
        )
        assert "File too large: huge.heic" in message
        assert "500MB" in message

    def test_generate_message_input_validation_generic(self):
        """Test message generation for generic input validation error."""
        error = InvalidFileError("Some validation error")
        context = {"input_path": Path("test.heic")}
        message = self.handler._generate_user_message(
            error, ErrorCategory.INPUT_VALIDATION, context
        )
        assert "Invalid input file: test.heic" in message
        assert "Some validation error" in message

    def test_generate_message_security_error(self):
        """Test message generation for security error."""
        error = SecurityError("Path traversal detected")
        context = {"input_path": Path("../etc/passwd")}
        message = self.handler._generate_user_message(error, ErrorCategory.SECURITY, context)
        assert "Security error: passwd" in message
        assert "Path traversal detected" in message
        assert "not allowed for security reasons" in message

    def test_generate_message_processing_error(self):
        """Test message generation for processing error."""
        error = ProcessingError("Failed to decode HEIC")
        context = {"input_path": Path("test.heic"), "operation": "decoding"}
        message = self.handler._generate_user_message(error, ErrorCategory.PROCESSING, context)
        assert "Processing error during decoding: test.heic" in message
        assert "Failed to decode HEIC" in message

    def test_generate_message_processing_error_default_operation(self):
        """Test message generation for processing error with default operation."""
        error = ProcessingError("Processing failed")
        context = {"input_path": Path("test.heic")}
        message = self.handler._generate_user_message(error, ErrorCategory.PROCESSING, context)
        assert "Processing error during conversion: test.heic" in message

    def test_generate_message_configuration_error(self):
        """Test message generation for configuration error."""
        error = ValueError("Invalid quality value: 150")
        context = {"input_path": Path("test.heic")}
        message = self.handler._generate_user_message(error, ErrorCategory.CONFIGURATION, context)
        assert "Configuration error" in message
        assert "Invalid quality value: 150" in message
        assert "check your settings" in message

    def test_generate_message_unknown_error(self):
        """Test message generation for unknown error."""
        error = RuntimeError("Unexpected error")
        context = {"input_path": Path("test.heic")}
        message = self.handler._generate_user_message(error, ErrorCategory.UNKNOWN, context)
        assert "Unexpected error processing test.heic" in message
        assert "Unexpected error" in message
        assert "report this issue" in message

    def test_generate_message_without_input_path(self):
        """Test message generation when input_path is missing from context."""
        error = InvalidFileError("Some error")
        context = {}
        message = self.handler._generate_user_message(
            error, ErrorCategory.INPUT_VALIDATION, context
        )
        assert "unknown file" in message

    def test_generate_message_all_english(self):
        """Test that all generated messages are in English."""
        test_cases = [
            (InvalidFileError("File not found"), ErrorCategory.INPUT_VALIDATION),
            (SecurityError("Security violation"), ErrorCategory.SECURITY),
            (ProcessingError("Processing failed"), ErrorCategory.PROCESSING),
            (ValueError("Invalid value"), ErrorCategory.CONFIGURATION),
            (RuntimeError("Unknown error"), ErrorCategory.UNKNOWN),
        ]

        for error, category in test_cases:
            context = {"input_path": Path("test.heic")}
            message = self.handler._generate_user_message(error, category, context)
            # Check that message is non-empty and contains only ASCII or common English characters
            assert len(message) > 0
            assert message.isascii() or all(ord(c) < 128 or c in " \n\t" for c in message)


class TestErrorLogging:
    """Tests for error logging in ErrorHandler."""

    def test_log_error_logs_at_error_level(self):
        """Test that errors are logged at ERROR level."""
        mock_logger = MagicMock(spec=logging.Logger)
        handler = ErrorHandler(logger=mock_logger)

        error = InvalidFileError("Test error")
        context = {"input_path": Path("test.heic"), "operation": "conversion"}

        handler._log_error(error, ErrorCategory.INPUT_VALIDATION, context)

        # Verify error was logged
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args

        # Check the log message
        log_message = call_args[0][0]
        assert "Error [input_validation]" in log_message
        assert "InvalidFileError" in log_message
        assert "Test error" in log_message

        # Check the context was included
        extra = call_args[1]["extra"]
        assert "input_path" in extra["context"]
        assert "operation" in extra["context"]

    def test_log_error_includes_stack_trace_in_debug(self):
        """Test that stack trace is logged at DEBUG level."""
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.isEnabledFor.return_value = True
        handler = ErrorHandler(logger=mock_logger)

        error = ProcessingError("Test error")
        context = {"input_path": Path("test.heic")}

        handler._log_error(error, ErrorCategory.PROCESSING, context)

        # Verify debug was called for stack trace
        mock_logger.debug.assert_called_once()
        debug_message = mock_logger.debug.call_args[0][0]
        assert "Stack trace" in debug_message
        assert "test.heic" in debug_message

    def test_log_error_skips_stack_trace_when_debug_disabled(self):
        """Test that stack trace is not logged when DEBUG is disabled."""
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.isEnabledFor.return_value = False
        handler = ErrorHandler(logger=mock_logger)

        error = ProcessingError("Test error")
        context = {"input_path": Path("test.heic")}

        handler._log_error(error, ErrorCategory.PROCESSING, context)

        # Verify debug was not called
        mock_logger.debug.assert_not_called()

    def test_log_error_with_multiple_context_items(self):
        """Test logging with multiple context items."""
        mock_logger = MagicMock(spec=logging.Logger)
        handler = ErrorHandler(logger=mock_logger)

        error = InvalidFileError("Test error")
        context = {
            "input_path": Path("test.heic"),
            "operation": "validation",
            "file_size": 1024,
            "attempt": 1,
        }

        handler._log_error(error, ErrorCategory.INPUT_VALIDATION, context)

        # Verify all context items are in the log
        extra = mock_logger.error.call_args[1]["extra"]
        context_str = extra["context"]
        assert "input_path" in context_str
        assert "operation" in context_str
        assert "file_size" in context_str
        assert "attempt" in context_str

    def test_log_error_with_empty_context(self):
        """Test logging with empty context."""
        mock_logger = MagicMock(spec=logging.Logger)
        handler = ErrorHandler(logger=mock_logger)

        error = InvalidFileError("Test error")
        context = {}

        handler._log_error(error, ErrorCategory.INPUT_VALIDATION, context)

        # Should still log without error
        mock_logger.error.assert_called_once()


class TestErrorHandlerIntegration:
    """Integration tests for ErrorHandler.handle_error()."""

    def test_handle_error_returns_conversion_result(self):
        """Test that handle_error returns a ConversionResult."""
        handler = ErrorHandler()
        error = InvalidFileError("Test error")
        context = {"input_path": Path("test.heic")}

        result = handler.handle_error(error, context)

        assert result.input_path == Path("test.heic")
        assert result.output_path is None
        assert result.status == ConversionStatus.FAILED
        assert result.error_message is not None
        assert len(result.error_message) > 0

    def test_handle_error_with_processing_time(self):
        """Test that handle_error preserves processing_time from context."""
        handler = ErrorHandler()
        error = ProcessingError("Test error")
        context = {"input_path": Path("test.heic"), "processing_time": 2.5}

        result = handler.handle_error(error, context)

        assert result.processing_time == 2.5

    def test_handle_error_without_processing_time(self):
        """Test that handle_error defaults processing_time to 0.0."""
        handler = ErrorHandler()
        error = InvalidFileError("Test error")
        context = {"input_path": Path("test.heic")}

        result = handler.handle_error(error, context)

        assert result.processing_time == 0.0

    def test_handle_error_without_input_path(self):
        """Test that handle_error handles missing input_path gracefully."""
        handler = ErrorHandler()
        error = InvalidFileError("Test error")
        context = {}

        result = handler.handle_error(error, context)

        assert result.input_path == Path("unknown")
        assert result.status == ConversionStatus.FAILED

    def test_handle_error_with_string_input_path(self):
        """Test that handle_error converts string input_path to Path."""
        handler = ErrorHandler()
        error = InvalidFileError("Test error")
        context = {"input_path": "test.heic"}

        result = handler.handle_error(error, context)

        assert result.input_path == Path("test.heic")
        assert isinstance(result.input_path, Path)

    def test_handle_error_with_non_path_safe_message_generation(self):
        """Test that user message generation is resilient to unusual input_path values."""
        handler = ErrorHandler()
        error = InvalidFileError("Invalid file")
        context = {"input_path": "bad\0path.heic"}

        result = handler.handle_error(error, context)

        assert result.status == ConversionStatus.FAILED
        assert result.error_message is not None

    def test_handle_error_logs_error(self):
        """Test that handle_error logs the error."""
        mock_logger = MagicMock(spec=logging.Logger)
        handler = ErrorHandler(logger=mock_logger)
        error = InvalidFileError("Test error")
        context = {"input_path": Path("test.heic")}

        handler.handle_error(error, context)

        # Verify logging occurred
        mock_logger.error.assert_called_once()

    def test_handle_error_never_raises(self):
        """Test that handle_error never raises exceptions."""
        handler = ErrorHandler()

        # Test with various error types
        errors = [
            InvalidFileError("Test"),
            SecurityError("Test"),
            ProcessingError("Test"),
            ValueError("Test"),
            RuntimeError("Test"),
        ]

        for error in errors:
            context = {"input_path": Path("test.heic")}
            result = handler.handle_error(error, context)
            assert result.status == ConversionStatus.FAILED

    def test_handle_error_message_is_descriptive(self):
        """Test that error messages are descriptive and contain context."""
        handler = ErrorHandler()
        error = InvalidFileError("File not found")
        context = {"input_path": Path("missing.heic")}

        result = handler.handle_error(error, context)

        # Message should be descriptive
        assert len(result.error_message) > 20
        # Message should contain filename
        assert "missing.heic" in result.error_message
        # Message should be actionable
        assert any(
            keyword in result.error_message.lower()
            for keyword in ["check", "please", "try", "ensure"]
        )

    def test_handle_error_with_custom_logger(self):
        """Test that ErrorHandler uses custom logger when provided."""
        custom_logger = logging.getLogger("custom_test_logger")
        handler = ErrorHandler(logger=custom_logger)

        assert handler.logger == custom_logger

    def test_handle_error_creates_default_logger(self):
        """Test that ErrorHandler creates default logger when none provided."""
        handler = ErrorHandler()

        assert handler.logger is not None
        assert isinstance(handler.logger, logging.Logger)
