"""Unit tests for configuration handling."""

from pathlib import Path

import pytest

from heic_converter.config import create_config, get_quality_from_env
from heic_converter.models import Config, StylePreferences


class TestGetQualityFromEnv:
    """Tests for get_quality_from_env function."""

    def test_returns_none_when_env_var_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that None is returned when HEIC_QUALITY is not set."""
        monkeypatch.delenv("HEIC_QUALITY", raising=False)
        assert get_quality_from_env() is None

    def test_returns_valid_quality_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that valid quality value is returned from environment."""
        monkeypatch.setenv("HEIC_QUALITY", "85")
        assert get_quality_from_env() == 85

    def test_returns_none_for_invalid_quality_below_range(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that None is returned for quality below 0."""
        monkeypatch.setenv("HEIC_QUALITY", "-1")
        assert get_quality_from_env() is None

    def test_returns_none_for_invalid_quality_above_range(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that None is returned for quality above 100."""
        monkeypatch.setenv("HEIC_QUALITY", "101")
        assert get_quality_from_env() is None

    def test_returns_none_for_non_integer_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that None is returned for non-integer values."""
        monkeypatch.setenv("HEIC_QUALITY", "not_a_number")
        assert get_quality_from_env() is None

    def test_returns_quality_at_lower_bound(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that quality 0 is valid."""
        monkeypatch.setenv("HEIC_QUALITY", "0")
        assert get_quality_from_env() == 0

    def test_returns_quality_at_upper_bound(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that quality 100 is valid."""
        monkeypatch.setenv("HEIC_QUALITY", "100")
        assert get_quality_from_env() == 100


class TestCreateConfig:
    """Tests for create_config function."""

    def test_uses_default_quality_when_no_quality_provided(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that default quality (100) is used when no quality is provided.

        Validates: Requirements 2.1
        """
        monkeypatch.delenv("HEIC_QUALITY", raising=False)
        config = create_config()
        assert config.quality == 100

    def test_uses_explicit_quality_when_provided(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that explicit quality parameter takes precedence.

        Validates: Requirements 2.2
        """
        monkeypatch.setenv("HEIC_QUALITY", "80")
        config = create_config(quality=95)
        assert config.quality == 95

    def test_uses_env_quality_when_no_explicit_quality(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that environment variable is used when no explicit quality.

        Validates: Requirements 2.3
        """
        monkeypatch.setenv("HEIC_QUALITY", "75")
        config = create_config()
        assert config.quality == 75

    def test_falls_back_to_default_on_invalid_explicit_quality(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fallback to default when explicit quality is invalid.

        Validates: Requirements 2.5
        """
        monkeypatch.delenv("HEIC_QUALITY", raising=False)
        config = create_config(quality=150)
        assert config.quality == 100

    def test_falls_back_to_env_on_invalid_explicit_quality(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fallback to environment when explicit quality is invalid.

        Validates: Requirements 2.3, 2.5
        """
        monkeypatch.setenv("HEIC_QUALITY", "90")
        config = create_config(quality=-5)
        assert config.quality == 90

    def test_falls_back_to_default_on_invalid_env_quality(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fallback to default when environment quality is invalid.

        Validates: Requirements 2.5
        """
        monkeypatch.setenv("HEIC_QUALITY", "200")
        config = create_config()
        assert config.quality == 100

    def test_quality_priority_explicit_over_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that explicit quality takes priority over environment.

        Validates: Requirements 2.2, 2.3
        """
        monkeypatch.setenv("HEIC_QUALITY", "50")
        config = create_config(quality=70)
        assert config.quality == 70

    def test_quality_priority_env_over_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that environment quality takes priority over default.

        Validates: Requirements 2.3
        """
        monkeypatch.setenv("HEIC_QUALITY", "60")
        config = create_config()
        assert config.quality == 60

    def test_validates_quality_range(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that quality is validated to be in 0-100 range.

        Validates: Requirements 2.4
        """
        monkeypatch.delenv("HEIC_QUALITY", raising=False)
        # Valid quality values should work
        config = create_config(quality=0)
        assert config.quality == 0

        config = create_config(quality=100)
        assert config.quality == 100

        config = create_config(quality=50)
        assert config.quality == 50

    def test_creates_config_with_all_parameters(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that all config parameters are properly set."""
        monkeypatch.delenv("HEIC_QUALITY", raising=False)
        output_dir = Path("/tmp/output")
        style_prefs = StylePreferences(
            natural_appearance=False,
            preserve_highlights=False,
            stable_skin_tones=False,
            avoid_filter_look=False,
        )

        config = create_config(
            quality=85,
            output_dir=output_dir,
            no_overwrite=True,
            verbose=True,
            parallel_workers=4,
            style_preferences=style_prefs,
        )

        assert config.quality == 85
        assert config.output_dir == output_dir
        assert config.no_overwrite is True
        assert config.verbose is True
        assert config.parallel_workers == 4
        assert config.style_preferences == style_prefs

    def test_creates_default_style_preferences_when_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that default StylePreferences is created when None is provided."""
        monkeypatch.delenv("HEIC_QUALITY", raising=False)
        config = create_config()

        assert config.style_preferences.natural_appearance is True
        assert config.style_preferences.preserve_highlights is True
        assert config.style_preferences.stable_skin_tones is True
        assert config.style_preferences.avoid_filter_look is True


class TestQualityValidation:
    """Tests for quality validation in Config model."""

    def test_config_validates_quality_in_post_init(self) -> None:
        """Test that Config validates quality in __post_init__.

        Validates: Requirements 2.4
        """
        # Valid quality should work
        config = Config(quality=50)
        assert config.quality == 50

        # Invalid quality should raise ValueError
        with pytest.raises(ValueError, match="Quality must be between 0 and 100"):
            Config(quality=-1)

        with pytest.raises(ValueError, match="Quality must be between 0 and 100"):
            Config(quality=101)

    def test_config_accepts_boundary_quality_values(self) -> None:
        """Test that Config accepts quality at boundaries (0 and 100).

        Validates: Requirements 2.4
        """
        config_min = Config(quality=0)
        assert config_min.quality == 0

        config_max = Config(quality=100)
        assert config_max.quality == 100
