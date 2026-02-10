"""Unit tests for core data models."""

from pathlib import Path

import pytest

from heic_converter.models import (
    BatchResults,
    Config,
    ConversionResult,
    ConversionStatus,
    EXIFMetadata,
    ImageMetrics,
    OptimizationParams,
    StylePreferences,
    ValidationResult,
)


class TestConversionStatus:
    """Tests for ConversionStatus enum."""

    def test_enum_values(self):
        """Test that ConversionStatus has the expected values."""
        assert ConversionStatus.SUCCESS.value == "success"
        assert ConversionStatus.FAILED.value == "failed"
        assert ConversionStatus.SKIPPED.value == "skipped"

    def test_enum_members(self):
        """Test that ConversionStatus has exactly three members."""
        assert len(ConversionStatus) == 3
        assert ConversionStatus.SUCCESS in ConversionStatus
        assert ConversionStatus.FAILED in ConversionStatus
        assert ConversionStatus.SKIPPED in ConversionStatus


class TestStylePreferences:
    """Tests for StylePreferences dataclass."""

    def test_default_initialization(self):
        """Test that StylePreferences initializes with correct defaults."""
        prefs = StylePreferences()
        assert prefs.natural_appearance is True
        assert prefs.preserve_highlights is True
        assert prefs.stable_skin_tones is True
        assert prefs.avoid_filter_look is True

    def test_custom_initialization(self):
        """Test that StylePreferences can be initialized with custom values."""
        prefs = StylePreferences(
            natural_appearance=False,
            preserve_highlights=False,
            stable_skin_tones=False,
            avoid_filter_look=False,
        )
        assert prefs.natural_appearance is False
        assert prefs.preserve_highlights is False
        assert prefs.stable_skin_tones is False
        assert prefs.avoid_filter_look is False


class TestConfig:
    """Tests for Config dataclass."""

    def test_default_initialization(self):
        """Test that Config initializes with correct defaults."""
        config = Config()
        assert config.quality == 100
        assert config.output_dir is None
        assert config.no_overwrite is False
        assert config.verbose is False
        assert config.parallel_workers is None
        assert isinstance(config.style_preferences, StylePreferences)

    def test_custom_initialization(self):
        """Test that Config can be initialized with custom values."""
        output_dir = Path("/tmp/output")
        prefs = StylePreferences(natural_appearance=False)
        config = Config(
            quality=95,
            output_dir=output_dir,
            no_overwrite=True,
            verbose=True,
            parallel_workers=4,
            style_preferences=prefs,
        )
        assert config.quality == 95
        assert config.output_dir == output_dir
        assert config.no_overwrite is True
        assert config.verbose is True
        assert config.parallel_workers == 4
        assert config.style_preferences == prefs

    def test_quality_validation_valid(self):
        """Test that valid quality values are accepted."""
        # Test boundary values
        Config(quality=0)
        Config(quality=100)
        Config(quality=50)

    def test_quality_validation_invalid_negative(self):
        """Test that negative quality values raise ValueError."""
        with pytest.raises(ValueError, match="Quality must be between 0 and 100"):
            Config(quality=-1)

    def test_quality_validation_invalid_too_high(self):
        """Test that quality values above 100 raise ValueError."""
        with pytest.raises(ValueError, match="Quality must be between 0 and 100"):
            Config(quality=101)

    def test_parallel_workers_validation_valid(self):
        """Test that valid parallel_workers values are accepted."""
        Config(parallel_workers=1)
        Config(parallel_workers=8)
        Config(parallel_workers=None)

    def test_parallel_workers_validation_invalid(self):
        """Test that invalid parallel_workers values raise ValueError."""
        with pytest.raises(ValueError, match="parallel_workers must be at least 1"):
            Config(parallel_workers=0)
        with pytest.raises(ValueError, match="parallel_workers must be at least 1"):
            Config(parallel_workers=-1)


