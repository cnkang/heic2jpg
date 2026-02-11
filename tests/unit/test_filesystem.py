"""Unit tests for FileSystemHandler class."""

import os
import tempfile
from pathlib import Path

import pytest

from heic_converter.errors import InvalidFileError, SecurityError
from heic_converter.filesystem import FileSystemHandler


@pytest.fixture
def fs_handler():
    """Create a FileSystemHandler instance."""
    return FileSystemHandler()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestValidateInputFile:
    """Tests for validate_input_file method."""

    def test_valid_heic_file(self, fs_handler, temp_dir):
        """Test validation of a valid HEIC file."""
        # Create a test HEIC file
        test_file = temp_dir / "test.heic"
        test_file.write_bytes(b"fake heic content")

        result = fs_handler.validate_input_file(test_file)
        assert result.valid is True
        assert result.error_message is None

    def test_valid_heif_file(self, fs_handler, temp_dir):
        """Test validation of a valid HEIF file."""
        # Create a test HEIF file
        test_file = temp_dir / "test.heif"
        test_file.write_bytes(b"fake heif content")

        result = fs_handler.validate_input_file(test_file)
        assert result.valid is True
        assert result.error_message is None

    def test_case_insensitive_extension(self, fs_handler, temp_dir):
        """Test that extension validation is case-insensitive."""
        # Create files with uppercase extensions
        test_file1 = temp_dir / "test.HEIC"
        test_file1.write_bytes(b"fake content")

        result1 = fs_handler.validate_input_file(test_file1)
        assert result1.valid is True

        test_file2 = temp_dir / "test.HeIc"
        test_file2.write_bytes(b"fake content")

        result2 = fs_handler.validate_input_file(test_file2)
        assert result2.valid is True

    def test_file_not_found(self, fs_handler, temp_dir):
        """Test validation fails for non-existent file."""
        test_file = temp_dir / "nonexistent.heic"

        result = fs_handler.validate_input_file(test_file)
        assert result.valid is False
        assert "not found" in result.error_message.lower()

    def test_path_is_directory(self, fs_handler, temp_dir):
        """Test validation fails for directory."""
        test_dir = temp_dir / "test.heic"
        test_dir.mkdir()

        result = fs_handler.validate_input_file(test_dir)
        assert result.valid is False
        assert "not a file" in result.error_message.lower()

    def test_invalid_extension(self, fs_handler, temp_dir):
        """Test validation fails for invalid extension."""
        test_file = temp_dir / "test.jpg"
        test_file.write_bytes(b"fake content")

        result = fs_handler.validate_input_file(test_file)
        assert result.valid is False
        assert "invalid file extension" in result.error_message.lower()

    def test_file_too_large(self, fs_handler, temp_dir):
        """Test validation fails for file exceeding size limit."""
        test_file = temp_dir / "large.heic"
        # Create a file with content larger than our test limit
        large_content = b"x" * 150  # 150 bytes
        test_file.write_bytes(large_content)

        # Temporarily reduce max file size for testing
        original_max = fs_handler.MAX_FILE_SIZE
        fs_handler.MAX_FILE_SIZE = 100  # 100 bytes

        result = fs_handler.validate_input_file(test_file)
        assert result.valid is False
        assert "too large" in result.error_message.lower()

        # Restore original max size
        fs_handler.MAX_FILE_SIZE = original_max

    def test_path_traversal_with_dotdot(self, fs_handler, temp_dir):
        """Test validation fails for path with .. components."""
        # Create a path with .. in it
        test_file = temp_dir / ".." / "test.heic"

        result = fs_handler.validate_input_file(test_file)
        assert result.valid is False
        assert "traversal" in result.error_message.lower()

    def test_unreadable_file(self, fs_handler, temp_dir):
        """Test validation fails for unreadable file."""
        import sys

        # Skip on Windows - chmod doesn't work the same way
        if sys.platform == "win32":
            pytest.skip("Permission tests not reliable on Windows")

        test_file = temp_dir / "unreadable.heic"
        test_file.write_bytes(b"fake content")

        # Remove read permissions
        os.chmod(test_file, 0o000)

        try:
            result = fs_handler.validate_input_file(test_file)
            assert result.valid is False
            assert "not readable" in result.error_message.lower()
        finally:
            # Restore permissions for cleanup
            os.chmod(test_file, 0o644)


