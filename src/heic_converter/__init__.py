"""HEIC to JPG Converter.

A Python application that converts iPhone HEIC photos to high-quality JPG format
optimized for silver halide (analog) printing.
"""

__version__ = "0.1.0"

from heic_converter.batch_processor import BatchProcessor
from heic_converter.config import create_config, get_quality_from_env
from heic_converter.exif import EXIFExtractor
from heic_converter.logging_config import (
    get_logger,
    log_operation_complete,
    log_operation_error,
    log_operation_start,
    set_log_level,
    setup_logging,
)
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

__all__ = [
    "BatchProcessor",
    "BatchResults",
    "Config",
    "ConversionResult",
    "ConversionStatus",
    "EXIFExtractor",
    "EXIFMetadata",
    "ImageMetrics",
    "OptimizationParams",
    "StylePreferences",
    "ValidationResult",
    "create_config",
    "get_logger",
    "get_quality_from_env",
    "log_operation_complete",
    "log_operation_error",
    "log_operation_start",
    "set_log_level",
    "setup_logging",
]
