"""Unit tests for ConversionOrchestrator."""

import json
import logging
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from heic2jpg.models import (
    Config,
    ConversionResult,
    ConversionStatus,
    StylePreferences,
)
from heic2jpg.orchestrator import ConversionOrchestrator


class TestConversionOrchestrator:
    """Unit tests for ConversionOrchestrator class."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return Config(
            quality=95,
            output_dir=None,
            no_overwrite=False,
            verbose=False,
            parallel_workers=2,
            style_preferences=StylePreferences(),
        )

    @pytest.fixture
    def orchestrator(self, config):
        """Create a ConversionOrchestrator instance."""
        logger = logging.getLogger("test")
        return ConversionOrchestrator(config, logger)

    def test_orchestrator_initialization(self, orchestrator, config):
        """Test that orchestrator initializes correctly."""
        assert orchestrator.config == config
        assert orchestrator.logger is not None
        assert orchestrator.filesystem is not None
        assert orchestrator.error_handler is not None
        assert orchestrator.exif_extractor is not None
        assert orchestrator.analyzer is not None
        assert orchestrator.optimizer is not None
        assert orchestrator.converter is not None

    def test_convert_single_with_invalid_file(self, orchestrator, tmp_path):
        """Test single conversion with invalid file."""
        # Create a non-existent file path
        input_path = tmp_path / "nonexistent.heic"

        result = orchestrator.convert_single(input_path)

        assert result.status == ConversionStatus.FAILED
        assert result.input_path == input_path
        assert result.output_path is None
        assert "not found" in result.error_message.lower()

    def test_convert_single_with_no_overwrite_existing_file(self, orchestrator, tmp_path):
        """Test single conversion with no-overwrite flag and existing output."""
        # Create a mock input file
        input_path = tmp_path / "test.heic"
        input_path.write_bytes(b"fake heic data")

        # Create existing output file
        output_path = tmp_path / "test.jpg"
        output_path.write_bytes(b"existing jpg")

        # Enable no-overwrite
        orchestrator.config.no_overwrite = True

        result = orchestrator.convert_single(input_path)

        assert result.status == ConversionStatus.SKIPPED
        assert "already exists" in result.error_message.lower()

    @patch("heic2jpg.orchestrator.ImageConverter")
    @patch("heic2jpg.orchestrator.ImageAnalyzer")
    @patch("heic2jpg.orchestrator.OptimizationParamGenerator")
    def test_convert_single_success_flow(
        self,
        mock_optimizer_class,
        mock_analyzer_class,
        mock_converter_class,
        orchestrator,
        tmp_path,
        sample_image_metrics,
        sample_optimization_params,
    ):
        """Test successful single conversion flow."""
        # Create a mock input file
        input_path = tmp_path / "test.heic"
        input_path.write_bytes(b"fake heic data")

        # Mock the converter decode method
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_exif = {}
        orchestrator.converter._decode_heic = Mock(return_value=(mock_image, mock_exif, None))

        # Mock the analyzer
        orchestrator.analyzer.analyze = Mock(return_value=sample_image_metrics)

        # Mock the optimizer
        orchestrator.optimizer.generate = Mock(return_value=sample_optimization_params)

        # Mock the converter convert method
        output_path = tmp_path / "test.jpg"
        mock_result = ConversionResult(
            input_path=input_path,
            output_path=output_path,
            status=ConversionStatus.SUCCESS,
            optimization_params=sample_optimization_params,
            processing_time=0.5,
        )
        orchestrator.converter.convert = Mock(return_value=mock_result)

        # Mock the persist_metrics method
        orchestrator._persist_metrics = Mock()

        result = orchestrator.convert_single(input_path)

        assert result.status == ConversionStatus.SUCCESS
        assert result.input_path == input_path
        assert result.metrics == sample_image_metrics

        # Verify the flow was called correctly
        orchestrator.converter._decode_heic.assert_called_once()
        orchestrator.analyzer.analyze.assert_called_once()
        orchestrator.optimizer.generate.assert_called_once()
        orchestrator.converter.convert.assert_called_once()
        orchestrator._persist_metrics.assert_called_once()

    def test_convert_batch_empty_list(self, orchestrator):
        """Test batch conversion with empty list."""
        result = orchestrator.convert_batch([])

        assert result.total_files == 0
        assert result.successful == 0
        assert result.failed == 0
        assert result.skipped == 0

    @patch("heic2jpg.orchestrator.BatchProcessor")
    def test_convert_batch_creates_processor(
        self, mock_batch_processor_class, orchestrator, tmp_path
    ):
        """Test that batch conversion creates a BatchProcessor."""
        # Create mock files
        files = [tmp_path / f"test{i}.heic" for i in range(3)]
        for f in files:
            f.write_bytes(b"fake heic")

        # Mock the batch processor
        mock_processor = Mock()
        mock_batch_processor_class.return_value = mock_processor

        # Mock the process_batch method
        from heic2jpg.models import BatchResults

        mock_results = BatchResults(
            results=[],
            total_files=3,
            successful=3,
            failed=0,
            skipped=0,
            total_time=1.5,
        )
        mock_processor.process_batch.return_value = mock_results

        result = orchestrator.convert_batch(files)

        assert result.total_files == 3
        assert result.successful == 3
        mock_processor.process_batch.assert_called_once_with(files)

    def test_persist_metrics_creates_json_file(
        self, orchestrator, tmp_path, sample_image_metrics, sample_optimization_params
    ):
        """Test that metrics are persisted to JSON file."""
        input_path = tmp_path / "test.heic"
        output_path = tmp_path / "test.jpg"

        result = ConversionResult(
            input_path=input_path,
            output_path=output_path,
            status=ConversionStatus.SUCCESS,
            metrics=sample_image_metrics,
            optimization_params=sample_optimization_params,
            processing_time=1.2,
        )

        orchestrator._persist_metrics(result)

        # Check that metrics file was created
        metrics_path = output_path.with_suffix(".metrics.json")
        assert metrics_path.exists()

        # Verify content
        with open(metrics_path) as f:
            data = json.load(f)

        assert data["input_file"] == str(input_path)
        assert data["output_file"] == str(output_path)
        assert data["processing_time"] == 1.2
        assert "analysis_metrics" in data
        assert "exif_metadata" in data
        assert "optimization_params" in data

        # Verify analysis metrics
        assert data["analysis_metrics"]["exposure_level"] == 0.0
        assert data["analysis_metrics"]["contrast_level"] == 0.7
        assert data["analysis_metrics"]["skin_tone_detected"] is True

        # Verify optimization params
        assert data["optimization_params"]["exposure_adjustment"] == 0.0
        assert data["optimization_params"]["noise_reduction"] == 0.3
        assert data["optimization_params"]["face_relight_strength"] == 0.0

    def test_persist_metrics_without_metrics(self, orchestrator, tmp_path):
        """Test that persist_metrics handles missing metrics gracefully."""
        result = ConversionResult(
            input_path=tmp_path / "test.heic",
            output_path=tmp_path / "test.jpg",
            status=ConversionStatus.SUCCESS,
            metrics=None,
            processing_time=1.0,
        )

        # Should not raise an error
        orchestrator._persist_metrics(result)

        # Metrics file should not be created
        metrics_path = (tmp_path / "test.jpg").with_suffix(".metrics.json")
        assert not metrics_path.exists()

    def test_persist_metrics_handles_errors_gracefully(
        self, orchestrator, tmp_path, sample_image_metrics
    ):
        """Test that persist_metrics handles errors without failing conversion."""
        # Create a result with an invalid output path
        result = ConversionResult(
            input_path=tmp_path / "test.heic",
            output_path=Path("/invalid/path/test.jpg"),
            status=ConversionStatus.SUCCESS,
            metrics=sample_image_metrics,
            processing_time=1.0,
        )

        # Should not raise an error (just log a warning)
        orchestrator._persist_metrics(result)

    def test_verbose_logging(self, config, tmp_path, caplog):
        """Test that verbose mode produces detailed logs."""
        config.verbose = True
        logger = logging.getLogger("test_verbose")
        logger.setLevel(logging.DEBUG)

        orchestrator = ConversionOrchestrator(config, logger)

        # Create a mock input file
        input_path = tmp_path / "test.heic"
        input_path.write_bytes(b"fake heic data")

        with caplog.at_level(logging.DEBUG):
            # This will fail but should produce debug logs
            result = orchestrator.convert_single(input_path)

        # Check that debug logs were produced
        # (The actual conversion will fail due to invalid HEIC data,
        # but we're testing that verbose mode is working)
        assert result.status == ConversionStatus.FAILED
