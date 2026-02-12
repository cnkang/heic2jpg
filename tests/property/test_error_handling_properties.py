"""Property-based tests for error handling.

Feature: heic2jpg
"""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from heic2jpg.converter import ImageConverter
from heic2jpg.filesystem import FileSystemHandler
from heic2jpg.models import Config, ConversionStatus, StylePreferences


# Feature: heic2jpg, Property 3: Invalid Input Error Handling
@given(
    file_extension=st.sampled_from([".txt", ".jpg", ".png", ".pdf", ".doc", ".mp4"]),
    file_content=st.binary(min_size=0, max_size=1024),
)
@pytest.mark.property_test
def test_invalid_format_returns_descriptive_error(file_extension: str, file_content: bytes):
    """Property 3: Invalid Input Error Handling.

    **Validates: Requirements 1.4, 1.5**

    For any file that is not a valid HEIC file (wrong format or corrupted),
    the converter should return a descriptive error message without crashing.

    This test verifies that files with wrong extensions are rejected with
    descriptive error messages.
    """
    # Create a temporary file with wrong extension
    with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
        temp_file.write(file_content)
        temp_path = Path(temp_file.name)

    try:
        # Create filesystem handler
        fs_handler = FileSystemHandler()

        # Validate the file - should fail for non-HEIC extensions
        validation_result = fs_handler.validate_input_file(temp_path)

        # Should be invalid
        assert not validation_result.valid, (
            f"File with extension {file_extension} should be rejected"
        )

        # Should have a descriptive error message
        assert validation_result.error_message is not None, "Error message should not be None"
        assert len(validation_result.error_message) > 0, "Error message should not be empty"
        assert "extension" in validation_result.error_message.lower(), (
            f"Error message should mention extension: {validation_result.error_message}"
        )

    finally:
        # Clean up
        if temp_path.exists():
            temp_path.unlink()


# Feature: heic2jpg, Property 3: Invalid Input Error Handling
@given(
    corrupted_content=st.binary(min_size=10, max_size=1024),
)
@pytest.mark.property_test
def test_corrupted_heic_returns_descriptive_error(corrupted_content: bytes):
    """Property 3: Invalid Input Error Handling.

    **Validates: Requirements 1.4, 1.5**

    For any file that is not a valid HEIC file (wrong format or corrupted),
    the converter should return a descriptive error message without crashing.

    This test verifies that corrupted HEIC files (files with .heic extension
    but invalid content) are handled gracefully with descriptive error messages.
    """
    # Create a temporary file with .heic extension but corrupted content
    with tempfile.NamedTemporaryFile(suffix=".heic", delete=False) as temp_file:
        temp_file.write(corrupted_content)
        temp_path = Path(temp_file.name)

    try:
        # Create converter with default config
        config = Config(
            quality=95,
            output_dir=None,
            no_overwrite=False,
            verbose=False,
            parallel_workers=None,
            style_preferences=StylePreferences(),
        )
        converter = ImageConverter(config)

        # Create output path
        output_path = temp_path.with_suffix(".jpg")

        # Try to convert - should fail gracefully
        from heic2jpg.models import OptimizationParams

        params = OptimizationParams(
            exposure_adjustment=0.0,
            contrast_adjustment=1.0,
            shadow_lift=0.0,
            highlight_recovery=0.0,
            saturation_adjustment=1.0,
            sharpness_amount=0.0,
            noise_reduction=0.0,
            skin_tone_protection=False,
        )

        # The converter should not crash - it should return a result
        result = converter.convert(temp_path, output_path, params)

        # Should have failed status
        assert result.status == ConversionStatus.FAILED, (
            "Corrupted HEIC file should result in FAILED status"
        )

        # Should have a descriptive error message
        assert result.error_message is not None, (
            "Error message should not be None for corrupted file"
        )
        assert len(result.error_message) > 0, "Error message should not be empty for corrupted file"

        # Error message should be descriptive (contain relevant keywords)
        error_lower = result.error_message.lower()
        assert any(
            keyword in error_lower
            for keyword in ["failed", "error", "invalid", "decode", "conversion"]
        ), f"Error message should be descriptive: {result.error_message}"

    finally:
        # Clean up
        if temp_path.exists():
            temp_path.unlink()
        if output_path.exists():
            output_path.unlink()


