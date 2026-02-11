"""File system operations with security validation for HEIC converter."""

from __future__ import annotations

import contextlib
import os
from typing import TYPE_CHECKING

from .errors import InvalidFileError, SecurityError
from .models import ValidationResult

if TYPE_CHECKING:
    from pathlib import Path


class FileSystemHandler:
    """Handle file system operations with security validation.

    This class provides secure file operations including:
    - Path traversal prevention
    - File size validation
    - Extension validation
    - Platform-independent path operations
    - Output path generation
    """

    # Maximum file size: 500MB
    MAX_FILE_SIZE = 500 * 1024 * 1024

    # Valid HEIC file extensions
    VALID_EXTENSIONS = {".heic", ".heif"}

    def validate_input_file(self, path: Path) -> ValidationResult:
        """Validate input file exists, is readable, and is HEIC format.

        Args:
            path: Path to the input file

        Returns:
            ValidationResult indicating whether the file is valid
        """
        # Resolve path to prevent directory traversal
        try:
            resolved_path = path.resolve(strict=False)
        except (OSError, RuntimeError) as e:
            return ValidationResult(valid=False, error_message=f"Invalid path: {e}")

        # Check for directory traversal attempts
        # If the resolved path tries to escape the current working directory
        # or contains suspicious patterns, reject it
        if ".." in path.parts:
            return ValidationResult(
                valid=False,
                error_message="Path traversal detected: path contains '..'",
            )

        # Check if file exists
        if not resolved_path.exists():
            return ValidationResult(valid=False, error_message=f"File not found: {path}")

        # Check if it's a file (not a directory)
        if not resolved_path.is_file():
            return ValidationResult(valid=False, error_message=f"Path is not a file: {path}")

        # Check if file is readable
        if not os.access(resolved_path, os.R_OK):
            return ValidationResult(valid=False, error_message=f"File is not readable: {path}")

        # Validate file extension
        if resolved_path.suffix.lower() not in self.VALID_EXTENSIONS:
            return ValidationResult(
                valid=False,
                error_message=f"Invalid file extension: {resolved_path.suffix}. "
                f"Expected one of {self.VALID_EXTENSIONS}",
            )

        # Validate file size
        try:
            file_size = resolved_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
                actual_mb = file_size / (1024 * 1024)
                return ValidationResult(
                    valid=False,
                    error_message=f"File too large: {actual_mb:.1f}MB (maximum: {max_mb:.0f}MB)",
                )
        except OSError as e:
            return ValidationResult(valid=False, error_message=f"Cannot read file size: {e}")

        return ValidationResult(valid=True)

    def validate_output_path(self, path: Path, no_overwrite: bool) -> ValidationResult:
        """Validate output path is writable and handle overwrite logic.

        Args:
            path: Path to the output file
            no_overwrite: If True, reject paths where file already exists

        Returns:
            ValidationResult indicating whether the output path is valid
        """
        # Resolve path to prevent directory traversal
        try:
            resolved_path = path.resolve(strict=False)
        except (OSError, RuntimeError) as e:
            return ValidationResult(valid=False, error_message=f"Invalid output path: {e}")

        # Check for directory traversal attempts
        if ".." in path.parts:
            return ValidationResult(
                valid=False,
                error_message="Path traversal detected in output path: contains '..'",
            )

        # Check if file already exists and no_overwrite is set
        if no_overwrite and resolved_path.exists():
            return ValidationResult(
                valid=False,
                error_message=f"Output file already exists: {path}",
            )

        # Check if parent directory exists and is writable
        parent_dir = resolved_path.parent
        if not parent_dir.exists():
            # Parent directory doesn't exist - we'll create it later
            # Check if we can create it by checking grandparent
            try:
                # Try to find an existing ancestor directory
                ancestor = parent_dir
                while not ancestor.exists() and ancestor != ancestor.parent:
                    ancestor = ancestor.parent

                if not os.access(ancestor, os.W_OK):
                    return ValidationResult(
                        valid=False,
                        error_message=f"Cannot create output directory: "
                        f"{parent_dir} (no write permission)",
                    )
            except (OSError, RuntimeError) as e:
                return ValidationResult(
                    valid=False,
                    error_message=f"Cannot validate output directory: {e}",
                )
        else:
            # Parent directory exists, check if it's writable
            if not os.access(parent_dir, os.W_OK):
                return ValidationResult(
                    valid=False,
                    error_message=f"Output directory is not writable: {parent_dir}",
                )

        return ValidationResult(valid=True)

    def read_file(self, path: Path) -> bytes:
        """Read file with security checks.

        Args:
            path: Path to the file to read

        Returns:
            File contents as bytes

        Raises:
            InvalidFileError: If file validation fails
            SecurityError: If security checks fail
        """
        # Validate the file first
        validation = self.validate_input_file(path)
        if not validation.valid:
            error_msg = validation.error_message or "Unknown validation error"
            if "traversal" in error_msg.lower():
                raise SecurityError(error_msg)
            raise InvalidFileError(error_msg)

        # Read the file
        try:
            resolved_path = path.resolve()
            return resolved_path.read_bytes()
        except OSError as e:
            raise InvalidFileError(f"Failed to read file {path}: {e}") from e

    def write_file(self, path: Path, data: bytes) -> None:
        """Write file with security checks.

        Args:
            path: Path to the file to write
            data: Data to write

        Raises:
            SecurityError: If security checks fail
            InvalidFileError: If write operation fails
        """
        # Validate the output path
        validation = self.validate_output_path(path, no_overwrite=False)
        if not validation.valid:
            error_msg = validation.error_message or "Unknown validation error"
            if "traversal" in error_msg.lower():
                raise SecurityError(error_msg)
            raise InvalidFileError(error_msg)

        # Ensure parent directory exists
        try:
            resolved_path = path.resolve(strict=False)
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise InvalidFileError(f"Failed to create output directory: {e}") from e

        # Write the file atomically using a temporary file
        temp_path = resolved_path.with_suffix(resolved_path.suffix + ".tmp")
        try:
            temp_path.write_bytes(data)
            # Atomic rename
            temp_path.replace(resolved_path)
        except OSError as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                with contextlib.suppress(OSError):
                    temp_path.unlink()
            raise InvalidFileError(f"Failed to write file {path}: {e}") from e

    def get_output_path(self, input_path: Path, output_dir: Path | None) -> Path:
        """Generate output path from input path.

        Args:
            input_path: Path to the input HEIC file
            output_dir: Optional output directory (if None, use input directory)

        Returns:
            Path to the output JPG file
        """
        # Change extension from .heic/.heif to .jpg
        output_filename = input_path.stem + ".jpg"

        # Use output directory if specified, otherwise use input directory
        if output_dir is not None:
            return output_dir / output_filename
        else:
            return input_path.parent / output_filename

    def ensure_directory(self, path: Path) -> None:
        """Create directory if it doesn't exist.

        Args:
            path: Path to the directory to create

        Raises:
            InvalidFileError: If directory creation fails
        """
        try:
            resolved_path = path.resolve(strict=False)
            resolved_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise InvalidFileError(f"Failed to create directory {path}: {e}") from e