class TestValidateOutputPath:
    """Tests for validate_output_path method."""

    def test_valid_output_path(self, fs_handler, temp_dir):
        """Test validation of a valid output path."""
        output_file = temp_dir / "output.jpg"

        result = fs_handler.validate_output_path(output_file, no_overwrite=False)
        assert result.valid is True
        assert result.error_message is None

    def test_output_path_with_no_overwrite_nonexistent(self, fs_handler, temp_dir):
        """Test validation succeeds when file doesn't exist and no_overwrite is True."""
        output_file = temp_dir / "output.jpg"

        result = fs_handler.validate_output_path(output_file, no_overwrite=True)
        assert result.valid is True

    def test_output_path_with_no_overwrite_exists(self, fs_handler, temp_dir):
        """Test validation fails when file exists and no_overwrite is True."""
        output_file = temp_dir / "output.jpg"
        output_file.write_bytes(b"existing content")

        result = fs_handler.validate_output_path(output_file, no_overwrite=True)
        assert result.valid is False
        assert "already exists" in result.error_message.lower()

    def test_output_path_traversal(self, fs_handler, temp_dir):
        """Test validation fails for output path with traversal."""
        output_file = temp_dir / ".." / "output.jpg"

        result = fs_handler.validate_output_path(output_file, no_overwrite=False)
        assert result.valid is False
        assert "traversal" in result.error_message.lower()

    def test_output_path_nonexistent_parent(self, fs_handler, temp_dir):
        """Test validation succeeds for path with non-existent parent directory."""
        output_file = temp_dir / "subdir" / "output.jpg"

        result = fs_handler.validate_output_path(output_file, no_overwrite=False)
        assert result.valid is True

    def test_output_path_unwritable_parent(self, fs_handler, temp_dir):
        """Test validation fails for path with unwritable parent directory."""
        import sys

        # Skip on Windows - chmod doesn't work the same way
        if sys.platform == "win32":
            pytest.skip("Permission tests not reliable on Windows")

        subdir = temp_dir / "subdir"
        subdir.mkdir()
        output_file = subdir / "output.jpg"

        # Remove write permissions from parent directory
        os.chmod(subdir, 0o444)

        try:
            result = fs_handler.validate_output_path(output_file, no_overwrite=False)
            assert result.valid is False
            assert "not writable" in result.error_message.lower()
        finally:
            # Restore permissions for cleanup
            os.chmod(subdir, 0o755)


class TestReadFile:
    """Tests for read_file method."""

    def test_read_valid_file(self, fs_handler, temp_dir):
        """Test reading a valid file."""
        test_file = temp_dir / "test.heic"
        content = b"test content"
        test_file.write_bytes(content)

        result = fs_handler.read_file(test_file)
        assert result == content

    def test_read_nonexistent_file(self, fs_handler, temp_dir):
        """Test reading non-existent file raises InvalidFileError."""
        test_file = temp_dir / "nonexistent.heic"

        with pytest.raises(InvalidFileError) as exc_info:
            fs_handler.read_file(test_file)
        assert "not found" in str(exc_info.value).lower()

    def test_read_file_with_traversal(self, fs_handler, temp_dir):
        """Test reading file with path traversal raises SecurityError."""
        test_file = temp_dir / ".." / "test.heic"

        with pytest.raises(SecurityError) as exc_info:
            fs_handler.read_file(test_file)
        assert "traversal" in str(exc_info.value).lower()

    def test_read_invalid_extension(self, fs_handler, temp_dir):
        """Test reading file with invalid extension raises InvalidFileError."""
        test_file = temp_dir / "test.jpg"
        test_file.write_bytes(b"content")

        with pytest.raises(InvalidFileError) as exc_info:
            fs_handler.read_file(test_file)
        assert "extension" in str(exc_info.value).lower()


