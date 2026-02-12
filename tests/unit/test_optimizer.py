"""Unit tests for OptimizationParamGenerator class."""

from heic2jpg.models import (
    EXIFMetadata,
    ImageMetrics,
    StylePreferences,
)
from heic2jpg.optimizer import OptimizationParamGenerator


class TestOptimizationParamGenerator:
    """Test suite for OptimizationParamGenerator class."""

    def test_generate_returns_valid_params(self):
        """Test that generate returns OptimizationParams with all fields populated."""
        generator = OptimizationParamGenerator(StylePreferences())

        # Create test metrics
        metrics = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        params = generator.generate(metrics)

        # Verify all fields are present and within valid ranges
        assert -2.0 <= params.exposure_adjustment <= 2.0
        assert 0.5 <= params.contrast_adjustment <= 1.5
        assert 0.0 <= params.shadow_lift <= 1.0
        assert 0.0 <= params.highlight_recovery <= 1.0
        assert 0.5 <= params.saturation_adjustment <= 1.5
        assert 0.0 <= params.sharpness_amount <= 2.0
        assert 0.0 <= params.noise_reduction <= 1.0
        assert isinstance(params.skin_tone_protection, bool)

    def test_exposure_adjustment_for_underexposed_image(self):
        """Test exposure adjustment for underexposed images."""
        generator = OptimizationParamGenerator(StylePreferences())

        # Create underexposed metrics (negative exposure level)
        metrics = ImageMetrics(
            exposure_level=-1.0,  # Underexposed
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        params = generator.generate(metrics)

        # Should apply positive exposure adjustment to brighten
        assert params.exposure_adjustment > 0.0

    def test_exposure_adjustment_for_overexposed_image(self):
        """Test exposure adjustment for overexposed images."""
        generator = OptimizationParamGenerator(StylePreferences())

        # Create overexposed metrics (positive exposure level)
        metrics = ImageMetrics(
            exposure_level=1.0,  # Overexposed
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        params = generator.generate(metrics)

        # Should apply negative exposure adjustment to darken
        assert params.exposure_adjustment < 0.0

    def test_highlight_recovery_for_overexposed_images(self):
        """Test highlight recovery for overexposed images."""
        generator = OptimizationParamGenerator(StylePreferences(preserve_highlights=True))

        # Create metrics with significant highlight clipping
        metrics = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=15.0,  # Significant clipping
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        params = generator.generate(metrics)

        # Should apply strong highlight recovery
        assert params.highlight_recovery > 0.7

    def test_highlight_recovery_for_no_clipping(self):
        """Test highlight recovery when there's no clipping."""
        generator = OptimizationParamGenerator(StylePreferences(preserve_highlights=True))

        # Create metrics with no highlight clipping
        metrics = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,  # No clipping
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        params = generator.generate(metrics)

        # Should apply no highlight recovery
        assert params.highlight_recovery == 0.0

    def test_shadow_lift_for_backlit_images(self):
        """Test shadow lift for backlit images."""
        generator = OptimizationParamGenerator(StylePreferences())

        # Create backlit metrics
        metrics = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=5.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=True,  # Backlit
            is_low_light=False,
            exif_data=None,
        )

        params = generator.generate(metrics)

        # Backlit images should still receive meaningful shadow lift
        assert params.shadow_lift > 0.1

    def test_shadow_lift_is_limited_for_bright_backlit_images(self):
        """Test that bright backlit images are not over-lifted."""
        generator = OptimizationParamGenerator(StylePreferences())

        metrics = ImageMetrics(
            exposure_level=0.6,  # Already bright
            contrast_level=0.6,
            shadow_clipping_percent=1.0,  # Little clipping
            highlight_clipping_percent=0.2,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=True,
            is_low_light=False,
            exif_data=None,
        )

        params = generator.generate(metrics)

        assert params.shadow_lift < 0.2

    def test_backlit_scene_enables_proactive_highlight_recovery(self):
        """Test proactive highlight recovery for backlit scenes."""
        generator = OptimizationParamGenerator(StylePreferences(preserve_highlights=True))

        metrics = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=2.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=True,
            is_low_light=False,
            exif_data=None,
        )

        params = generator.generate(metrics)

        assert params.highlight_recovery >= 0.1

    def test_shadow_lift_reduced_with_flash(self):
        """Test that shadow lift is reduced when flash was used."""
        generator = OptimizationParamGenerator(StylePreferences())

        # Create backlit metrics without flash
        metrics_no_flash = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=5.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=True,
            is_low_light=False,
            exif_data=None,
        )

        # Create backlit metrics with flash
        metrics_with_flash = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=5.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=True,
            is_low_light=False,
            exif_data=EXIFMetadata(flash_fired=True),
        )

        params_no_flash = generator.generate(metrics_no_flash)
        params_with_flash = generator.generate(metrics_with_flash)

        # Shadow lift should be reduced when flash was used
        assert params_with_flash.shadow_lift < params_no_flash.shadow_lift

    def test_noise_reduction_scaling_with_iso(self):
        """Test noise reduction scaling with ISO."""
        generator = OptimizationParamGenerator(StylePreferences())

        # Create metrics with low ISO
        metrics_low_iso = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
            exif_data=EXIFMetadata(iso=200),
        )

        # Create metrics with high ISO
        metrics_high_iso = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,  # Same measured noise
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
            exif_data=EXIFMetadata(iso=3200),
        )

        params_low_iso = generator.generate(metrics_low_iso)
        params_high_iso = generator.generate(metrics_high_iso)

        # High ISO should result in stronger noise reduction
        assert params_high_iso.noise_reduction > params_low_iso.noise_reduction

    def test_noise_reduction_for_low_light_images(self):
        """Test noise reduction for low-light images."""
        generator = OptimizationParamGenerator(StylePreferences())

        # Create low-light metrics
        metrics_low_light = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.5,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=True,  # Low-light
            exif_data=None,
        )

        # Create normal light metrics
        metrics_normal_light = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.5,  # Same measured noise
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        params_low_light = generator.generate(metrics_low_light)
        params_normal_light = generator.generate(metrics_normal_light)

        # Low-light should result in stronger noise reduction
        assert params_low_light.noise_reduction > params_normal_light.noise_reduction

    def test_skin_tone_protection_enabled(self):
        """Test that skin tone protection is enabled when skin tones detected."""
        generator = OptimizationParamGenerator(StylePreferences(stable_skin_tones=True))

        # Create metrics with skin tones detected
        metrics = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=True,  # Skin tones detected
            skin_tone_hue_range=(10.0, 40.0),
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        params = generator.generate(metrics)

        # Skin tone protection should be enabled
        assert params.skin_tone_protection is True

    def test_skin_tone_protection_disabled_when_no_skin_tones(self):
        """Test that skin tone protection is disabled when no skin tones detected."""
        generator = OptimizationParamGenerator(StylePreferences(stable_skin_tones=True))

        # Create metrics without skin tones
        metrics = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=False,  # No skin tones
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        params = generator.generate(metrics)

        # Skin tone protection should be disabled
        assert params.skin_tone_protection is False

    def test_skin_tone_protection_disabled_by_preference(self):
        """Test that skin tone protection is disabled when preference is False."""
        generator = OptimizationParamGenerator(StylePreferences(stable_skin_tones=False))

        # Create metrics with skin tones detected
        metrics = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=True,  # Skin tones detected
            skin_tone_hue_range=(10.0, 40.0),
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        params = generator.generate(metrics)

        # Skin tone protection should be disabled due to preference
        assert params.skin_tone_protection is False

    def test_conservative_saturation_with_skin_tones(self):
        """Test conservative saturation adjustment with skin tones."""
        generator = OptimizationParamGenerator(StylePreferences(stable_skin_tones=True))

        # Create metrics with skin tones and low saturation
        metrics_with_skin = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=0.7,  # Low saturation
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=True,
            skin_tone_hue_range=(10.0, 40.0),
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        # Create metrics without skin tones and same low saturation
        metrics_without_skin = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=0.7,  # Low saturation
            sharpness_score=0.5,
            noise_level=0.3,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        params_with_skin = generator.generate(metrics_with_skin)
        params_without_skin = generator.generate(metrics_without_skin)

        # Saturation adjustment should be more conservative with skin tones
        # Both should increase saturation, but skin tone version should be more subtle
        assert params_with_skin.saturation_adjustment > 1.0
        assert params_without_skin.saturation_adjustment > 1.0
        assert params_with_skin.saturation_adjustment < params_without_skin.saturation_adjustment

    def test_sharpness_reduced_with_high_noise(self):
        """Test that sharpness is reduced when high noise is present."""
        generator = OptimizationParamGenerator(StylePreferences())

        # Create metrics with low noise and low sharpness
        metrics_low_noise = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.3,  # Low sharpness
            noise_level=0.2,  # Low noise
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        # Create metrics with high noise and low sharpness
        metrics_high_noise = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.6,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.3,  # Low sharpness
            noise_level=0.8,  # High noise
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        params_low_noise = generator.generate(metrics_low_noise)
        params_high_noise = generator.generate(metrics_high_noise)

        # Sharpness should be reduced with high noise
        assert params_high_noise.sharpness_amount < params_low_noise.sharpness_amount

    def test_natural_appearance_reduces_adjustments(self):
        """Test that natural appearance preference reduces adjustment strength."""
        # Generator with natural appearance
        generator_natural = OptimizationParamGenerator(StylePreferences(natural_appearance=True))

        # Generator without natural appearance
        generator_aggressive = OptimizationParamGenerator(
            StylePreferences(natural_appearance=False)
        )

        # Create metrics that need adjustments
        metrics = ImageMetrics(
            exposure_level=-1.0,  # Underexposed
            contrast_level=0.4,  # Low contrast
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=0.7,  # Low saturation
            sharpness_score=0.3,  # Low sharpness
            noise_level=0.3,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
            exif_data=None,
        )

        params_natural = generator_natural.generate(metrics)
        params_aggressive = generator_aggressive.generate(metrics)

        # Natural appearance should result in more subtle adjustments
        assert abs(params_natural.exposure_adjustment) < abs(params_aggressive.exposure_adjustment)
        assert params_natural.sharpness_amount < params_aggressive.sharpness_amount

    def test_all_parameters_within_valid_ranges(self):
        """Test that all parameters are always within valid ranges."""
        generator = OptimizationParamGenerator(StylePreferences())

        # Test with extreme metrics
        extreme_metrics = [
            # Extremely underexposed
            ImageMetrics(
                exposure_level=-2.0,
                contrast_level=0.0,
                shadow_clipping_percent=100.0,
                highlight_clipping_percent=0.0,
                saturation_level=0.0,
                sharpness_score=0.0,
                noise_level=1.0,
                skin_tone_detected=False,
                skin_tone_hue_range=None,
                is_backlit=True,
                is_low_light=True,
                exif_data=EXIFMetadata(iso=6400),
            ),
            # Extremely overexposed
            ImageMetrics(
                exposure_level=2.0,
                contrast_level=1.0,
                shadow_clipping_percent=0.0,
                highlight_clipping_percent=100.0,
                saturation_level=2.0,
                sharpness_score=1.0,
                noise_level=0.0,
                skin_tone_detected=True,
                skin_tone_hue_range=(10.0, 40.0),
                is_backlit=False,
                is_low_light=False,
                exif_data=EXIFMetadata(iso=100),
            ),
        ]

        for metrics in extreme_metrics:
            params = generator.generate(metrics)

            # Verify all parameters are within valid ranges
            assert -2.0 <= params.exposure_adjustment <= 2.0
            assert 0.5 <= params.contrast_adjustment <= 1.5
            assert 0.0 <= params.shadow_lift <= 1.0
            assert 0.0 <= params.highlight_recovery <= 1.0
            assert 0.5 <= params.saturation_adjustment <= 1.5
            assert 0.0 <= params.sharpness_amount <= 2.0
            assert 0.0 <= params.noise_reduction <= 1.0
