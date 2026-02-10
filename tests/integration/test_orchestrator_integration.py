"""Integration tests for ConversionOrchestrator.

These tests verify end-to-end conversion workflows including:
- Single file conversion with all components integrated
- Batch conversion with parallel processing
- Error handling and recovery
- Metrics persistence
"""

import json
from pathlib import Path

from PIL import Image

from heic_converter.config import create_config
from heic_converter.models import ConversionStatus
from heic_converter.orchestrator import ConversionOrchestrator


class TestOrchestratorSingleFileIntegration:
    """Integration tests for single file conversion."""

    def test_single_file_conversion_end_to_end(self, tmp_path: Path) -> None:
        """Test complete single file conversion workflow.

        Validates: Requirements 1.1, 1.2, 1.3, 19.12
        """
        # Create a test HEIC file (using JPG as proxy since we can't easily create real HEIC)
        input_file = tmp_path / "test_input.heic"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create a simple test image
        test_image = Image.new("RGB", (400, 300), color=(128, 128, 128))
        # Save as JPG first, then rename to .heic for testing
        temp_jpg = tmp_path / "temp.jpg"
        test_image.save(temp_jpg, format="JPEG", quality=95)
        temp_jpg.rename(input_file)

        # Create orchestrator with configuration
        config = create_config(quality=95, output_dir=output_dir, verbose=True)
        orchestrator = ConversionOrchestrator(config)

        # Convert the file
        result = orchestrator.convert_single(input_file)

        # Verify conversion succeeded
        assert result.status == ConversionStatus.SUCCESS
        assert result.input_path == input_file
        assert result.output_path is not None
        assert result.output_path.exists()
        assert result.output_path.suffix == ".jpg"
        assert result.output_path.parent == output_dir
        assert result.error_message is None
        assert result.processing_time > 0

        # Verify metrics were captured
        assert result.metrics is not None
        assert hasattr(result.metrics, "exposure_level")
        assert hasattr(result.metrics, "contrast_level")
        assert hasattr(result.metrics, "highlight_clipping_percent")

        # Verify metrics were persisted
        metrics_file = result.output_path.with_suffix(".metrics.json")
        assert metrics_file.exists()

        with open(metrics_file) as f:
            metrics_data = json.load(f)

        assert "input_file" in metrics_data
        assert "output_file" in metrics_data
        assert "analysis_metrics" in metrics_data
        assert "processing_time" in metrics_data

        # Verify output image is valid
        output_image = Image.open(result.output_path)
        assert output_image.size == test_image.size
        assert output_image.mode == "RGB"

    def test_single_file_with_no_overwrite(self, tmp_path: Path) -> None:
        """Test single file conversion with no-overwrite flag.

        Validates: Requirements 18.5
        """
        # Create input and existing output file
        input_file = tmp_path / "test.heic"
        output_file = tmp_path / "test.jpg"

        # Create test image
        test_image = Image.new("RGB", (200, 200), color=(100, 100, 100))
        temp_jpg = tmp_path / "temp.jpg"
        test_image.save(temp_jpg, format="JPEG")
        temp_jpg.rename(input_file)

        # Create existing output file
        existing_image = Image.new("RGB", (200, 200), color=(255, 0, 0))
        existing_image.save(output_file, format="JPEG")

        # Create orchestrator with no-overwrite enabled
        config = create_config(no_overwrite=True)
        orchestrator = ConversionOrchestrator(config)

        # Convert the file
        result = orchestrator.convert_single(input_file)

        # Verify file was skipped
        assert result.status == ConversionStatus.SKIPPED
        assert result.output_path == output_file
        assert "already exists" in result.error_message.lower()

        # Verify existing file was not modified
        output_image = Image.open(output_file)
        # Check that it's still the red image we created (allow for JPEG compression artifacts)
        # Use direct pixel access instead of deprecated getdata()
        pixel = output_image.getpixel((0, 0))
        # Red channel should be close to 255, green and blue should be close to 0
        assert pixel[0] >= 250  # Red channel
        assert pixel[1] <= 5  # Green channel
        assert pixel[2] <= 5  # Blue channel

    def test_single_file_with_invalid_input(self, tmp_path: Path) -> None:
        """Test single file conversion with invalid input file.

        Validates: Requirements 1.4, 1.5
        """
        # Test with non-existent file
        input_file = tmp_path / "nonexistent.heic"
        config = create_config()
        orchestrator = ConversionOrchestrator(config)

        result = orchestrator.convert_single(input_file)

        assert result.status == ConversionStatus.FAILED
        assert result.error_message is not None
        assert (
            "not found" in result.error_message.lower()
            or "does not exist" in result.error_message.lower()
        )

    def test_single_file_with_corrupted_file(self, tmp_path: Path) -> None:
        """Test single file conversion with corrupted HEIC file.

        Validates: Requirements 1.5
        """
        # Create a corrupted file (just random bytes)
        input_file = tmp_path / "corrupted.heic"
        with open(input_file, "wb") as f:
            f.write(b"This is not a valid HEIC file" * 100)

        config = create_config()
        orchestrator = ConversionOrchestrator(config)

        result = orchestrator.convert_single(input_file)

        # Should fail gracefully with error message
        assert result.status == ConversionStatus.FAILED
        assert result.error_message is not None
        assert len(result.error_message) > 0


