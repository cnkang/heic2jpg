"""Integration tests for quality configuration."""

import pytest

from heic2jpg.config import create_config


class TestQualityConfigurationIntegration:
    """Integration tests for quality configuration handling."""

    def test_quality_configuration_priority_chain(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test the complete priority chain: explicit > env > default."""
        # Test 1: No explicit quality, no env var -> default (100)
        monkeypatch.delenv("HEIC_QUALITY", raising=False)
        config = create_config()
        assert config.quality == 100

        # Test 2: No explicit quality, valid env var -> env value
        monkeypatch.setenv("HEIC_QUALITY", "85")
        config = create_config()
        assert config.quality == 85

        # Test 3: Explicit quality, valid env var -> explicit value
        config = create_config(quality=70)
        assert config.quality == 70

        # Test 4: Invalid explicit quality, valid env var -> env value
        config = create_config(quality=150)
        assert config.quality == 85

        # Test 5: Invalid explicit quality, invalid env var -> default
        monkeypatch.setenv("HEIC_QUALITY", "200")
        config = create_config(quality=-10)
        assert config.quality == 100

    def test_quality_configuration_with_all_config_options(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that quality configuration works with all other config options."""
        monkeypatch.setenv("HEIC_QUALITY", "90")

        config = create_config(
            output_dir=None,
            no_overwrite=True,
            verbose=True,
            parallel_workers=4,
        )

        assert config.quality == 90
        assert config.no_overwrite is True
        assert config.verbose is True
        assert config.parallel_workers == 4

    def test_environment_variable_isolation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that environment variable changes are properly isolated."""
        # Set initial env var
        monkeypatch.setenv("HEIC_QUALITY", "80")
        config1 = create_config()
        assert config1.quality == 80

        # Change env var
        monkeypatch.setenv("HEIC_QUALITY", "60")
        config2 = create_config()
        assert config2.quality == 60

        # First config should still have original value
        assert config1.quality == 80

        # Remove env var
        monkeypatch.delenv("HEIC_QUALITY")
        config3 = create_config()
        assert config3.quality == 100

    def test_quality_validation_error_messages(self) -> None:
        """Test that quality validation provides clear error messages."""
        from heic2jpg.models import Config

        with pytest.raises(ValueError) as exc_info:
            Config(quality=-1)
        assert "Quality must be between 0 and 100" in str(exc_info.value)
        assert "got -1" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            Config(quality=101)
        assert "Quality must be between 0 and 100" in str(exc_info.value)
        assert "got 101" in str(exc_info.value)
