"""Conversion orchestrator for HEIC to JPG converter.

This module provides the main orchestration layer that coordinates
single file and batch conversions, integrating all components:
- FileSystemHandler for file operations
- ImageAnalyzer for image analysis
- OptimizationParamGenerator for parameter generation
- ImageConverter for actual conversion
- BatchProcessor for parallel batch processing
"""

from __future__ import annotations

import json
from time import perf_counter
from typing import TYPE_CHECKING

from heic_converter.analyzer import ImageAnalyzer
from heic_converter.batch_processor import BatchProcessor
from heic_converter.converter import ImageConverter
from heic_converter.errors import ErrorHandler
from heic_converter.exif import EXIFExtractor
from heic_converter.filesystem import FileSystemHandler
from heic_converter.logging_config import get_logger
from heic_converter.models import (
    BatchResults,
    Config,
    ConversionResult,
    ConversionStatus,
)
from heic_converter.optimizer import OptimizationParamGenerator

if TYPE_CHECKING:
    import logging
    from collections.abc import Callable
    from pathlib import Path


class ConversionOrchestrator:
    """Orchestrate single and batch HEIC to JPG conversions.

    This class provides the main entry point for conversions, handling:
    - Single file conversion flow
    - Batch conversion flow with parallel processing
    - Configuration management
    - Component integration
    - Metrics persistence
    """

    def __init__(
        self,
        config: Config,
        logger: logging.Logger | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ):
        """Initialize orchestrator with configuration.

        Args:
            config: Configuration for conversions
            logger: Optional logger instance
            progress_callback: Optional callback for progress updates (current, total, filename)
        """
        self.config = config
        self.logger = logger or get_logger(__name__)
        self.progress_callback = progress_callback

        # Initialize components
        self.filesystem = FileSystemHandler()
        self.error_handler = ErrorHandler(self.logger)
        self.exif_extractor = EXIFExtractor()
        self.analyzer = ImageAnalyzer()
        self.optimizer = OptimizationParamGenerator(config.style_preferences)
        self.converter = ImageConverter(config)

        # Initialize batch processor (will be created when needed)
        self._batch_processor: BatchProcessor | None = None

        self.logger.info("ConversionOrchestrator initialized")

    def convert_single(self, input_path: Path) -> ConversionResult:
        """Convert a single HEIC file to JPG.

        This method orchestrates the complete conversion flow:
        1. Validate input file
        2. Generate output path
        3. Check for existing output (handle no-overwrite)
        4. Extract EXIF metadata
        5. Analyze image
        6. Generate optimization parameters
        7. Convert with optimizations
        8. Persist metrics (if configured)

        Args:
            input_path: Path to the input HEIC file

        Returns:
            ConversionResult with conversion status and details
        """
        start_time = perf_counter()

        try:
            self.logger.info(f"Starting conversion of {input_path.name}")

            # 1. Validate input file
            validation = self.filesystem.validate_input_file(input_path)
            if not validation.valid:
                self.logger.error(
                    f"Input validation failed for {input_path.name}: {validation.error_message}"
                )
                return ConversionResult(
                    input_path=input_path,
                    output_path=None,
                    status=ConversionStatus.FAILED,
                    error_message=validation.error_message,
                    processing_time=perf_counter() - start_time,
                )

            # 2. Generate output path
            output_path = self.filesystem.get_output_path(input_path, self.config.output_dir)

            # 3. Check for existing output file
            if output_path.exists() and self.config.no_overwrite:
                self.logger.info(f"Skipping {input_path.name}: output file already exists")
                return ConversionResult(
                    input_path=input_path,
                    output_path=output_path,
                    status=ConversionStatus.SKIPPED,
                    error_message="Output file already exists (no-overwrite enabled)",
                    processing_time=perf_counter() - start_time,
                )

            # Validate output path
            output_validation = self.filesystem.validate_output_path(
                output_path, self.config.no_overwrite
            )
            if not output_validation.valid:
                self.logger.error(
                    f"Output validation failed for {output_path}: {output_validation.error_message}"
                )
                return ConversionResult(
                    input_path=input_path,
                    output_path=None,
                    status=ConversionStatus.FAILED,
                    error_message=output_validation.error_message,
                    processing_time=perf_counter() - start_time,
                )

            # Ensure output directory exists before encoding
            self.filesystem.ensure_directory(output_path.parent)

            # 4. Decode HEIC and extract EXIF
            self.logger.debug(f"Decoding HEIC file: {input_path.name}")
            image_array, exif_dict, icc_profile = self.converter._decode_heic(input_path)
            exif_metadata = self.exif_extractor.extract_from_dict(exif_dict)

            # 5. Analyze image
            self.logger.debug(f"Analyzing image: {input_path.name}")
            metrics = self.analyzer.analyze(image_array, exif_metadata)

            if self.config.verbose:
                self.logger.debug(
                    f"Analysis metrics for {input_path.name}: "
                    f"exposure={metrics.exposure_level:.2f}, "
                    f"contrast={metrics.contrast_level:.2f}, "
                    f"highlight_clipping={metrics.highlight_clipping_percent:.1f}%, "
                    f"shadow_clipping={metrics.shadow_clipping_percent:.1f}%, "
                    f"saturation={metrics.saturation_level:.2f}, "
                    f"sharpness={metrics.sharpness_score:.2f}, "
                    f"noise={metrics.noise_level:.2f}, "
                    f"backlit={metrics.is_backlit}, "
                    f"low_light={metrics.is_low_light}"
                )

            # 6. Generate optimization parameters
            self.logger.debug(f"Generating optimization parameters: {input_path.name}")
            optimization_params = self.optimizer.generate(metrics)

            if self.config.verbose:
                self.logger.debug(
                    f"Optimization params for {input_path.name}: "
                    f"exposure_adj={optimization_params.exposure_adjustment:.2f}, "
                    f"contrast_adj={optimization_params.contrast_adjustment:.2f}, "
                    f"shadow_lift={optimization_params.shadow_lift:.2f}, "
                    f"highlight_recovery={optimization_params.highlight_recovery:.2f}, "
                    f"saturation_adj={optimization_params.saturation_adjustment:.2f}, "
                    f"sharpness={optimization_params.sharpness_amount:.2f}, "
                    f"noise_reduction={optimization_params.noise_reduction:.2f}"
                )

            # 7. Convert with optimizations
            self.logger.debug(f"Converting image: {input_path.name}")
            result = self.converter.convert(
                input_path,
                output_path,
                optimization_params,
                decoded_image=image_array,
                decoded_exif=exif_dict,
                decoded_icc_profile=icc_profile,
            )

            # Add metrics to result
            result.metrics = metrics

            # 8. Persist metrics if conversion was successful
            if result.status == ConversionStatus.SUCCESS:
                self._persist_metrics(result)
                self.logger.info(
                    f"Successfully converted {input_path.name} -> {output_path.name} "
                    f"({result.processing_time:.2f}s)"
                )
            else:
                self.logger.error(
                    f"Conversion failed for {input_path.name}: {result.error_message}"
                )

            return result

        except Exception as e:
            # Handle any unexpected errors
            self.logger.exception(f"Unexpected error converting {input_path.name}")
            return self.error_handler.handle_error(
                e,
                {
                    "input_path": input_path,
                    "operation": "single_conversion",
                    "processing_time": perf_counter() - start_time,
                },
            )

    def convert_batch(self, input_paths: list[Path]) -> BatchResults:
        """Convert multiple HEIC files in parallel.

        This method uses the BatchProcessor to convert multiple files
        in parallel, with error isolation and progress tracking.

        Args:
            input_paths: List of input HEIC file paths

        Returns:
            BatchResults with aggregated results from all conversions
        """
        if not input_paths:
            self.logger.warning("Empty batch provided for conversion")
            return BatchResults(
                results=[],
                total_files=0,
                successful=0,
                failed=0,
                skipped=0,
                total_time=0.0,
            )

        self.logger.info(f"Starting batch conversion of {len(input_paths)} files")

        # Create batch processor if not already created
        if self._batch_processor is None:
            self._batch_processor = BatchProcessor(self.config, self.logger, self.progress_callback)

        # Process batch
        batch_results = self._batch_processor.process_batch(input_paths)

        # Persist metrics for all successful conversions
        for result in batch_results.results:
            if result.status == ConversionStatus.SUCCESS and result.metrics:
                self._persist_metrics(result)

        self.logger.info(
            f"Batch conversion complete: {batch_results.successful} successful, "
            f"{batch_results.failed} failed, {batch_results.skipped} skipped "
            f"in {batch_results.total_time:.2f}s "
            f"(success rate: {batch_results.success_rate():.1f}%)"
        )

        return batch_results

    def _persist_metrics(self, result: ConversionResult) -> None:
        """Persist analysis metrics to a JSON file for review and tuning.

        Metrics are saved alongside the output JPG file with a .metrics.json extension.

        Args:
            result: ConversionResult containing metrics to persist
        """
        if not result.metrics or not result.output_path:
            return

        try:
            # Create metrics file path (same as output but with .metrics.json extension)
            metrics_path = result.output_path.with_suffix(".metrics.json")

            # Prepare metrics data
            metrics_data = {
                "input_file": str(result.input_path),
                "output_file": str(result.output_path),
                "processing_time": result.processing_time,
                "analysis_metrics": {
                    "exposure_level": result.metrics.exposure_level,
                    "contrast_level": result.metrics.contrast_level,
                    "shadow_clipping_percent": result.metrics.shadow_clipping_percent,
                    "highlight_clipping_percent": result.metrics.highlight_clipping_percent,
                    "saturation_level": result.metrics.saturation_level,
                    "sharpness_score": result.metrics.sharpness_score,
                    "noise_level": result.metrics.noise_level,
                    "skin_tone_detected": result.metrics.skin_tone_detected,
                    "skin_tone_hue_range": result.metrics.skin_tone_hue_range,
                    "is_backlit": result.metrics.is_backlit,
                    "is_low_light": result.metrics.is_low_light,
                },
                "exif_metadata": None,
                "optimization_params": None,
            }

            # Add EXIF metadata if available
            if result.metrics.exif_data:
                metrics_data["exif_metadata"] = {
                    "iso": result.metrics.exif_data.iso,
                    "exposure_time": result.metrics.exif_data.exposure_time,
                    "f_number": result.metrics.exif_data.f_number,
                    "exposure_compensation": result.metrics.exif_data.exposure_compensation,
                    "flash_fired": result.metrics.exif_data.flash_fired,
                    "scene_type": result.metrics.exif_data.scene_type,
                    "brightness_value": result.metrics.exif_data.brightness_value,
                    "metering_mode": result.metrics.exif_data.metering_mode,
                }

            # Add optimization parameters if available
            if result.optimization_params:
                metrics_data["optimization_params"] = {
                    "exposure_adjustment": result.optimization_params.exposure_adjustment,
                    "contrast_adjustment": result.optimization_params.contrast_adjustment,
                    "shadow_lift": result.optimization_params.shadow_lift,
                    "highlight_recovery": result.optimization_params.highlight_recovery,
                    "saturation_adjustment": result.optimization_params.saturation_adjustment,
                    "sharpness_amount": result.optimization_params.sharpness_amount,
                    "noise_reduction": result.optimization_params.noise_reduction,
                    "skin_tone_protection": result.optimization_params.skin_tone_protection,
                }

            # Write metrics to JSON file
            with open(metrics_path, "w", encoding="utf-8") as f:
                json.dump(metrics_data, f, indent=2)

            self.logger.debug(f"Persisted metrics to {metrics_path}")

        except Exception as e:
            # Don't fail the conversion if metrics persistence fails
            self.logger.warning(f"Failed to persist metrics for {result.input_path.name}: {str(e)}")