class TestOrchestratorBatchConversionIntegration:
    """Integration tests for batch conversion."""

    def test_batch_conversion_end_to_end(self, tmp_path: Path) -> None:
        """Test complete batch conversion workflow with multiple files.

        Validates: Requirements 3.1, 3.3, 3.4
        """
        # Create multiple test HEIC files
        input_files = []
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        for i in range(5):
            input_file = tmp_path / f"test_{i}.heic"
            # Create test image with different colors
            color = (50 * i, 100, 150)
            test_image = Image.new("RGB", (300, 200), color=color)
            temp_jpg = tmp_path / f"temp_{i}.jpg"
            test_image.save(temp_jpg, format="JPEG", quality=95)
            temp_jpg.rename(input_file)
            input_files.append(input_file)

        # Create orchestrator with parallel processing
        config = create_config(quality=90, output_dir=output_dir, parallel_workers=2, verbose=True)
        orchestrator = ConversionOrchestrator(config)

        # Convert batch
        batch_results = orchestrator.convert_batch(input_files)

        # Verify batch results
        assert batch_results.total_files == 5
        assert batch_results.successful == 5
        assert batch_results.failed == 0
        assert batch_results.skipped == 0
        assert batch_results.success_rate() == 100.0
        assert batch_results.total_time > 0
        assert len(batch_results.results) == 5

        # Verify all files were converted
        for i, result in enumerate(batch_results.results):
            assert result.status == ConversionStatus.SUCCESS
            assert result.output_path is not None
            assert result.output_path.exists()
            assert result.output_path.suffix == ".jpg"
            assert result.metrics is not None

            # Verify metrics were persisted
            metrics_file = result.output_path.with_suffix(".metrics.json")
            assert metrics_file.exists()

    def test_batch_conversion_with_mixed_results(self, tmp_path: Path) -> None:
        """Test batch conversion with mix of valid and invalid files.

        Validates: Requirements 3.5
        """
        input_files = []
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create 2 valid files
        for i in range(2):
            input_file = tmp_path / f"valid_{i}.heic"
            test_image = Image.new("RGB", (200, 200), color=(100, 100, 100))
            temp_jpg = tmp_path / f"temp_valid_{i}.jpg"
            test_image.save(temp_jpg, format="JPEG")
            temp_jpg.rename(input_file)
            input_files.append(input_file)

        # Create 1 corrupted file
        corrupted_file = tmp_path / "corrupted.heic"
        with open(corrupted_file, "wb") as f:
            f.write(b"Invalid data" * 50)
        input_files.append(corrupted_file)

        # Create 1 non-existent file
        nonexistent_file = tmp_path / "nonexistent.heic"
        input_files.append(nonexistent_file)

        # Create orchestrator
        config = create_config(output_dir=output_dir, parallel_workers=2)
        orchestrator = ConversionOrchestrator(config)

        # Convert batch
        batch_results = orchestrator.convert_batch(input_files)

        # Verify batch results - should have processed all files
        assert batch_results.total_files == 4
        assert batch_results.successful == 2  # Only the valid files
        assert batch_results.failed == 2  # Corrupted and nonexistent
        assert batch_results.skipped == 0
        assert batch_results.success_rate() == 50.0

        # Verify successful conversions
        successful_results = [
            r for r in batch_results.results if r.status == ConversionStatus.SUCCESS
        ]
        assert len(successful_results) == 2
        for result in successful_results:
            assert result.output_path is not None
            assert result.output_path.exists()

        # Verify failed conversions have error messages
        failed_results = [r for r in batch_results.results if r.status == ConversionStatus.FAILED]
        assert len(failed_results) == 2
        for result in failed_results:
            assert result.error_message is not None
            assert len(result.error_message) > 0

    def test_batch_conversion_with_empty_list(self, tmp_path: Path) -> None:
        """Test batch conversion with empty file list.

        Validates: Requirements 3.1
        """
        config = create_config()
        orchestrator = ConversionOrchestrator(config)

        # Convert empty batch
        batch_results = orchestrator.convert_batch([])

        # Verify empty results
        assert batch_results.total_files == 0
        assert batch_results.successful == 0
        assert batch_results.failed == 0
        assert batch_results.skipped == 0
        assert len(batch_results.results) == 0

    def test_batch_conversion_with_no_overwrite(self, tmp_path: Path) -> None:
        """Test batch conversion with no-overwrite flag and existing files.

        Validates: Requirements 3.5, 18.5
        """
        input_files = []
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create 3 input files
        for i in range(3):
            input_file = tmp_path / f"test_{i}.heic"
            test_image = Image.new("RGB", (200, 200), color=(100 + i * 20, 100, 100))
            temp_jpg = tmp_path / f"temp_{i}.jpg"
            test_image.save(temp_jpg, format="JPEG")
            temp_jpg.rename(input_file)
            input_files.append(input_file)

        # Create existing output file for the first input
        existing_output = output_dir / "test_0.jpg"
        existing_image = Image.new("RGB", (200, 200), color=(255, 0, 0))
        existing_image.save(existing_output, format="JPEG")

        # Create orchestrator with no-overwrite
        config = create_config(output_dir=output_dir, no_overwrite=True)
        orchestrator = ConversionOrchestrator(config)

        # Convert batch
        batch_results = orchestrator.convert_batch(input_files)

        # Verify results
        assert batch_results.total_files == 3
        assert batch_results.successful == 2  # Files 1 and 2
        assert batch_results.failed == 0
        assert batch_results.skipped == 1  # File 0 was skipped

        # Verify skipped file
        skipped_results = [r for r in batch_results.results if r.status == ConversionStatus.SKIPPED]
        assert len(skipped_results) == 1
        assert skipped_results[0].input_path.name == "test_0.heic"


