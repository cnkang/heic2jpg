"""Property-based tests for OptimizationParamGenerator class.

These tests validate universal properties that should hold across all inputs.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from heic_converter.models import (
    EXIFMetadata,
    ImageMetrics,
    StylePreferences,
)
from heic_converter.optimizer import OptimizationParamGenerator


# Custom strategies for generating test data
@st.composite
def image_metrics(draw):
    """Generate random ImageMetrics for testing.

    Args:
        draw: Hypothesis draw function

    Returns:
        ImageMetrics with random but valid values
    """
    # Generate EXIF metadata (optional)
    has_exif = draw(st.booleans())
    exif = None
    if has_exif:
        exif = EXIFMetadata(
            iso=draw(st.one_of(st.none(), st.integers(min_value=100, max_value=6400))),
            exposure_time=draw(st.one_of(st.none(), st.floats(min_value=0.0001, max_value=1.0))),
            f_number=draw(st.one_of(st.none(), st.floats(min_value=1.4, max_value=22.0))),
            exposure_compensation=draw(
                st.one_of(st.none(), st.floats(min_value=-2.0, max_value=2.0))
            ),
            flash_fired=draw(st.one_of(st.none(), st.booleans())),
            scene_type=draw(
                st.one_of(
                    st.none(), st.sampled_from(["standard", "landscape", "portrait", "night"])
                )
            ),
            brightness_value=draw(st.one_of(st.none(), st.floats(min_value=-5.0, max_value=10.0))),
            metering_mode=draw(
                st.one_of(
                    st.none(),
                    st.sampled_from(["average", "center-weighted-average", "spot", "pattern"]),
                )
            ),
        )

    # Generate skin tone hue range if detected
    skin_tone_detected = draw(st.booleans())
    skin_tone_hue_range = None
    if skin_tone_detected:
        min_hue = draw(st.floats(min_value=0.0, max_value=50.0))
        max_hue = draw(st.floats(min_value=min_hue, max_value=50.0))
        skin_tone_hue_range = (min_hue, max_hue)

    return ImageMetrics(
        exposure_level=draw(st.floats(min_value=-2.0, max_value=2.0)),
        contrast_level=draw(st.floats(min_value=0.0, max_value=1.0)),
        shadow_clipping_percent=draw(st.floats(min_value=0.0, max_value=100.0)),
        highlight_clipping_percent=draw(st.floats(min_value=0.0, max_value=100.0)),
        saturation_level=draw(st.floats(min_value=0.0, max_value=2.0)),
        sharpness_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        noise_level=draw(st.floats(min_value=0.0, max_value=1.0)),
        skin_tone_detected=skin_tone_detected,
        skin_tone_hue_range=skin_tone_hue_range,
        is_backlit=draw(st.booleans()),
        is_low_light=draw(st.booleans()),
        exif_data=exif,
    )


@st.composite
def varied_image_metrics(draw):
    """Generate a list of ImageMetrics with intentionally varied characteristics.

    This ensures we get metrics that differ from each other to test
    per-image optimization.
    """
    # Generate 2-5 metrics with different exposure levels
    num_metrics = draw(st.integers(min_value=2, max_value=5))

    metrics_list = []
    for i in range(num_metrics):
        # Ensure different exposure levels
        exposure_level = draw(st.floats(min_value=-2.0 + i * 0.5, max_value=-1.5 + i * 0.5))

        # Vary other characteristics too
        has_exif = draw(st.booleans())
        exif = None
        if has_exif:
            # Vary ISO across images
            iso = draw(st.sampled_from([100, 400, 800, 1600, 3200]))
            exif = EXIFMetadata(
                iso=iso,
                exposure_time=draw(
                    st.one_of(st.none(), st.floats(min_value=0.0001, max_value=1.0))
                ),
                f_number=draw(st.one_of(st.none(), st.floats(min_value=1.4, max_value=22.0))),
                exposure_compensation=draw(
                    st.one_of(st.none(), st.floats(min_value=-2.0, max_value=2.0))
                ),
                flash_fired=draw(st.one_of(st.none(), st.booleans())),
                scene_type=draw(
                    st.one_of(
                        st.none(), st.sampled_from(["standard", "landscape", "portrait", "night"])
                    )
                ),
                brightness_value=draw(
                    st.one_of(st.none(), st.floats(min_value=-5.0, max_value=10.0))
                ),
                metering_mode=draw(
                    st.one_of(
                        st.none(),
                        st.sampled_from(["average", "center-weighted-average", "spot", "pattern"]),
                    )
                ),
            )

        skin_tone_detected = draw(st.booleans())
        skin_tone_hue_range = None
        if skin_tone_detected:
            min_hue = draw(st.floats(min_value=0.0, max_value=50.0))
            max_hue = draw(st.floats(min_value=min_hue, max_value=50.0))
            skin_tone_hue_range = (min_hue, max_hue)

        metrics = ImageMetrics(
            exposure_level=exposure_level,
            contrast_level=draw(st.floats(min_value=0.0, max_value=1.0)),
            shadow_clipping_percent=draw(st.floats(min_value=0.0, max_value=100.0)),
            highlight_clipping_percent=draw(st.floats(min_value=0.0, max_value=100.0)),
            saturation_level=draw(st.floats(min_value=0.0, max_value=2.0)),
            sharpness_score=draw(st.floats(min_value=0.0, max_value=1.0)),
            noise_level=draw(st.floats(min_value=0.0, max_value=1.0)),
            skin_tone_detected=skin_tone_detected,
            skin_tone_hue_range=skin_tone_hue_range,
            is_backlit=draw(st.booleans()),
            is_low_light=draw(st.booleans()),
            exif_data=exif,
        )
        metrics_list.append(metrics)

    return metrics_list


@st.composite
def style_preferences(draw):
    """Generate random StylePreferences."""
    return StylePreferences(
        natural_appearance=draw(st.booleans()),
        preserve_highlights=draw(st.booleans()),
        stable_skin_tones=draw(st.booleans()),
        avoid_filter_look=draw(st.booleans()),
    )


# Feature: heic-to-jpg-converter, Property 23: Per-Image Optimization Parameters
@given(
    metrics_list=varied_image_metrics(),
    style_prefs=style_preferences(),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_per_image_optimization_parameters(metrics_list, style_prefs):
    """Property 23: Per-Image Optimization Parameters

    **Validates: Requirements 19.7**

    For any batch of images with different analysis metrics, each image should
    receive different optimization parameters rather than shared batch-wide parameters.
    """
    generator = OptimizationParamGenerator(style_prefs)

    # Generate optimization parameters for all metrics
    params_list = []
    for metrics in metrics_list:
        params = generator.generate(metrics)
        params_list.append(params)

    # Verify that we got parameters for all metrics
    assert len(params_list) == len(metrics_list), "Should get parameters for each image"

    # Check that at least some parameters differ between images
    # (with varied metrics, parameters should differ)

    # Collect all exposure adjustments
    exposure_adjustments = [p.exposure_adjustment for p in params_list]

    # Collect all contrast adjustments
    contrast_adjustments = [p.contrast_adjustment for p in params_list]

    # Collect all noise reduction values
    noise_reductions = [p.noise_reduction for p in params_list]

    # At least one parameter type should show variation across images
    has_exposure_variation = len(set(exposure_adjustments)) > 1
    has_contrast_variation = len(set(contrast_adjustments)) > 1
    has_noise_variation = len(set(noise_reductions)) > 1

    # Only require parameter variation when the generated input metrics actually differ.
    # Hypothesis can still generate identical items in the batch.
    input_metrics_vary = len({repr(metrics) for metrics in metrics_list}) > 1
    if input_metrics_vary:
        assert has_exposure_variation or has_contrast_variation or has_noise_variation, (
            "Images with different metrics should produce different optimization parameters"
        )

    # Verify that each parameter is within valid ranges
    for i, params in enumerate(params_list):
        assert -2.0 <= params.exposure_adjustment <= 2.0, (
            f"Image {i}: Exposure adjustment should be in range [-2.0, 2.0], got {params.exposure_adjustment}"
        )

        assert 0.5 <= params.contrast_adjustment <= 1.5, (
            f"Image {i}: Contrast adjustment should be in range [0.5, 1.5], got {params.contrast_adjustment}"
        )

        assert 0.0 <= params.shadow_lift <= 1.0, (
            f"Image {i}: Shadow lift should be in range [0.0, 1.0], got {params.shadow_lift}"
        )

        assert 0.0 <= params.highlight_recovery <= 1.0, (
            f"Image {i}: Highlight recovery should be in range [0.0, 1.0], got {params.highlight_recovery}"
        )

        assert 0.5 <= params.saturation_adjustment <= 1.5, (
            f"Image {i}: Saturation adjustment should be in range [0.5, 1.5], got {params.saturation_adjustment}"
        )

        assert 0.0 <= params.sharpness_amount <= 2.0, (
            f"Image {i}: Sharpness amount should be in range [0.0, 2.0], got {params.sharpness_amount}"
        )

        assert 0.0 <= params.noise_reduction <= 1.0, (
            f"Image {i}: Noise reduction should be in range [0.0, 1.0], got {params.noise_reduction}"
        )

        # Verify boolean flag is actually boolean
        assert isinstance(params.skin_tone_protection, bool), (
            f"Image {i}: skin_tone_protection should be boolean"
        )

        # If skin tones detected and stable_skin_tones preference is set,
        # skin_tone_protection should be True
        if metrics_list[i].skin_tone_detected and style_prefs.stable_skin_tones:
            assert params.skin_tone_protection is True, (
                f"Image {i}: skin_tone_protection should be True when skin tones detected and stable_skin_tones preference is set"
            )


# Feature: heic-to-jpg-converter, Property 29: EXIF-Informed Noise Reduction
@given(
    metrics=image_metrics(),
    style_prefs=style_preferences(),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_exif_informed_noise_reduction(metrics, style_prefs):
    """Property 29: EXIF-Informed Noise Reduction

    **Validates: Requirements 21.6**

    For any image with EXIF ISO information, the noise reduction strength should be
    proportional to the ISO value (higher ISO = stronger noise reduction).
    """
    generator = OptimizationParamGenerator(style_prefs)

    # Generate optimization parameters
    params = generator.generate(metrics)

    # Verify noise reduction is within valid range
    assert 0.0 <= params.noise_reduction <= 1.0, (
        f"Noise reduction should be in range [0.0, 1.0], got {params.noise_reduction}"
    )

    # If EXIF data with ISO is available, verify noise reduction is influenced by ISO
    if metrics.exif_data and metrics.exif_data.iso is not None:
        iso = metrics.exif_data.iso

        # Create a comparison metrics with higher ISO
        if iso < 3200:  # Only test if we can increase ISO
            higher_iso = min(iso * 2, 6400)

            # Create new EXIF with higher ISO
            higher_iso_exif = EXIFMetadata(
                iso=higher_iso,
                exposure_time=metrics.exif_data.exposure_time,
                f_number=metrics.exif_data.f_number,
                exposure_compensation=metrics.exif_data.exposure_compensation,
                flash_fired=metrics.exif_data.flash_fired,
                scene_type=metrics.exif_data.scene_type,
                brightness_value=metrics.exif_data.brightness_value,
                metering_mode=metrics.exif_data.metering_mode,
            )

            # Create new metrics with higher ISO but same other values
            higher_iso_metrics = ImageMetrics(
                exposure_level=metrics.exposure_level,
                contrast_level=metrics.contrast_level,
                shadow_clipping_percent=metrics.shadow_clipping_percent,
                highlight_clipping_percent=metrics.highlight_clipping_percent,
                saturation_level=metrics.saturation_level,
                sharpness_score=metrics.sharpness_score,
                noise_level=metrics.noise_level,
                skin_tone_detected=metrics.skin_tone_detected,
                skin_tone_hue_range=metrics.skin_tone_hue_range,
                is_backlit=metrics.is_backlit,
                is_low_light=metrics.is_low_light,
                exif_data=higher_iso_exif,
            )

            # Generate parameters for higher ISO
            higher_iso_params = generator.generate(higher_iso_metrics)

            # Higher ISO should result in equal or higher noise reduction
            # (allowing for small floating point differences)
            assert higher_iso_params.noise_reduction >= params.noise_reduction - 0.01, (
                f"Higher ISO ({higher_iso}) should result in equal or higher noise reduction than lower ISO ({iso}). "
                f"Got {higher_iso_params.noise_reduction} vs {params.noise_reduction}"
            )