class TestEXIFMetadata:
    """Tests for EXIFMetadata dataclass."""

    def test_default_initialization(self):
        """Test that EXIFMetadata initializes with all None values."""
        exif = EXIFMetadata()
        assert exif.iso is None
        assert exif.exposure_time is None
        assert exif.f_number is None
        assert exif.exposure_compensation is None
        assert exif.flash_fired is None
        assert exif.scene_type is None
        assert exif.brightness_value is None
        assert exif.metering_mode is None

    def test_custom_initialization(self):
        """Test that EXIFMetadata can be initialized with custom values."""
        exif = EXIFMetadata(
            iso=800,
            exposure_time=1 / 125,
            f_number=1.8,
            exposure_compensation=-0.5,
            flash_fired=True,
            scene_type="night",
            brightness_value=3.5,
            metering_mode="spot",
        )
        assert exif.iso == 800
        assert exif.exposure_time == 1 / 125
        assert exif.f_number == 1.8
        assert exif.exposure_compensation == -0.5
        assert exif.flash_fired is True
        assert exif.scene_type == "night"
        assert exif.brightness_value == 3.5
        assert exif.metering_mode == "spot"


class TestImageMetrics:
    """Tests for ImageMetrics dataclass."""

    def test_initialization(self):
        """Test that ImageMetrics can be initialized with required values."""
        exif = EXIFMetadata(iso=400)
        metrics = ImageMetrics(
            exposure_level=0.5,
            contrast_level=0.7,
            shadow_clipping_percent=2.0,
            highlight_clipping_percent=1.5,
            saturation_level=1.2,
            sharpness_score=0.8,
            noise_level=0.3,
            skin_tone_detected=True,
            skin_tone_hue_range=(15.0, 35.0),
            is_backlit=False,
            is_low_light=True,
            exif_data=exif,
        )
        assert metrics.exposure_level == 0.5
        assert metrics.contrast_level == 0.7
        assert metrics.shadow_clipping_percent == 2.0
        assert metrics.highlight_clipping_percent == 1.5
        assert metrics.saturation_level == 1.2
        assert metrics.sharpness_score == 0.8
        assert metrics.noise_level == 0.3
        assert metrics.skin_tone_detected is True
        assert metrics.skin_tone_hue_range == (15.0, 35.0)
        assert metrics.is_backlit is False
        assert metrics.is_low_light is True
        assert metrics.exif_data == exif

    def test_initialization_without_exif(self):
        """Test that ImageMetrics can be initialized without EXIF data."""
        metrics = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.5,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.1,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
        )
        assert metrics.exif_data is None


class TestOptimizationParams:
    """Tests for OptimizationParams dataclass."""

    def test_initialization(self):
        """Test that OptimizationParams can be initialized with values."""
        params = OptimizationParams(
            exposure_adjustment=0.3,
            contrast_adjustment=1.1,
            shadow_lift=0.2,
            highlight_recovery=0.5,
            saturation_adjustment=0.95,
            sharpness_amount=1.0,
            noise_reduction=0.4,
            skin_tone_protection=True,
        )
        assert params.exposure_adjustment == 0.3
        assert params.contrast_adjustment == 1.1
        assert params.shadow_lift == 0.2
        assert params.highlight_recovery == 0.5
        assert params.saturation_adjustment == 0.95
        assert params.sharpness_amount == 1.0
        assert params.noise_reduction == 0.4
        assert params.skin_tone_protection is True


