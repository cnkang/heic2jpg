"""Configuration handling for the HEIC to JPG converter."""

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from .models import Config, StylePreferences


def get_quality_from_env() -> int | None:
    """Get quality setting from environment variable.

    Reads the HEIC_QUALITY environment variable and validates it.
    Returns None if the variable is not set or contains an invalid value.

    Returns:
        Quality value (0-100) if valid, None otherwise
    """
    quality_str = os.getenv("HEIC_QUALITY")
    if quality_str is None:
        return None

    try:
        quality = int(quality_str)
        if 0 <= quality <= 100:
            return quality
        else:
            # Invalid quality value, will fall back to default
            return None
    except ValueError:
        # Not a valid integer, will fall back to default
        return None


def create_config(
    quality: int | None = None,
    output_dir: Path | None = None,
    no_overwrite: bool = False,
    verbose: bool = False,
    parallel_workers: int | None = None,
    style_preferences: StylePreferences | None = None,
) -> Config:
    """Create a Config object with quality from environment variable fallback.

    This function implements the quality configuration priority:
    1. Explicit quality parameter (if provided and valid)
    2. HEIC_QUALITY environment variable (if set and valid)
    3. Default quality (100)

    Args:
        quality: Explicit quality value (0-100), or None to use environment/default
        output_dir: Optional output directory for converted files
        no_overwrite: Skip existing files without prompting
        verbose: Enable verbose logging
        parallel_workers: Number of parallel workers (None = auto-detect)
        style_preferences: Style preferences for optimization

    Returns:
        Config object with quality set according to priority

    Raises:
        ValueError: If the final quality value is invalid (outside 0-100 range)
    """
    # Determine quality with fallback logic
    final_quality: int

    if quality is not None:
        # Explicit quality provided - validate it
        if not 0 <= quality <= 100:
            # Invalid explicit quality - fall back to environment or default
            env_quality = get_quality_from_env()
            final_quality = env_quality if env_quality is not None else 100
        else:
            final_quality = quality
    else:
        # No explicit quality - try environment variable
        env_quality = get_quality_from_env()
        final_quality = env_quality if env_quality is not None else 100

    # Create config with determined quality
    return Config(
        quality=final_quality,
        output_dir=output_dir,
        no_overwrite=no_overwrite,
        verbose=verbose,
        parallel_workers=parallel_workers,
        style_preferences=style_preferences or StylePreferences(),
    )
