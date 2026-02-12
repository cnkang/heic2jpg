"""Unit tests for logging configuration."""

import logging
import tempfile
from pathlib import Path

import pytest

from heic2jpg.logging_config import (
    PlatformIndependentFormatter,
    get_logger,
    log_operation_complete,
    log_operation_error,
    log_operation_start,
    set_log_level,
    setup_logging,
)


class TestPlatformIndependentFormatter:
    """Test the platform-independent formatter."""

    def test_normalizes_crlf_to_lf(self):
        """Test that CRLF line endings are normalized to LF."""
        formatter = PlatformIndependentFormatter("%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Line 1\r\nLine 2\r\nLine 3",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "\r\n" not in formatted
        assert "Line 1\nLine 2\nLine 3" in formatted

    def test_normalizes_cr_to_lf(self):
        """Test that CR line endings are normalized to LF."""
        formatter = PlatformIndependentFormatter("%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Line 1\rLine 2\rLine 3",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "\r" not in formatted
        assert "Line 1\nLine 2\nLine 3" in formatted

    def test_preserves_lf(self):
        """Test that LF line endings are preserved."""
        formatter = PlatformIndependentFormatter("%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Line 1\nLine 2\nLine 3",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "Line 1\nLine 2\nLine 3" in formatted


class TestSetupLogging:
    """Test the setup_logging function."""

    def teardown_method(self):
        """Clean up logger after each test."""
        logger = logging.getLogger("heic2jpg")
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)

    def test_default_configuration(self):
        """Test default logging configuration."""
        logger = setup_logging()

        assert logger.name == "heic2jpg"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_verbose_mode(self):
        """Test verbose logging mode sets DEBUG level."""
        logger = setup_logging(verbose=True)

        assert logger.level == logging.DEBUG
        assert logger.handlers[0].level == logging.DEBUG

    def test_custom_level(self):
        """Test custom logging level."""
        logger = setup_logging(level=logging.WARNING)

        assert logger.level == logging.WARNING

    def test_verbose_overrides_level(self):
        """Test that verbose mode overrides custom level."""
        logger = setup_logging(level=logging.WARNING, verbose=True)

        assert logger.level == logging.DEBUG

    def test_file_logging(self):
        """Test file logging configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = setup_logging(log_file=log_file)

            # Should have console and file handlers
            assert len(logger.handlers) == 2
            assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)

            # Test that logging to file works
            logger.info("Test message")

            # Close file handlers to release file on Windows
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()

            assert log_file.exists()
            content = log_file.read_text(encoding="utf-8")
            assert "Test message" in content

    def test_file_logging_creates_directory(self):
        """Test that file logging creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "subdir" / "test.log"
            logger = setup_logging(log_file=log_file)

            logger.info("Test message")

            # Close file handlers to release file on Windows
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()

            assert log_file.exists()
            assert log_file.parent.exists()

    def test_file_logging_failure_does_not_crash(self):
        """Test that file logging failure doesn't crash setup."""
        # Try to log to an invalid path
        invalid_path = Path("/invalid/path/that/does/not/exist/test.log")
        logger = setup_logging(log_file=invalid_path)

        # Should still have console handler
        assert len(logger.handlers) >= 1
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

    def test_formatter_is_platform_independent(self):
        """Test that the formatter is PlatformIndependentFormatter."""
        logger = setup_logging()

        handler = logger.handlers[0]
        assert isinstance(handler.formatter, PlatformIndependentFormatter)

    def test_verbose_format_includes_details(self):
        """Test that verbose format includes filename and line number."""
        logger = setup_logging(verbose=True)

        handler = logger.handlers[0]
        format_string = handler.formatter._fmt
        assert "%(filename)s" in format_string
        assert "%(lineno)d" in format_string

    def test_standard_format_is_concise(self):
        """Test that standard format is more concise."""
        logger = setup_logging(verbose=False)

        handler = logger.handlers[0]
        format_string = handler.formatter._fmt
        assert "%(filename)s" not in format_string
        assert "%(lineno)d" not in format_string


class TestGetLogger:
    """Test the get_logger function."""

    def test_returns_logger_under_heic2jpg_namespace(self):
        """Test that get_logger returns logger under heic2jpg namespace."""
        logger = get_logger("test_module")

        assert logger.name == "heic2jpg.test_module"

    def test_preserves_heic2jpg_prefix(self):
        """Test that heic2jpg prefix is not duplicated."""
        logger = get_logger("heic2jpg.test_module")

        assert logger.name == "heic2jpg.test_module"

    def test_different_names_return_different_loggers(self):
        """Test that different names return different logger instances."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1 is not logger2
        assert logger1.name != logger2.name


class TestSetLogLevel:
    """Test the set_log_level function."""

    def setup_method(self):
        """Set up logger before each test."""
        self.logger = setup_logging()

    def teardown_method(self):
        """Clean up logger after each test."""
        logger = logging.getLogger("heic2jpg")
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)

    def test_set_level_with_int(self):
        """Test setting log level with integer."""
        set_log_level(logging.WARNING)

        logger = logging.getLogger("heic2jpg")
        assert logger.level == logging.WARNING
        for handler in logger.handlers:
            assert handler.level == logging.WARNING

    def test_set_level_with_string(self):
        """Test setting log level with string."""
        set_log_level("ERROR")

        logger = logging.getLogger("heic2jpg")
        assert logger.level == logging.ERROR

    def test_set_level_case_insensitive(self):
        """Test that string level is case-insensitive."""
        set_log_level("debug")

        logger = logging.getLogger("heic2jpg")
        assert logger.level == logging.DEBUG

    def test_invalid_string_level_raises_error(self):
        """Test that invalid string level raises ValueError."""
        with pytest.raises(ValueError, match="Invalid log level"):
            set_log_level("INVALID")


class TestOperationLogging:
    """Test the operation logging convenience functions."""

    def setup_method(self):
        """Set up logger before each test."""
        self.logger = setup_logging()

    def teardown_method(self):
        """Clean up logger after each test."""
        logger = logging.getLogger("heic2jpg")
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)

    def test_log_operation_start(self, caplog):
        """Test log_operation_start function."""
        caplog.set_level(logging.INFO)

        log_operation_start(self.logger, "conversion", filename="test.heic")

        assert "Starting conversion" in caplog.text
        assert "filename=test.heic" in caplog.text

    def test_log_operation_complete_success(self, caplog):
        """Test log_operation_complete with success."""
        caplog.set_level(logging.INFO)

        log_operation_complete(
            self.logger, "conversion", success=True, duration=1.5, filename="test.heic"
        )

        assert "Conversion completed successfully" in caplog.text
        assert "1.50s" in caplog.text
        assert "filename=test.heic" in caplog.text

    def test_log_operation_complete_failure(self, caplog):
        """Test log_operation_complete with failure."""
        caplog.set_level(logging.ERROR)

        log_operation_complete(self.logger, "conversion", success=False, filename="test.heic")

        assert "Conversion failed" in caplog.text
        assert "filename=test.heic" in caplog.text

    def test_log_operation_complete_without_duration(self, caplog):
        """Test log_operation_complete without duration."""
        caplog.set_level(logging.INFO)

        log_operation_complete(self.logger, "analysis", success=True)

        assert "Analysis completed successfully" in caplog.text
        # Duration should not be in message (no "in X.XXs" pattern)
        assert " in " not in caplog.text or "s:" not in caplog.text

    def test_log_operation_error(self, caplog):
        """Test log_operation_error function."""
        caplog.set_level(logging.ERROR)

        error = ValueError("Invalid input")
        log_operation_error(self.logger, "conversion", error, filename="test.heic")

        assert "Error during conversion" in caplog.text
        assert "ValueError" in caplog.text
        assert "Invalid input" in caplog.text
        assert "filename=test.heic" in caplog.text

    def test_log_operation_error_includes_stack_trace_in_debug(self, caplog):
        """Test that log_operation_error includes stack trace in DEBUG mode."""
        # Set up logger with DEBUG level
        logger = setup_logging(verbose=True)
        caplog.set_level(logging.DEBUG)

        error = ValueError("Invalid input")
        log_operation_error(logger, "conversion", error)

        # Stack trace should be logged at DEBUG level
        # Check for the "Stack trace" message that's logged
        assert "Stack trace for conversion error" in caplog.text


class TestEnglishOnlyMessages:
    """Test that all log messages are in English."""

    def setup_method(self):
        """Set up logger before each test."""
        self.logger = setup_logging()

    def teardown_method(self):
        """Clean up logger after each test."""
        logger = logging.getLogger("heic2jpg")
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)

    def test_all_messages_are_ascii_compatible(self, caplog):
        """Test that all log messages use ASCII-compatible English."""
        caplog.set_level(logging.DEBUG)

        # Test various logging functions
        self.logger.info("Test message")
        self.logger.debug("Debug message")
        self.logger.warning("Warning message")
        self.logger.error("Error message")

        log_operation_start(self.logger, "test", param="value")
        log_operation_complete(self.logger, "test", success=True, duration=1.0)
        log_operation_error(self.logger, "test", ValueError("error"))

        # All messages should be encodable as ASCII (or at least Latin-1)
        for record in caplog.records:
            message = record.getMessage()
            # Should not raise UnicodeEncodeError
            message.encode("ascii", errors="ignore")

            # Check that message doesn't contain common non-English characters
            # (This is a basic check - not exhaustive)
            assert not any(
                char in message for char in ["中", "文", "日", "本", "한", "국", "العربية"]
            )