# Feature: heic2jpg, Property 3: Invalid Input Error Handling
@given(
    file_size=st.integers(min_value=0, max_value=100),
)
@pytest.mark.property_test
def test_empty_or_tiny_heic_returns_descriptive_error(file_size: int):
    """Property 3: Invalid Input Error Handling.

    **Validates: Requirements 1.4, 1.5**

    For any file that is not a valid HEIC file (wrong format or corrupted),
    the converter should return a descriptive error message without crashing.

    This test verifies that empty or very small HEIC files (which cannot be
    valid HEIC images) are handled gracefully with descriptive error messages.
    """
    # Create a temporary file with .heic extension but tiny/empty content
    with tempfile.NamedTemporaryFile(suffix=".heic", delete=False) as temp_file:
        # Write minimal content (not a valid HEIC)
        temp_file.write(b"X" * file_size)
        temp_path = Path(temp_file.name)

    try:
        # Create converter with default config
        config = Config(
            quality=95,
            output_dir=None,
            no_overwrite=False,
            verbose=False,
            parallel_workers=None,
            style_preferences=StylePreferences(),
        )
        converter = ImageConverter(config)

        # Create output path
        output_path = temp_path.with_suffix(".jpg")

        # Try to convert - should fail gracefully
        from heic2jpg.models import OptimizationParams

        params = OptimizationParams(
            exposure_adjustment=0.0,
            contrast_adjustment=1.0,
            shadow_lift=0.0,
            highlight_recovery=0.0,
            saturation_adjustment=1.0,
            sharpness_amount=0.0,
            noise_reduction=0.0,
            skin_tone_protection=False,
        )

        # The converter should not crash - it should return a result
        result = converter.convert(temp_path, output_path, params)

        # Should have failed status
        assert result.status == ConversionStatus.FAILED, (
            f"Empty/tiny HEIC file ({file_size} bytes) should result in FAILED status"
        )

        # Should have a descriptive error message
        assert result.error_message is not None, (
            "Error message should not be None for empty/tiny file"
        )
        assert len(result.error_message) > 0, (
            "Error message should not be empty for empty/tiny file"
        )

        # Error message should be in English and descriptive
        error_lower = result.error_message.lower()
        assert any(
            keyword in error_lower
            for keyword in ["failed", "error", "invalid", "decode", "conversion"]
        ), f"Error message should be descriptive: {result.error_message}"

    finally:
        # Clean up
        if temp_path.exists():
            temp_path.unlink()
        if output_path.exists():
            output_path.unlink()


# Feature: heic2jpg, Property 3: Invalid Input Error Handling
@pytest.mark.property_test
def test_nonexistent_file_returns_descriptive_error():
    """Property 3: Invalid Input Error Handling.

    **Validates: Requirements 1.4, 1.5**

    For any file that is not a valid HEIC file (wrong format or corrupted),
    the converter should return a descriptive error message without crashing.

    This test verifies that attempting to convert a non-existent file
    is handled gracefully with a descriptive error message.
    """
    # Create a path to a file that doesn't exist
    nonexistent_path = Path("/tmp/nonexistent_file_12345.heic")

    # Ensure it doesn't exist
    if nonexistent_path.exists():
        nonexistent_path.unlink()

    # Create filesystem handler
    fs_handler = FileSystemHandler()

    # Validate the file - should fail
    validation_result = fs_handler.validate_input_file(nonexistent_path)

    # Should be invalid
    assert not validation_result.valid, "Non-existent file should be rejected"

    # Should have a descriptive error message
    assert validation_result.error_message is not None, (
        "Error message should not be None for non-existent file"
    )
    assert len(validation_result.error_message) > 0, (
        "Error message should not be empty for non-existent file"
    )

    # Error message should mention the file not being found
    error_lower = validation_result.error_message.lower()
    assert "not found" in error_lower or "does not exist" in error_lower, (
        f"Error message should mention file not found: {validation_result.error_message}"
    )


# Feature: heic2jpg, Property 13: Descriptive Error Messages
@given(
    error_type=st.sampled_from(
        [
            "invalid_file",
            "security",
            "processing",
            "configuration",
        ]
    ),
    filename=st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="._-",
        ),
        min_size=1,
        max_size=50,
    ).map(lambda s: s + ".heic"),
)
@pytest.mark.property_test
def test_error_messages_are_descriptive(error_type: str, filename: str):
    """Property 13: Descriptive Error Messages.

    **Validates: Requirements 16.1**

    For any error condition, the error message should be non-empty,
    contain relevant context (e.g., filename), and describe the problem clearly.

    This test verifies that error messages generated by the ErrorHandler
    meet the descriptive requirements across different error types.
    """
    from heic2jpg.errors import (
        ConversionError,
        ErrorHandler,
        InvalidFileError,
        ProcessingError,
        SecurityError,
    )

    # Create error handler
    error_handler = ErrorHandler()

    # Create appropriate error based on type
    if error_type == "invalid_file":
        error = InvalidFileError(f"Invalid file format: {filename}")
    elif error_type == "security":
        error = SecurityError(f"Path traversal detected in {filename}")
    elif error_type == "processing":
        error = ProcessingError(f"Failed to process {filename}")
    elif error_type == "configuration":
        error = ValueError(f"Invalid configuration for {filename}")
    else:
        error = ConversionError(f"Unknown error with {filename}")

    # Create context with filename
    context = {
        "input_path": Path(filename),
        "operation": "conversion",
    }

    # Handle the error
    result = error_handler.handle_error(error, context)

    # Verify error message is non-empty
    assert result.error_message is not None, "Error message should not be None"
    assert len(result.error_message) > 0, "Error message should not be empty"

    # Verify error message contains relevant context (filename)
    # The filename might be transformed (e.g., just the basename), so check for the base name
    base_filename = Path(filename).name
    assert base_filename in result.error_message or "unknown" in result.error_message.lower(), (
        f"Error message should contain filename context. "
        f"Expected '{base_filename}' in message: {result.error_message}"
    )

    # Verify error message describes the problem clearly
    # It should contain descriptive keywords related to the error
    error_lower = result.error_message.lower()
    descriptive_keywords = [
        "error",
        "failed",
        "invalid",
        "security",
        "processing",
        "configuration",
        "not found",
        "corrupted",
        "format",
        "permission",
        "access",
        "conversion",
    ]
    has_descriptive_keyword = any(keyword in error_lower for keyword in descriptive_keywords)
    assert has_descriptive_keyword, (
        f"Error message should contain descriptive keywords. Message: {result.error_message}"
    )

    # Verify the message is in English (contains common English words)
    # This is a basic check - we look for common English words
    english_indicators = [
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "file",
        "error",
        "failed",
        "invalid",
        "not",
        "cannot",
        "unable",
    ]
    has_english = any(word in error_lower for word in english_indicators)
    assert has_english, f"Error message should be in English. Message: {result.error_message}"


