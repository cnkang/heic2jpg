"""Batch processor with parallel execution for HEIC to JPG converter."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import blake2s
from time import perf_counter
from typing import TYPE_CHECKING

from heic2jpg.analyzer import ImageAnalyzer
from heic2jpg.converter import ImageConverter
from heic2jpg.errors import ErrorHandler
from heic2jpg.exif import EXIFExtractor
from heic2jpg.filesystem import FileSystemHandler
from heic2jpg.logging_config import get_logger
from heic2jpg.models import BatchResults, Config, ConversionResult, ConversionStatus
from heic2jpg.optimizer import OptimizationParamGenerator

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class BatchProcessor:
    """Manage parallel execution of conversions using multiprocessing.

    This class implements parallel batch processing with:
    - Automatic worker count determination based on CPU cores
    - Error isolation (one file failure doesn't stop batch)
    - Progress tracking across workers
    - Result aggregation
    """

    def __init__(
        self,
        config: Config,
        logger: logging.Logger | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ):
        """Initialize with configuration and determine worker count.

        Args:
            config: Configuration for conversion
            logger: Optional logger instance
            progress_callback: Optional callback for progress updates (current, total, filename)
        """
        self.config = config
        self.logger = logger or get_logger(__name__)
        self.progress_callback = progress_callback

        # Determine worker count
        if config.parallel_workers is not None:
            self.worker_count = config.parallel_workers
        else:
            # Auto-detect based on CPU cores
            cpu_count = os.cpu_count()
            if cpu_count is None:
                self.worker_count = 4  # Fallback default
            else:
                # Use all cores, but cap at 8 for reasonable resource usage
                self.worker_count = min(cpu_count, 8)

        self.logger.info(f"BatchProcessor initialized with {self.worker_count} workers")

    def process_batch(self, files: list[Path]) -> BatchResults:
        """Process multiple files in parallel using ProcessPoolExecutor.

        Args:
            files: List of input file paths to process

        Returns:
            BatchResults with aggregated results from all conversions
        """
        if not files:
            # Empty batch
            return BatchResults(
                results=[],
                total_files=0,
                successful=0,
                failed=0,
                skipped=0,
                total_time=0.0,
            )

        start_time = perf_counter()
        results: list[ConversionResult] = []
        planned_jobs = self._plan_output_paths(files)

        self.logger.info(f"Starting batch processing of {len(planned_jobs)} files")

        # Use ProcessPoolExecutor for true parallelism
        with ProcessPoolExecutor(max_workers=self.worker_count) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(
                    _process_single_file_worker,
                    file_path,
                    self.config,
                    output_path,
                ): file_path
                for file_path, output_path in planned_jobs
            }

            # Collect results as they complete
            for completed_count, future in enumerate(as_completed(future_to_file), start=1):
                file_path = future_to_file[future]

                try:
                    result = future.result()
                    results.append(result)

                    # Log result
                    if result.status == ConversionStatus.SUCCESS:
                        self.logger.info(
                            f"Successfully converted {result.input_path.name} "
                            f"({completed_count}/{len(files)})"
                        )
                    elif result.status == ConversionStatus.FAILED:
                        self.logger.error(
                            f"Failed to convert {result.input_path.name}: "
                            f"{result.error_message} ({completed_count}/{len(files)})"
                        )
                    elif result.status == ConversionStatus.SKIPPED:
                        self.logger.info(
                            f"Skipped {result.input_path.name} ({completed_count}/{len(files)})"
                        )

                    # Call progress callback if provided
                    if self.progress_callback:
                        self.progress_callback(completed_count, len(files), file_path.name)

                except Exception as e:
                    # Worker process raised an exception
                    # Create a failed result
                    self.logger.error(f"Worker process failed for {file_path.name}: {str(e)}")
                    error_handler = ErrorHandler(self.logger)
                    result = error_handler.handle_error(
                        e, {"input_path": file_path, "operation": "batch_processing"}
                    )
                    results.append(result)

                    # Call progress callback if provided
                    if self.progress_callback:
                        self.progress_callback(completed_count, len(files), file_path.name)

        # Aggregate results
        total_time = perf_counter() - start_time
        successful = sum(1 for r in results if r.status == ConversionStatus.SUCCESS)
        failed = sum(1 for r in results if r.status == ConversionStatus.FAILED)
        skipped = sum(1 for r in results if r.status == ConversionStatus.SKIPPED)

        batch_results = BatchResults(
            results=results,
            total_files=len(files),
            successful=successful,
            failed=failed,
            skipped=skipped,
            total_time=total_time,
        )

        self.logger.info(
            f"Batch processing complete: {successful} successful, "
            f"{failed} failed, {skipped} skipped in {total_time:.2f}s"
        )

        return batch_results

    def _plan_output_paths(self, files: list[Path]) -> list[tuple[Path, Path]]:
        """Plan deterministic output paths and prevent in-batch filename collisions."""
        filesystem = FileSystemHandler()
        used_paths: set[Path] = set()
        planned_jobs: list[tuple[Path, Path]] = []

        for file_path in files:
            base_output_path = filesystem.get_output_path(file_path, self.config.output_dir)
            output_path = base_output_path
            duplicate_index = 0

            while output_path in used_paths:
                output_path = self._with_collision_suffix(
                    base_output_path, file_path, duplicate_index
                )
                duplicate_index += 1

            if output_path != base_output_path:
                self.logger.warning(
                    f"Output path collision detected for {file_path.name}; "
                    f"using {output_path.name} instead of {base_output_path.name}"
                )

            used_paths.add(output_path)
            planned_jobs.append((file_path, output_path))

        return planned_jobs

    @staticmethod
    def _with_collision_suffix(base_output_path: Path, file_path: Path, index: int) -> Path:
        """Build a collision-safe output filename using a deterministic source hash."""
        try:
            source_key = str(file_path.resolve(strict=False))
        except OSError, RuntimeError:
            source_key = str(file_path)
        source_hash = blake2s(source_key.encode("utf-8"), digest_size=4).hexdigest()
        ordinal_suffix = "" if index == 0 else f"_{index}"
        unique_name = (
            f"{base_output_path.stem}_{source_hash}{ordinal_suffix}{base_output_path.suffix}"
        )
        return base_output_path.with_name(unique_name)


def _process_single_file_worker(
    file_path: Path,
    config: Config,
    output_path: Path | None = None,
) -> ConversionResult:
    """Process a single file (called by worker processes).

    This function is designed to be called by worker processes in the
    ProcessPoolExecutor. It creates its own instances of all necessary
    components to avoid pickling issues.

    Args:
        file_path: Path to the input file
        config: Configuration for conversion
        output_path: Optional pre-planned output path to avoid in-batch collisions

    Returns:
        ConversionResult for the file
    """
    # Create logger for this worker
    logger = logging.getLogger(f"worker-{os.getpid()}")

    # Create component instances for this worker
    filesystem = FileSystemHandler()
    error_handler = ErrorHandler(logger)
    exif_extractor = EXIFExtractor()
    analyzer = ImageAnalyzer()
    optimizer = OptimizationParamGenerator(config.style_preferences)
    converter = ImageConverter(config)

    try:
        # Validate input file
        validation = filesystem.validate_input_file(file_path)
        if not validation.valid:
            return ConversionResult(
                input_path=file_path,
                output_path=None,
                status=ConversionStatus.FAILED,
                error_message=validation.error_message,
            )

        # Generate output path
        target_output_path = output_path or filesystem.get_output_path(file_path, config.output_dir)

        # Check if output file exists and handle no-overwrite flag
        if target_output_path.exists() and config.no_overwrite:
            return ConversionResult(
                input_path=file_path,
                output_path=target_output_path,
                status=ConversionStatus.SKIPPED,
                error_message="Output file already exists (no-overwrite enabled)",
            )

        # Validate output path
        output_validation = filesystem.validate_output_path(target_output_path, config.no_overwrite)
        if not output_validation.valid:
            return ConversionResult(
                input_path=file_path,
                output_path=None,
                status=ConversionStatus.FAILED,
                error_message=output_validation.error_message,
            )

        # Ensure output directory exists before encoding
        filesystem.ensure_directory(target_output_path.parent)

        # Decode HEIC and extract EXIF
        image_array, exif_dict, icc_profile = converter._decode_heic(file_path)
        exif_metadata = exif_extractor.extract_from_dict(exif_dict)

        # Analyze image
        metrics = analyzer.analyze(image_array, exif_metadata)

        # Generate optimization parameters
        optimization_params = optimizer.generate(metrics)

        # Convert with optimizations
        result = converter.convert(
            file_path,
            target_output_path,
            optimization_params,
            decoded_image=image_array,
            decoded_exif=exif_dict,
            decoded_icc_profile=icc_profile,
        )

        # Add metrics to result
        result.metrics = metrics

        return result

    except Exception as e:
        # Handle any errors
        return error_handler.handle_error(e, {"input_path": file_path, "operation": "conversion"})
