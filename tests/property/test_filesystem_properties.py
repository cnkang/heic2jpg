"""Property-based tests for FileSystemHandler class.

These tests validate universal properties that should hold across all inputs.
"""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from heic_converter.filesystem import FileSystemHandler


# Custom strategies for generating test data
@st.composite
def malicious_paths(draw):
    """Generate paths with directory traversal attempts.

    Property 10: Path Traversal Prevention
    For any file path containing directory traversal patterns (e.g., "../", "..\\"),
    the converter should reject it with a security error.

    Note: We use forward slashes which work on all platforms (Windows, macOS, Linux).
    Backslashes are only path separators on Windows.
    """
    # Generate various path traversal patterns that contain ".." as a path component
    # Using forward slashes which work cross-platform
    base_patterns = [
        Path(".."),
        Path("../"),
        Path("../.."),
        Path("../../"),
        Path("./../"),
        Path("../etc/passwd"),
        Path("../../sensitive/data"),
        Path("./../../etc/shadow"),
        Path("subdir/../../../etc/passwd"),
        Path("foo/../bar"),
        Path("../foo"),
    ]

    base_path = draw(st.sampled_from(base_patterns))

    # Add a .heic filename at the end
    filename = draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")), min_size=1, max_size=20
        )
    )

    return base_path / f"{filename}.heic"


# Feature: heic-to-jpg-converter, Property 10: Path Traversal Prevention
@given(path=malicious_paths())
@settings(max_examples=100)
@pytest.mark.property_test
def test_path_traversal_prevention(path):
    """Property 10: Path Traversal Prevention

    **Validates: Requirements 14.1**

    For any file path containing directory traversal patterns (e.g., "../", "..\\"),
    the converter should reject it with a security error.
    """
    # Create a FileSystemHandler instance
    fs_handler = FileSystemHandler()

    # Validate the path
    result = fs_handler.validate_input_file(path)

    # The validation should fail
    assert result.valid is False, f"Path with traversal pattern should be rejected: {path}"

    # The error message should mention traversal
    assert result.error_message is not None
    assert "traversal" in result.error_message.lower(), (
        f"Error message should mention 'traversal': {result.error_message}"
    )


# Feature: heic-to-jpg-converter, Property 11: File Size Validation
@given(
    # Use smaller file sizes for faster testing (just above the limit)
    file_size=st.integers(
        min_value=FileSystemHandler.MAX_FILE_SIZE + 1,
        max_value=FileSystemHandler.MAX_FILE_SIZE + 10 * 1024 * 1024,  # Max 10MB over limit
    )
)
@settings(max_examples=100, deadline=None)  # Disable deadline for file I/O operations
@pytest.mark.property_test
def test_file_size_validation(file_size):
    """Property 11: File Size Validation

    **Validates: Requirements 14.2**

    For any file larger than the maximum allowed size (500MB), the converter should
    reject it with an error before attempting to load it into memory.
    """
    # Create a FileSystemHandler instance
    fs_handler = FileSystemHandler()

    # Create a temporary file with the specified size
    with tempfile.NamedTemporaryFile(suffix=".heic", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
        try:
            # Write data to reach the desired file size
            # Write in chunks to avoid memory issues
            chunk_size = 1024 * 1024  # 1MB chunks
            remaining = file_size
            while remaining > 0:
                write_size = min(chunk_size, remaining)
                tmp_file.write(b"x" * write_size)
                remaining -= write_size

            tmp_file.flush()

            # Validate the file
            result = fs_handler.validate_input_file(tmp_path)

            # The validation should fail
            assert result.valid is False, (
                f"File with size {file_size} bytes should be rejected (max: {fs_handler.MAX_FILE_SIZE})"
            )

            # The error message should mention size
            assert result.error_message is not None
            assert "too large" in result.error_message.lower(), (
                f"Error message should mention 'too large': {result.error_message}"
            )
        finally:
            # Clean up the temporary file
            if tmp_path.exists():
                tmp_path.unlink()


# Feature: heic-to-jpg-converter, Property 27: Platform-Independent Path Handling
@given(
    # Generate various path components
    path_components=st.lists(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
            ),
            min_size=1,
            max_size=20,
        ),
        min_size=1,
        max_size=5,
    )
)
@settings(max_examples=100)
@pytest.mark.property_test
def test_platform_independent_path_handling(path_components):
    """Property 27: Platform-Independent Path Handling

    **Validates: Requirements 20.4**

    For any file path, the converter should handle it correctly using platform-independent
    path operations (pathlib.Path) that work on Windows, macOS, and Linux.
    """
    # Create a FileSystemHandler instance
    fs_handler = FileSystemHandler()

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)

        # Build a path using pathlib (platform-independent)
        # Create nested directories
        current_path = temp_dir
        for component in path_components[:-1]:
            current_path = current_path / component

        # Add the filename with .heic extension
        input_file = current_path / f"{path_components[-1]}.heic"

        # Create the directory structure
        input_file.parent.mkdir(parents=True, exist_ok=True)

        # Create the file
        input_file.write_bytes(b"test content")

        # Validate the file - should work regardless of platform
        result = fs_handler.validate_input_file(input_file)

        # The validation should succeed (file exists, valid extension, valid size)
        assert result.valid is True, f"Platform-independent path should be valid: {input_file}"

        # Test output path generation - should also be platform-independent
        output_path = fs_handler.get_output_path(input_file, output_dir=None)

        # Output path should have .jpg extension
        assert output_path.suffix == ".jpg", (
            f"Output path should have .jpg extension: {output_path}"
        )

        # Output path should be in the same directory as input
        assert output_path.parent == input_file.parent, (
            "Output path should be in same directory as input"
        )

        # Output path should preserve the stem (filename without extension)
        assert output_path.stem == input_file.stem, "Output path should preserve filename stem"

        # Test with output directory
        output_dir = temp_dir / "output"
        output_path_with_dir = fs_handler.get_output_path(input_file, output_dir=output_dir)

        # Output path should be in the specified directory
        assert output_path_with_dir.parent == output_dir, (
            "Output path should be in specified output directory"
        )

        # Output path should still have .jpg extension
        assert output_path_with_dir.suffix == ".jpg", (
            "Output path with directory should have .jpg extension"
        )