class TestOrchestratorErrorHandling:
    """Integration tests for error handling in orchestrator."""

    def test_orchestrator_handles_filesystem_errors(self, tmp_path: Path) -> None:
        """Test orchestrator handles filesystem errors gracefully.

        Validates: Requirements 16.1, 16.2
        """
        # Create input file
        input_file = tmp_path / "test.heic"
        test_image = Image.new("RGB", (200, 200), color=(100, 100, 100))
        temp_jpg = tmp_path / "temp.jpg"
        test_image.save(temp_jpg, format="JPEG")
        temp_jpg.rename(input_file)

        # Try to write to a read-only directory (simulate permission error)
        output_dir = tmp_path / "readonly"
        output_dir.mkdir()

        # Make directory read-only (Unix-like systems)
        import os
        import stat

        try:
            os.chmod(output_dir, stat.S_IRUSR | stat.S_IXUSR)

            config = create_config(output_dir=output_dir)
            orchestrator = ConversionOrchestrator(config)

            result = orchestrator.convert_single(input_file)

            # Should fail with descriptive error
            assert result.status == ConversionStatus.FAILED
            assert result.error_message is not None

        finally:
            # Restore permissions for cleanup
            os.chmod(output_dir, stat.S_IRWXU)

    def test_orchestrator_logs_errors(self, tmp_path: Path, caplog) -> None:
        """Test orchestrator logs errors appropriately.

        Validates: Requirements 16.2, 16.4
        """
        import logging

        caplog.set_level(logging.INFO)

        # Create invalid input file
        input_file = tmp_path / "nonexistent.heic"

        config = create_config()
        orchestrator = ConversionOrchestrator(config)

        result = orchestrator.convert_single(input_file)

        # Verify error was logged
        assert result.status == ConversionStatus.FAILED
        assert any("error" in record.message.lower() for record in caplog.records)

    def test_orchestrator_verbose_logging(self, tmp_path: Path, caplog) -> None:
        """Test orchestrator provides detailed logs in verbose mode.

        Validates: Requirements 16.5
        """
        import logging

        caplog.set_level(logging.DEBUG)

        # Create test file
        input_file = tmp_path / "test.heic"
        test_image = Image.new("RGB", (200, 200), color=(100, 100, 100))
        temp_jpg = tmp_path / "temp.jpg"
        test_image.save(temp_jpg, format="JPEG")
        temp_jpg.rename(input_file)

        # Create orchestrator with verbose mode
        config = create_config(verbose=True)
        orchestrator = ConversionOrchestrator(config)

        result = orchestrator.convert_single(input_file)

        # Verify verbose logging occurred
        assert result.status == ConversionStatus.SUCCESS

        # Check for detailed log messages
        log_messages = [record.message for record in caplog.records]
        assert any("analysis metrics" in msg.lower() for msg in log_messages)
        assert any("optimization params" in msg.lower() for msg in log_messages)


