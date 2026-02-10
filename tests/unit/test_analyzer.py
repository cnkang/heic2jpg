"""Unit tests for ImageAnalyzer class."""

import numpy as np

from heic_converter.analyzer import ImageAnalyzer
from heic_converter.models import EXIFMetadata


class TestImageAnalyzer:
    """Test suite for ImageAnalyzer class."""

    def test_analyze_returns_valid_metrics(self):
        """Test that analyze returns ImageMetrics with all fields populated."""
        analyzer = ImageAnalyzer()

        # Create a simple test image (100x100 gray)
        image = np.full((100, 100, 3), 128, dtype=np.uint8)

        metrics = analyzer.analyze(image)

        # Verify all fields are present
        assert metrics.exposure_level is not None
        assert metrics.contrast_level is not None
        assert metrics.shadow_clipping_percent is not None
        assert metrics.highlight_clipping_percent is not None
        assert metrics.saturation_level is not None
        assert metrics.sharpness_score is not None
        assert metrics.noise_level is not None
        assert isinstance(metrics.skin_tone_detected, bool)
        assert isinstance(metrics.is_backlit, bool)
        assert isinstance(metrics.is_low_light, bool)

    def test_exposure_calculation_with_bright_image(self):
        """Test exposure calculation with a bright image."""
        analyzer = ImageAnalyzer()

        # Create a bright image (200/255 = 0.78)
        image = np.full((100, 100, 3), 200, dtype=np.uint8)

        metrics = analyzer.analyze(image)

        # Bright image should have positive exposure
        assert metrics.exposure_level > 0.0
        assert -2.0 <= metrics.exposure_level <= 2.0

    def test_exposure_calculation_with_dark_image(self):
        """Test exposure calculation with a dark image."""
        analyzer = ImageAnalyzer()

        # Create a dark image (50/255 = 0.20)
        image = np.full((100, 100, 3), 50, dtype=np.uint8)

        metrics = analyzer.analyze(image)

        # Dark image should have negative exposure
        assert metrics.exposure_level < 0.0
        assert -2.0 <= metrics.exposure_level <= 2.0

    def test_exposure_calculation_with_exif_compensation(self):
        """Test that EXIF exposure compensation affects exposure calculation."""
        analyzer = ImageAnalyzer()

        # Create a mid-tone image
        image = np.full((100, 100, 3), 128, dtype=np.uint8)

        # Without EXIF
        metrics_no_exif = analyzer.analyze(image, exif=None)

        # With positive exposure compensation
        exif_positive = EXIFMetadata(exposure_compensation=1.0)
        metrics_positive = analyzer.analyze(image, exif=exif_positive)

        # With negative exposure compensation
        exif_negative = EXIFMetadata(exposure_compensation=-1.0)
        metrics_negative = analyzer.analyze(image, exif=exif_negative)

        # Positive compensation should increase exposure level
        assert metrics_positive.exposure_level > metrics_no_exif.exposure_level

        # Negative compensation should decrease exposure level
        assert metrics_negative.exposure_level < metrics_no_exif.exposure_level

    def test_contrast_calculation_with_uniform_image(self):
        """Test contrast calculation with a uniform (no contrast) image."""
        analyzer = ImageAnalyzer()

        # Create a uniform image (no contrast)
        image = np.full((100, 100, 3), 128, dtype=np.uint8)

        metrics = analyzer.analyze(image)

        # Uniform image should have very low contrast
        assert metrics.contrast_level < 0.1
        assert 0.0 <= metrics.contrast_level <= 1.0

    def test_contrast_calculation_with_high_contrast_image(self):
        """Test contrast calculation with a high contrast image."""
        analyzer = ImageAnalyzer()

        # Create a checkerboard pattern (high contrast)
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[::2, ::2] = 255  # White squares
        image[1::2, 1::2] = 255  # White squares

        metrics = analyzer.analyze(image)

        # High contrast image should have high contrast level
        assert metrics.contrast_level > 0.5
        assert 0.0 <= metrics.contrast_level <= 1.0

    def test_clipping_detection_with_shadows(self):
        """Test clipping detection with shadow clipping."""
        analyzer = ImageAnalyzer()

        # Create an image with 50% pure black (shadow clipping)
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[50:, :] = 128  # Bottom half is mid-tone

        metrics = analyzer.analyze(image)

        # Should detect significant shadow clipping
        assert metrics.shadow_clipping_percent > 40.0
        assert metrics.shadow_clipping_percent < 60.0
        assert 0.0 <= metrics.shadow_clipping_percent <= 100.0

    def test_clipping_detection_with_highlights(self):
        """Test clipping detection with highlight clipping."""
        analyzer = ImageAnalyzer()

        # Create an image with 50% pure white (highlight clipping)
        image = np.full((100, 100, 3), 255, dtype=np.uint8)
        image[50:, :] = 128  # Bottom half is mid-tone

        metrics = analyzer.analyze(image)

        # Should detect significant highlight clipping
        assert metrics.highlight_clipping_percent > 40.0
        assert metrics.highlight_clipping_percent < 60.0
        assert 0.0 <= metrics.highlight_clipping_percent <= 100.0

    def test_clipping_detection_with_no_clipping(self):
        """Test clipping detection with no clipping."""
        analyzer = ImageAnalyzer()

        # Create an image with mid-tones only (no clipping)
        image = np.full((100, 100, 3), 128, dtype=np.uint8)

        metrics = analyzer.analyze(image)

        # Should detect no clipping
        assert metrics.shadow_clipping_percent == 0.0
        assert metrics.highlight_clipping_percent == 0.0

    def test_backlit_detection_with_backlit_image(self):
        """Test backlit detection with a backlit image."""
        analyzer = ImageAnalyzer()

        # Create a backlit image (bright edges, dark center)
        image = np.full((100, 100, 3), 200, dtype=np.uint8)
        # Dark center region
        image[30:70, 30:70] = 50

        metrics = analyzer.analyze(image)

        # Should detect backlit condition
        assert metrics.is_backlit is True

    def test_backlit_detection_with_normal_image(self):
        """Test backlit detection with a normal image."""
        analyzer = ImageAnalyzer()

        # Create a uniform image (not backlit)
        image = np.full((100, 100, 3), 128, dtype=np.uint8)

        metrics = analyzer.analyze(image)

        # Should not detect backlit condition
        assert metrics.is_backlit is False

    def test_low_light_detection_with_dark_image(self):
        """Test low-light detection with a dark image."""
        analyzer = ImageAnalyzer()

        # Create a very dark image
        image = np.full((100, 100, 3), 30, dtype=np.uint8)

        metrics = analyzer.analyze(image)

        # Should detect low-light condition
        assert metrics.is_low_light is True

    def test_low_light_detection_with_dark_image_and_high_iso(self):
        """Test low-light detection with dark image and high ISO."""
        analyzer = ImageAnalyzer()

        # Create a somewhat dark image
        image = np.full((100, 100, 3), 60, dtype=np.uint8)

        # With high ISO
        exif = EXIFMetadata(iso=1600)
        metrics = analyzer.analyze(image, exif=exif)

        # Should detect low-light condition due to high ISO
        assert metrics.is_low_light is True

    def test_low_light_detection_with_bright_image(self):
        """Test low-light detection with a bright image."""
        analyzer = ImageAnalyzer()

        # Create a bright image
        image = np.full((100, 100, 3), 200, dtype=np.uint8)

        metrics = analyzer.analyze(image)

        # Should not detect low-light condition
        assert metrics.is_low_light is False

    def test_saturation_calculation(self):
        """Test saturation calculation."""
        analyzer = ImageAnalyzer()

        # Create a grayscale image (no saturation)
        gray_image = np.full((100, 100, 3), 128, dtype=np.uint8)

        # Create a saturated image (pure red)
        saturated_image = np.zeros((100, 100, 3), dtype=np.uint8)
        saturated_image[:, :, 0] = 255  # Red channel

        metrics_gray = analyzer.analyze(gray_image)
        metrics_saturated = analyzer.analyze(saturated_image)

        # Grayscale should have lower saturation than saturated image
        assert metrics_gray.saturation_level < metrics_saturated.saturation_level
        assert 0.0 <= metrics_gray.saturation_level <= 2.0
        assert 0.0 <= metrics_saturated.saturation_level <= 2.0

    def test_sharpness_calculation_with_blurry_image(self):
        """Test sharpness calculation with a blurry image."""
        analyzer = ImageAnalyzer()

        # Create a uniform image (very blurry/no edges)
        image = np.full((100, 100, 3), 128, dtype=np.uint8)

        metrics = analyzer.analyze(image)

        # Uniform image should have very low sharpness
        assert metrics.sharpness_score < 0.1
        assert 0.0 <= metrics.sharpness_score <= 1.0

    def test_sharpness_calculation_with_sharp_image(self):
        """Test sharpness calculation with a sharp image."""
        analyzer = ImageAnalyzer()

        # Create a checkerboard pattern (sharp edges)
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[::2, ::2] = 255
        image[1::2, 1::2] = 255

        metrics = analyzer.analyze(image)

        # Sharp image should have higher sharpness
        assert metrics.sharpness_score > 0.1
        assert 0.0 <= metrics.sharpness_score <= 1.0

    def test_noise_estimation_without_exif(self):
        """Test noise estimation without EXIF data."""
        analyzer = ImageAnalyzer()

        # Create a clean image
        clean_image = np.full((100, 100, 3), 128, dtype=np.uint8)

        # Create a noisy image
        rng = np.random.RandomState(42)
        noisy_image = clean_image.copy().astype(np.int16)
        noise = rng.randint(-30, 31, size=noisy_image.shape)
        noisy_image = np.clip(noisy_image + noise, 0, 255).astype(np.uint8)

        metrics_clean = analyzer.analyze(clean_image)
        metrics_noisy = analyzer.analyze(noisy_image)

        # Noisy image should have higher noise level
        assert metrics_noisy.noise_level > metrics_clean.noise_level
        assert 0.0 <= metrics_clean.noise_level <= 1.0
        assert 0.0 <= metrics_noisy.noise_level <= 1.0

    def test_noise_estimation_with_high_iso(self):
        """Test noise estimation with high ISO EXIF data."""
        analyzer = ImageAnalyzer()

        # Create a clean image
        image = np.full((100, 100, 3), 128, dtype=np.uint8)

        # Without EXIF
        metrics_no_exif = analyzer.analyze(image, exif=None)

        # With high ISO
        exif_high_iso = EXIFMetadata(iso=3200)
        metrics_high_iso = analyzer.analyze(image, exif=exif_high_iso)

        # High ISO should increase estimated noise level
        assert metrics_high_iso.noise_level > metrics_no_exif.noise_level

    def test_skin_tone_detection_with_no_skin_tones(self):
        """Test skin tone detection with an image containing no skin tones."""
        analyzer = ImageAnalyzer()

        # Create a blue image (no skin tones)
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[:, :, 2] = 200  # Blue channel

        metrics = analyzer.analyze(image)

        # Should not detect skin tones
        assert metrics.skin_tone_detected is False
        assert metrics.skin_tone_hue_range is None

    def test_skin_tone_detection_with_skin_tones(self):
        """Test skin tone detection with an image containing skin tones."""
        analyzer = ImageAnalyzer()

        # Create an image with skin tone colors (orange/peach hues)
        # Skin tones are typically in the 0-50 degree hue range
        # In RGB, this is reddish-orange colors
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[:, :, 0] = 220  # Red
        image[:, :, 1] = 180  # Green
        image[:, :, 2] = 140  # Blue

        metrics = analyzer.analyze(image)

        # Should detect skin tones
        assert metrics.skin_tone_detected is True
        assert metrics.skin_tone_hue_range is not None

        # Hue range should be in valid range
        min_hue, max_hue = metrics.skin_tone_hue_range
        assert 0.0 <= min_hue <= 360.0
        assert 0.0 <= max_hue <= 360.0
        assert min_hue <= max_hue

    def test_exif_data_preserved_in_metrics(self):
        """Test that EXIF data is preserved in the metrics."""
        analyzer = ImageAnalyzer()

        image = np.full((100, 100, 3), 128, dtype=np.uint8)

        exif = EXIFMetadata(
            iso=800,
            exposure_time=1.0 / 60.0,
            f_number=2.8,
            exposure_compensation=0.5,
        )

        metrics = analyzer.analyze(image, exif=exif)

        # EXIF data should be preserved
        assert metrics.exif_data is exif
        assert metrics.exif_data.iso == 800
        assert metrics.exif_data.exposure_time == 1.0 / 60.0
        assert metrics.exif_data.f_number == 2.8
        assert metrics.exif_data.exposure_compensation == 0.5

    def test_analyze_with_none_exif(self):
        """Test that analyze works correctly with None EXIF data."""
        analyzer = ImageAnalyzer()

        image = np.full((100, 100, 3), 128, dtype=np.uint8)

        metrics = analyzer.analyze(image, exif=None)

        # Should work without errors
        assert metrics.exif_data is None
        assert metrics.exposure_level is not None
        assert metrics.noise_level is not None
        assert isinstance(metrics.is_low_light, bool)

    def test_metrics_within_valid_ranges(self):
        """Test that all metrics are within their valid ranges."""
        analyzer = ImageAnalyzer()

        # Test with various random images
        rng = np.random.RandomState(42)

        for _ in range(10):
            # Generate random image
            image = rng.randint(0, 256, size=(100, 100, 3), dtype=np.uint8)

            metrics = analyzer.analyze(image)

            # Verify all metrics are in valid ranges
            assert -2.0 <= metrics.exposure_level <= 2.0
            assert 0.0 <= metrics.contrast_level <= 1.0
            assert 0.0 <= metrics.shadow_clipping_percent <= 100.0
            assert 0.0 <= metrics.highlight_clipping_percent <= 100.0
            assert 0.0 <= metrics.saturation_level <= 2.0
            assert 0.0 <= metrics.sharpness_score <= 1.0
            assert 0.0 <= metrics.noise_level <= 1.0
            assert isinstance(metrics.skin_tone_detected, bool)
            assert isinstance(metrics.is_backlit, bool)
            assert isinstance(metrics.is_low_light, bool)