class TestWriteFile:
    """Tests for write_file method."""

    def test_write_valid_file(self, fs_handler, temp_dir):
        """Test writing a valid file."""
        output_file = temp_dir / "output.jpg"
        content = b"output content"

        fs_handler.write_file(output_file, content)

        assert output_file.exists()
        assert output_file.read_bytes() == content

    def test_write_creates_parent_directory(self, fs_handler, temp_dir):
        """Test writing file creates parent directory if needed."""
        output_file = temp_dir / "subdir" / "output.jpg"
        content = b"output content"

        fs_handler.write_file(output_file, content)

        assert output_file.exists()
        assert output_file.read_bytes() == content

    def test_write_overwrites_existing_file(self, fs_handler, temp_dir):
        """Test writing file overwrites existing file."""
        output_file = temp_dir / "output.jpg"
        output_file.write_bytes(b"old content")

        new_content = b"new content"
        fs_handler.write_file(output_file, new_content)

        assert output_file.read_bytes() == new_content

    def test_write_with_traversal(self, fs_handler, temp_dir):
        """Test writing file with path traversal raises SecurityError."""
        output_file = temp_dir / ".." / "output.jpg"

        with pytest.raises(SecurityError) as exc_info:
            fs_handler.write_file(output_file, b"content")
        assert "traversal" in str(exc_info.value).lower()


class TestGetOutputPath:
    """Tests for get_output_path method."""

    def test_output_path_same_directory(self, fs_handler):
        """Test output path generation in same directory as input."""
        input_path = Path("/path/to/input.heic")

        output_path = fs_handler.get_output_path(input_path, output_dir=None)

        assert output_path == Path("/path/to/input.jpg")
        assert output_path.parent == input_path.parent
        assert output_path.stem == input_path.stem
        assert output_path.suffix == ".jpg"

    def test_output_path_different_directory(self, fs_handler):
        """Test output path generation in different directory."""
        input_path = Path("/path/to/input.heic")
        output_dir = Path("/output/dir")

        output_path = fs_handler.get_output_path(input_path, output_dir=output_dir)

        assert output_path == Path("/output/dir/input.jpg")
        assert output_path.parent == output_dir
        assert output_path.stem == input_path.stem
        assert output_path.suffix == ".jpg"

    def test_output_path_preserves_filename(self, fs_handler):
        """Test output path preserves input filename (changes extension only)."""
        input_path = Path("/path/to/my_photo_2024.heic")

        output_path = fs_handler.get_output_path(input_path, output_dir=None)

        assert output_path.stem == "my_photo_2024"
        assert output_path.suffix == ".jpg"

    def test_output_path_heif_extension(self, fs_handler):
        """Test output path generation for .heif extension."""
        input_path = Path("/path/to/input.heif")

        output_path = fs_handler.get_output_path(input_path, output_dir=None)

        assert output_path == Path("/path/to/input.jpg")


class TestEnsureDirectory:
    """Tests for ensure_directory method."""

    def test_ensure_directory_creates_new(self, fs_handler, temp_dir):
        """Test ensure_directory creates new directory."""
        new_dir = temp_dir / "newdir"

        fs_handler.ensure_directory(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_directory_creates_nested(self, fs_handler, temp_dir):
        """Test ensure_directory creates nested directories."""
        nested_dir = temp_dir / "level1" / "level2" / "level3"

        fs_handler.ensure_directory(nested_dir)

        assert nested_dir.exists()
        assert nested_dir.is_dir()

    def test_ensure_directory_existing(self, fs_handler, temp_dir):
        """Test ensure_directory succeeds for existing directory."""
        existing_dir = temp_dir / "existing"
        existing_dir.mkdir()

        # Should not raise an error
        fs_handler.ensure_directory(existing_dir)

        assert existing_dir.exists()
        assert existing_dir.is_dir()