class TestOrchestratorMetricsPersistence:
    """Integration tests for metrics persistence."""

    def test_metrics_persisted_for_successful_conversion(self, tmp_path: Path) -> None:
        """Test metrics are saved for successful conversions.

        Validates: Requirements 19.12
        """
        # Create test file
        input_file = tmp_path / "test.heic"
        test_image = Image.new("RGB", (300, 200), color=(150, 150, 150))
        temp_jpg = tmp_path / "temp.jpg"
        test_image.save(temp_jpg, format="JPEG")
        temp_jpg.rename(input_file)

        config = create_config()
        orchestrator = ConversionOrchestrator(config)

        result = orchestrator.convert_single(input_file)

        # Verify conversion succeeded
        assert result.status == ConversionStatus.SUCCESS
        assert result.output_path is not None

        # Verify metrics file exists
        metrics_file = result.output_path.with_suffix(".metrics.json")
        assert metrics_file.exists()

        # Verify metrics content
        with open(metrics_file) as f:
            metrics_data = json.load(f)

        # Check required fields
        assert "input_file" in metrics_data
        assert "output_file" in metrics_data
        assert "processing_time" in metrics_data
        assert "analysis_metrics" in metrics_data

        # Check analysis metrics fields
        analysis = metrics_data["analysis_metrics"]
        assert "exposure_level" in analysis
        assert "contrast_level" in analysis
        assert "shadow_clipping_percent" in analysis
        assert "highlight_clipping_percent" in analysis
        assert "saturation_level" in analysis
        assert "sharpness_score" in analysis
        assert "noise_level" in analysis
        assert "skin_tone_detected" in analysis
        assert "is_backlit" in analysis
        assert "is_low_light" in analysis

    def test_metrics_not_persisted_for_failed_conversion(self, tmp_path: Path) -> None:
        """Test metrics are not saved for failed conversions.

        Validates: Requirements 19.12
        """
        # Create invalid file
        input_file = tmp_path / "nonexistent.heic"

        config = create_config()
        orchestrator = ConversionOrchestrator(config)

        result = orchestrator.convert_single(input_file)

        # Verify conversion failed
        assert result.status == ConversionStatus.FAILED

        # Verify no metrics file was created
        if result.output_path:
            metrics_file = result.output_path.with_suffix(".metrics.json")
            assert not metrics_file.exists()

    def test_batch_metrics_persisted_for_all_successful(self, tmp_path: Path) -> None:
        """Test metrics are saved for all successful conversions in batch.

        Validates: Requirements 19.12
        """
        input_files = []
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create 3 test files
        for i in range(3):
            input_file = tmp_path / f"test_{i}.heic"
            test_image = Image.new("RGB", (200, 200), color=(100 + i * 30, 100, 100))
            temp_jpg = tmp_path / f"temp_{i}.jpg"
            test_image.save(temp_jpg, format="JPEG")
            temp_jpg.rename(input_file)
            input_files.append(input_file)

        config = create_config(output_dir=output_dir)
        orchestrator = ConversionOrchestrator(config)

        batch_results = orchestrator.convert_batch(input_files)

        # Verify all conversions succeeded
        assert batch_results.successful == 3

        # Verify metrics files exist for all
        for result in batch_results.results:
            assert result.status == ConversionStatus.SUCCESS
            assert result.output_path is not None
            metrics_file = result.output_path.with_suffix(".metrics.json")
            assert metrics_file.exists()

            # Verify metrics content
            with open(metrics_file) as f:
                metrics_data = json.load(f)
            assert "analysis_metrics" in metrics_data
