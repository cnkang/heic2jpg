"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_config():
    """Provide a sample configuration for testing."""
    from heic_converter.models import Config, StylePreferences

    return Config(
        quality=95,
        output_dir=None,
        no_overwrite=False,
        verbose=False,
        parallel_workers=None,
        style_preferences=StylePreferences(),
    )


@pytest.fixture
def sample_exif_metadata():
    """Provide sample EXIF metadata for testing."""
    from heic_converter.models import EXIFMetadata

    return EXIFMetadata(
        iso=400,
        exposure_time=1 / 60,
        f_number=2.8,
        exposure_compensation=0.0,
        flash_fired=False,
        scene_type="portrait",
        brightness_value=5.0,
        metering_mode="pattern",
    )


@pytest.fixture
def sample_image_metrics(sample_exif_metadata):
    """Provide sample image metrics for testing."""
    from heic_converter.models import ImageMetrics

    return ImageMetrics(
        exposure_level=0.0,
        contrast_level=0.7,
        shadow_clipping_percent=2.0,
        highlight_clipping_percent=1.0,
        saturation_level=1.0,
        sharpness_score=0.8,
        noise_level=0.2,
        skin_tone_detected=True,
        skin_tone_hue_range=(10.0, 40.0),
        is_backlit=False,
        is_low_light=False,
        exif_data=sample_exif_metadata,
    )


@pytest.fixture
def sample_optimization_params():
    """Provide sample optimization parameters for testing."""
    from heic_converter.models import OptimizationParams

    return OptimizationParams(
        exposure_adjustment=0.0,
        contrast_adjustment=1.0,
        shadow_lift=0.1,
        highlight_recovery=0.2,
        saturation_adjustment=1.0,
        sharpness_amount=0.5,
        noise_reduction=0.3,
        skin_tone_protection=True,
    )
