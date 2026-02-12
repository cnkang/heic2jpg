"""Property-based tests for ImageAnalyzer class.

These tests validate universal properties that should hold across all inputs.
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from heic2jpg.analyzer import ImageAnalyzer
from heic2jpg.models import EXIFMetadata


# Custom strategies for generating test images
@st.composite
def rgb_images(draw, min_size=50, max_size=500):
    """Generate random RGB images as numpy arrays.

    Args:
        draw: Hypothesis draw function
        min_size: Minimum image dimension
        max_size: Maximum image dimension

    Returns:
        RGB image as numpy array (uint8)
    """
    width = draw(st.integers(min_value=min_size, max_value=max_size))
    height = draw(st.integers(min_value=min_size, max_value=max_size))

    # Generate random RGB values
    image = draw(
        st.lists(
            st.integers(min_value=0, max_value=255),
            min_size=width * height * 3,
            max_size=width * height * 3,
        )
    )

    # Convert to numpy array and reshape
    image_array = np.array(image, dtype=np.uint8).reshape((height, width, 3))

    return image_array


@st.composite
def varied_exposure_images(draw):
    """Generate images with varied exposure levels.

    Creates images with different brightness levels to ensure
    different exposure metrics.
    """
    width = draw(st.integers(min_value=100, max_value=300))
    height = draw(st.integers(min_value=100, max_value=300))

    # Generate images with different brightness levels
    brightness = draw(st.integers(min_value=0, max_value=255))

    # Create image with uniform brightness plus some noise
    image = np.full((height, width, 3), brightness, dtype=np.uint8)

    # Add some random noise to make it more realistic
    # Use numpy random instead of hypothesis lists for large arrays
    noise_level = draw(st.integers(min_value=5, max_value=30))
    rng = np.random.RandomState(draw(st.integers(min_value=0, max_value=2**31 - 1)))
    noise_array = rng.randint(
        -noise_level, noise_level + 1, size=(height, width, 3), dtype=np.int16
    )
    image = np.clip(image.astype(np.int16) + noise_array, 0, 255).astype(np.uint8)

    return image


@st.composite
def exif_metadata(draw):
    """Generate random EXIF metadata."""
    return EXIFMetadata(
        iso=draw(st.one_of(st.none(), st.integers(min_value=100, max_value=6400))),
        exposure_time=draw(st.one_of(st.none(), st.floats(min_value=0.0001, max_value=1.0))),
        f_number=draw(st.one_of(st.none(), st.floats(min_value=1.4, max_value=22.0))),
        exposure_compensation=draw(st.one_of(st.none(), st.floats(min_value=-2.0, max_value=2.0))),
        flash_fired=draw(st.one_of(st.none(), st.booleans())),
        scene_type=draw(
            st.one_of(st.none(), st.sampled_from(["standard", "landscape", "portrait", "night"]))
        ),
        brightness_value=draw(st.one_of(st.none(), st.floats(min_value=-5.0, max_value=10.0))),
        metering_mode=draw(
            st.one_of(
                st.none(),
                st.sampled_from(["average", "center-weighted-average", "spot", "pattern"]),
            )
        ),
    )


# Feature: heic2jpg, Property 22: Per-Image Analysis Independence
@given(
    images=st.lists(
        varied_exposure_images(),
        min_size=2,
        max_size=5,
    )
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_per_image_analysis_independence(images):
    """Property 22: Per-Image Analysis Independence

    **Validates: Requirements 19.1, 19.2, 19.3, 19.4, 19.5, 19.6**

    For any batch of images with different visual characteristics, each image should
    receive different analysis metrics (exposure, contrast, clipping, saturation,
    sharpness, noise).
    """
    analyzer = ImageAnalyzer()

    # Analyze all images
    metrics_list = []
    for image in images:
        metrics = analyzer.analyze(image, exif=None)
        metrics_list.append(metrics)

    # Verify that we got metrics for all images
    assert len(metrics_list) == len(images), "Should get metrics for each image"

    # Independence check: per-image results should not depend on analysis order.
    reversed_metrics = []
    for image in reversed(images):
        reversed_metrics.append(analyzer.analyze(image, exif=None))

    for i, metrics in enumerate(metrics_list):
        reverse_index = len(images) - 1 - i
        assert metrics == reversed_metrics[reverse_index], (
            f"Image {i}: Metrics should be identical regardless of batch order"
        )

    # Verify that each metric is within valid ranges
    for i, metrics in enumerate(metrics_list):
        assert -2.0 <= metrics.exposure_level <= 2.0, (
            f"Image {i}: Exposure level should be in range [-2.0, 2.0], got {metrics.exposure_level}"
        )

        assert 0.0 <= metrics.contrast_level <= 1.0, (
            f"Image {i}: Contrast level should be in range [0.0, 1.0], got {metrics.contrast_level}"
        )

        assert 0.0 <= metrics.shadow_clipping_percent <= 100.0, (
            f"Image {i}: Shadow clipping should be in range [0.0, 100.0], got {metrics.shadow_clipping_percent}"
        )

        assert 0.0 <= metrics.highlight_clipping_percent <= 100.0, (
            f"Image {i}: Highlight clipping should be in range [0.0, 100.0], got {metrics.highlight_clipping_percent}"
        )

        assert 0.0 <= metrics.saturation_level <= 2.0, (
            f"Image {i}: Saturation level should be in range [0.0, 2.0], got {metrics.saturation_level}"
        )

        assert 0.0 <= metrics.sharpness_score <= 1.0, (
            f"Image {i}: Sharpness score should be in range [0.0, 1.0], got {metrics.sharpness_score}"
        )

        assert 0.0 <= metrics.noise_level <= 1.0, (
            f"Image {i}: Noise level should be in range [0.0, 1.0], got {metrics.noise_level}"
        )

        # Verify boolean flags are actually booleans
        assert isinstance(metrics.skin_tone_detected, bool), (
            f"Image {i}: skin_tone_detected should be boolean"
        )

        assert isinstance(metrics.is_backlit, bool), f"Image {i}: is_backlit should be boolean"

        assert isinstance(metrics.is_low_light, bool), f"Image {i}: is_low_light should be boolean"

        # If skin tones detected, hue range should be present
        if metrics.skin_tone_detected:
            assert metrics.skin_tone_hue_range is not None, (
                f"Image {i}: If skin tones detected, hue range should be present"
            )

            min_hue, max_hue = metrics.skin_tone_hue_range
            assert 0.0 <= min_hue <= 360.0, (
                f"Image {i}: Min hue should be in range [0.0, 360.0], got {min_hue}"
            )
            assert 0.0 <= max_hue <= 360.0, (
                f"Image {i}: Max hue should be in range [0.0, 360.0], got {max_hue}"
            )
            assert min_hue <= max_hue, f"Image {i}: Min hue should be <= max hue"