class TestConversionResult:
    """Tests for ConversionResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful conversion result."""
        input_path = Path("input.heic")
        output_path = Path("output.jpg")
        result = ConversionResult(
            input_path=input_path,
            output_path=output_path,
            status=ConversionStatus.SUCCESS,
            processing_time=1.5,
        )
        assert result.input_path == input_path
        assert result.output_path == output_path
        assert result.status == ConversionStatus.SUCCESS
        assert result.error_message is None
        assert result.metrics is None
        assert result.optimization_params is None
        assert result.processing_time == 1.5

    def test_failed_result(self):
        """Test creating a failed conversion result."""
        input_path = Path("input.heic")
        result = ConversionResult(
            input_path=input_path,
            output_path=None,
            status=ConversionStatus.FAILED,
            error_message="Invalid HEIC file",
            processing_time=0.1,
        )
        assert result.input_path == input_path
        assert result.output_path is None
        assert result.status == ConversionStatus.FAILED
        assert result.error_message == "Invalid HEIC file"
        assert result.processing_time == 0.1

    def test_result_with_metrics_and_params(self):
        """Test creating a result with metrics and optimization params."""
        input_path = Path("input.heic")
        output_path = Path("output.jpg")
        metrics = ImageMetrics(
            exposure_level=0.0,
            contrast_level=0.5,
            shadow_clipping_percent=0.0,
            highlight_clipping_percent=0.0,
            saturation_level=1.0,
            sharpness_score=0.5,
            noise_level=0.1,
            skin_tone_detected=False,
            skin_tone_hue_range=None,
            is_backlit=False,
            is_low_light=False,
        )
        params = OptimizationParams(
            exposure_adjustment=0.0,
            contrast_adjustment=1.0,
            shadow_lift=0.0,
            highlight_recovery=0.0,
            saturation_adjustment=1.0,
            sharpness_amount=0.5,
            noise_reduction=0.1,
            skin_tone_protection=False,
        )
        result = ConversionResult(
            input_path=input_path,
            output_path=output_path,
            status=ConversionStatus.SUCCESS,
            metrics=metrics,
            optimization_params=params,
        )
        assert result.metrics == metrics
        assert result.optimization_params == params


class TestBatchResults:
    """Tests for BatchResults dataclass."""

    def test_initialization(self):
        """Test that BatchResults can be initialized."""
        results = [
            ConversionResult(
                input_path=Path("1.heic"),
                output_path=Path("1.jpg"),
                status=ConversionStatus.SUCCESS,
            ),
            ConversionResult(
                input_path=Path("2.heic"),
                output_path=None,
                status=ConversionStatus.FAILED,
            ),
        ]
        batch = BatchResults(
            results=results,
            total_files=2,
            successful=1,
            failed=1,
            skipped=0,
            total_time=3.5,
        )
        assert batch.results == results
        assert batch.total_files == 2
        assert batch.successful == 1
        assert batch.failed == 1
        assert batch.skipped == 0
        assert batch.total_time == 3.5

    def test_success_rate_calculation(self):
        """Test BatchResults.success_rate() calculation."""
        # Test 100% success rate
        batch = BatchResults(
            results=[],
            total_files=10,
            successful=10,
            failed=0,
            skipped=0,
            total_time=10.0,
        )
        assert batch.success_rate() == 100.0

        # Test 50% success rate
        batch = BatchResults(
            results=[],
            total_files=10,
            successful=5,
            failed=5,
            skipped=0,
            total_time=10.0,
        )
        assert batch.success_rate() == 50.0

        # Test 0% success rate
        batch = BatchResults(
            results=[],
            total_files=10,
            successful=0,
            failed=10,
            skipped=0,
            total_time=10.0,
        )
        assert batch.success_rate() == 0.0

        # Test with skipped files
        batch = BatchResults(
            results=[],
            total_files=10,
            successful=7,
            failed=2,
            skipped=1,
            total_time=10.0,
        )
        assert batch.success_rate() == 70.0

    def test_success_rate_empty_batch(self):
        """Test BatchResults.success_rate() with empty batch."""
        batch = BatchResults(
            results=[],
            total_files=0,
            successful=0,
            failed=0,
            skipped=0,
            total_time=0.0,
        )
        assert batch.success_rate() == 0.0


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid validation result."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.error_message is None

    def test_invalid_result(self):
        """Test creating an invalid validation result."""
        result = ValidationResult(valid=False, error_message="File not found")
        assert result.valid is False
        assert result.error_message == "File not found"
