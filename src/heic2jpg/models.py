"""Core data models for the HEIC to JPG converter."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ConversionStatus(Enum):
    """Status of a conversion operation."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StylePreferences:
    """Style preferences for image optimization.

    Attributes:
        natural_appearance: Prefer subtle adjustments for natural look
        preserve_highlights: Aggressively preserve highlight detail
        stable_skin_tones: Protect skin tone hue ranges from saturation changes
        avoid_filter_look: Limit adjustment ranges to avoid artificial appearance
    """

    natural_appearance: bool = True
    preserve_highlights: bool = True
    stable_skin_tones: bool = True
    avoid_filter_look: bool = True


@dataclass
class Config:
    """Configuration for the HEIC converter.

    Attributes:
        quality: JPG quality level (0-100, default 100)
        output_dir: Optional output directory for converted files
        no_overwrite: Skip existing files without prompting
        verbose: Enable verbose logging
        parallel_workers: Number of parallel workers (None = auto-detect)
        style_preferences: Style preferences for optimization
    """

    quality: int = 100
    output_dir: Path | None = None
    no_overwrite: bool = False
    verbose: bool = False
    parallel_workers: int | None = None
    style_preferences: StylePreferences = field(default_factory=StylePreferences)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not 0 <= self.quality <= 100:
            raise ValueError(f"Quality must be between 0 and 100, got {self.quality}")
        if self.parallel_workers is not None and self.parallel_workers < 1:
            raise ValueError(f"parallel_workers must be at least 1, got {self.parallel_workers}")


@dataclass
class EXIFMetadata:
    """EXIF metadata extracted from an image.

    Attributes:
        iso: ISO sensitivity value
        exposure_time: Shutter speed in seconds
        f_number: Aperture f-number
        exposure_compensation: Exposure compensation in EV
        flash_fired: Whether flash was used
        scene_type: Scene type (portrait, landscape, night, etc.)
        brightness_value: EXIF brightness value
        metering_mode: Metering mode used
    """

    iso: int | None = None
    exposure_time: float | None = None
    f_number: float | None = None
    exposure_compensation: float | None = None
    flash_fired: bool | None = None
    scene_type: str | None = None
    brightness_value: float | None = None
    metering_mode: str | None = None


@dataclass
class ImageMetrics:
    """Analysis metrics for an image.

    Attributes:
        exposure_level: Exposure level in EV (-2.0 to +2.0)
        contrast_level: Contrast level (0.0 to 1.0)
        shadow_clipping_percent: Percentage of shadow clipping (0.0 to 100.0)
        highlight_clipping_percent: Percentage of highlight clipping (0.0 to 100.0)
        saturation_level: Saturation level (0.0 to 2.0)
        sharpness_score: Sharpness score (0.0 to 1.0)
        noise_level: Noise level (0.0 to 1.0)
        skin_tone_detected: Whether skin tones were detected
        skin_tone_hue_range: Hue range of detected skin tones
        is_backlit: Whether image appears to be backlit
        is_low_light: Whether image was taken in low-light conditions
        exif_data: EXIF metadata if available
    """

    exposure_level: float
    contrast_level: float
    shadow_clipping_percent: float
    highlight_clipping_percent: float
    saturation_level: float
    sharpness_score: float
    noise_level: float
    skin_tone_detected: bool
    skin_tone_hue_range: tuple[float, float] | None
    is_backlit: bool
    is_low_light: bool
    exif_data: EXIFMetadata | None = None


@dataclass
class OptimizationParams:
    """Optimization parameters for image processing.

    Attributes:
        exposure_adjustment: Exposure adjustment in EV (-2.0 to +2.0)
        contrast_adjustment: Contrast multiplier (0.5 to 1.5)
        shadow_lift: Shadow lift amount (0.0 to 1.0)
        highlight_recovery: Highlight recovery amount (0.0 to 1.0)
        face_relight_strength: Local face relighting strength (0.0 to 1.0)
        saturation_adjustment: Saturation multiplier (0.5 to 1.5)
        sharpness_amount: Sharpening amount (0.0 to 2.0)
        noise_reduction: Noise reduction amount (0.0 to 1.0)
        skin_tone_protection: Whether to protect skin tones
    """

    exposure_adjustment: float
    contrast_adjustment: float
    shadow_lift: float
    highlight_recovery: float
    saturation_adjustment: float
    sharpness_amount: float
    noise_reduction: float
    skin_tone_protection: bool
    face_relight_strength: float = 0.0


@dataclass
class ConversionResult:
    """Result of a single conversion operation.

    Attributes:
        input_path: Path to the input HEIC file
        output_path: Path to the output JPG file (None if failed)
        status: Conversion status
        error_message: Error message if conversion failed
        metrics: Image analysis metrics if available
        optimization_params: Optimization parameters used if available
        processing_time: Time taken to process in seconds
    """

    input_path: Path
    output_path: Path | None
    status: ConversionStatus
    error_message: str | None = None
    metrics: ImageMetrics | None = None
    optimization_params: OptimizationParams | None = None
    processing_time: float = 0.0


@dataclass
class BatchResults:
    """Results of a batch conversion operation.

    Attributes:
        results: List of individual conversion results
        total_files: Total number of files processed
        successful: Number of successful conversions
        failed: Number of failed conversions
        skipped: Number of skipped files
        total_time: Total time taken in seconds
    """

    results: list[ConversionResult]
    total_files: int
    successful: int
    failed: int
    skipped: int
    total_time: float

    def success_rate(self) -> float:
        """Calculate success rate as percentage.

        Returns:
            Success rate as a percentage (0.0 to 100.0)
        """
        if self.total_files == 0:
            return 0.0
        return (self.successful / self.total_files) * 100.0


@dataclass
class ValidationResult:
    """Result of a validation operation.

    Attributes:
        valid: Whether the validation passed
        error_message: Error message if validation failed
    """

    valid: bool
    error_message: str | None = None
