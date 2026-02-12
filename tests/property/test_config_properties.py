"""Property-based tests for configuration handling."""

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from heic_converter.config import create_config, get_quality_from_env
from heic_converter.models import Config

if TYPE_CHECKING:
    from collections.abc import Iterator

    pass


@contextmanager
def env_var(name: str, value: str | None) -> Iterator[None]:
    """Context manager to temporarily set/unset an environment variable."""
    old_value = os.environ.get(name)
    try:
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
        yield
    finally:
        if old_value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = old_value


# Feature: heic2jpg, Property 4: Quality Configuration Acceptance
@given(quality=st.integers(min_value=0, max_value=100))
@settings(max_examples=100)
@pytest.mark.property_test
def test_quality_configuration_acceptance(quality: int) -> None:
    """For any valid quality value (0-100) provided via configuration or environment
    variable, the converter should use that quality level for JPG encoding.

    **Validates: Requirements 2.2, 2.3**
    """
    # Clear environment to test explicit configuration
    with env_var("HEIC_QUALITY", None):
        # Test explicit quality configuration
        config = create_config(quality=quality)
        assert config.quality == quality, (
            f"Expected quality {quality} from explicit config, got {config.quality}"
        )

    # Test environment variable configuration
    with env_var("HEIC_QUALITY", str(quality)):
        config_from_env = create_config()
        assert config_from_env.quality == quality, (
            f"Expected quality {quality} from environment variable, got {config_from_env.quality}"
        )


# Feature: heic2jpg, Property 5: Quality Validation
@given(
    quality=st.one_of(
        st.integers(max_value=-1),  # Below valid range
        st.integers(min_value=101),  # Above valid range
    )
)
@settings(max_examples=100)
@pytest.mark.property_test
def test_quality_validation(quality: int) -> None:
    """For any quality value outside the range 0-100, the converter should reject it
    with an error and fall back to the default quality of 100.

    **Validates: Requirements 2.4, 2.5**
    """
    # Clear environment variable
    with env_var("HEIC_QUALITY", None):
        # Test that invalid explicit quality falls back to default
        config = create_config(quality=quality)
        assert config.quality == 100, (
            f"Expected fallback to default quality 100 for invalid quality {quality}, "
            f"got {config.quality}"
        )

    # Test that invalid environment variable falls back to default
    with env_var("HEIC_QUALITY", str(quality)):
        config_from_env = create_config()
        assert config_from_env.quality == 100, (
            f"Expected fallback to default quality 100 for invalid env quality {quality}, "
            f"got {config_from_env.quality}"
        )

    # Test that Config constructor raises ValueError for invalid quality
    with pytest.raises(ValueError, match="Quality must be between 0 and 100"):
        Config(quality=quality)


# Additional property test: Quality priority order
@given(
    explicit_quality=st.integers(min_value=0, max_value=100),
    env_quality=st.integers(min_value=0, max_value=100),
)
@settings(max_examples=100)
@pytest.mark.property_test
def test_quality_priority_order(explicit_quality: int, env_quality: int) -> None:
    """For any combination of explicit and environment quality values, explicit
    quality should take priority over environment variable.

    **Validates: Requirements 2.2, 2.3**
    """
    # Set environment variable
    with env_var("HEIC_QUALITY", str(env_quality)):
        # Create config with explicit quality
        config = create_config(quality=explicit_quality)

        # Explicit quality should take priority
        assert config.quality == explicit_quality, (
            f"Expected explicit quality {explicit_quality} to take priority over "
            f"environment quality {env_quality}, got {config.quality}"
        )


# Property test: Environment variable parsing robustness
@given(
    invalid_value=st.one_of(
        st.text(min_size=1).filter(
            lambda x: not x.isdigit() and "\x00" not in x
        ),  # Non-numeric strings without null bytes
        st.just(""),  # Empty string
        st.floats().map(str),  # Float values as strings
    )
)
@settings(max_examples=100)
@pytest.mark.property_test
def test_environment_variable_parsing_robustness(invalid_value: str) -> None:
    """For any invalid environment variable value, the converter should handle it
    gracefully and fall back to default quality.

    **Validates: Requirements 2.5**
    """
    with env_var("HEIC_QUALITY", invalid_value):
        # Should not raise an exception
        quality = get_quality_from_env()

        # Should return None for invalid values
        assert quality is None, (
            f"Expected None for invalid environment value '{invalid_value}', got {quality}"
        )

        # Config creation should fall back to default
        config = create_config()
        assert config.quality == 100, (
            f"Expected fallback to default quality 100 for invalid env value "
            f"'{invalid_value}', got {config.quality}"
        )