# Feature: heic2jpg, Property 13: Descriptive Error Messages
@given(
    operation=st.sampled_from(["conversion", "validation", "analysis", "optimization"]),
    error_message=st.text(min_size=5, max_size=100),
)
@pytest.mark.property_test
def test_conversion_result_error_messages_are_descriptive(operation: str, error_message: str):
    """Property 13: Descriptive Error Messages.

    **Validates: Requirements 16.1**

    For any error condition, the error message should be non-empty,
    contain relevant context (e.g., filename), and describe the problem clearly.

    This test verifies that ConversionResult objects with errors
    contain descriptive error messages.
    """
    from heic2jpg.errors import ErrorHandler, ProcessingError

    # Create error handler
    error_handler = ErrorHandler()

    # Create a processing error with the given message
    error = ProcessingError(error_message)

    # Create context
    test_filename = "test_image.heic"
    context = {
        "input_path": Path(test_filename),
        "operation": operation,
    }

    # Handle the error
    result = error_handler.handle_error(error, context)

    # Verify the result has failed status
    assert result.status == ConversionStatus.FAILED, "Error handling should result in FAILED status"

    # Verify error message is non-empty
    assert result.error_message is not None, "Error message should not be None"
    assert len(result.error_message) > 0, "Error message should not be empty"

    # Verify error message contains context
    # Should contain either the filename or the operation
    message_lower = result.error_message.lower()
    has_context = (
        test_filename in result.error_message
        or operation in message_lower
        or "test_image" in message_lower
    )
    assert has_context, (
        f"Error message should contain context (filename or operation). "
        f"Message: {result.error_message}"
    )


# Feature: heic2jpg, Property 13: Descriptive Error Messages
@pytest.mark.property_test
def test_filesystem_validation_errors_are_descriptive():
    """Property 13: Descriptive Error Messages.

    **Validates: Requirements 16.1**

    For any error condition, the error message should be non-empty,
    contain relevant context (e.g., filename), and describe the problem clearly.

    This test verifies that filesystem validation errors contain
    descriptive error messages with relevant context.
    """
    from heic2jpg.filesystem import FileSystemHandler

    fs_handler = FileSystemHandler()

    # Test various error conditions
    test_cases = [
        # Non-existent file
        (Path("/tmp/nonexistent_test_file_xyz.heic"), "not found"),
        # Wrong extension
        (Path(__file__).with_suffix(".txt"), "extension"),
    ]

    for test_path, expected_keyword in test_cases:
        # For wrong extension test, create a temporary file
        if expected_keyword == "extension":
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
                temp_file.write(b"test content")
                test_path = Path(temp_file.name)

        try:
            # Validate the file
            validation_result = fs_handler.validate_input_file(test_path)

            # Should be invalid
            assert not validation_result.valid, f"Validation should fail for {test_path}"

            # Should have a descriptive error message
            assert validation_result.error_message is not None, (
                f"Error message should not be None for {test_path}"
            )
            assert len(validation_result.error_message) > 0, (
                f"Error message should not be empty for {test_path}"
            )

            # Should contain the expected keyword
            error_lower = validation_result.error_message.lower()
            assert expected_keyword in error_lower, (
                f"Error message should contain '{expected_keyword}'. "
                f"Message: {validation_result.error_message}"
            )

            # Should contain filename context
            filename = test_path.name
            assert filename in validation_result.error_message or "file" in error_lower, (
                f"Error message should contain filename context. "
                f"Message: {validation_result.error_message}"
            )

        finally:
            # Clean up temporary file if created
            if expected_keyword == "extension" and test_path.exists():
                test_path.unlink()
