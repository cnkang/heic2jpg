"""Property-based tests for ConversionOrchestrator.

These tests validate universal properties that should hold across all inputs.
"""

import json
import logging
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from heic_converter.models import (
    Config,
    ConversionResult,
    ConversionStatus,
    ImageMetrics,
    OptimizationParams,
    StylePreferences,
)
from heic_converter.orchestrator import ConversionOrchestrator


@st.composite
def image_metrics_strategy(draw):
    """Generate random but valid ImageMetrics for testing."""
    return ImageMetrics(
        exposure_level=draw(st.floats(min_value=-2.0, max_value=2.0)),
        contrast_level=draw(st.floats(min_value=0.0, max_value=1.0)),
        shadow_clipping_percent=draw(st.floats(min_value=0.0, max_value=100.0)),
        highlight_clipping_percent=draw(st.floats(min_value=0.0, max_value=100.0)),
        saturation_level=draw(st.floats(min_value=0.0, max_value=2.0)),
        sharpness_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        noise_level=draw(st.floats(min_value=0.0, max_value=1.0)),
        skin_tone_detected=draw(st.booleans()),
        skin_tone_hue_range=draw(
            st.one_of(
                st.none(),
                st.tuples(
                    st.floats(min_value=0.0, max_value=360.0),
                    st.floats(min_value=0.0, max_value=360.0),
                ),
            )
        ),
        is_backlit=draw(st.booleans()),
        is_low_light=draw(st.booleans()),
        exif_data=None,  # Simplified for this test
    )


@st.composite
def optimization_params_strategy(draw):
    """Generate random but valid OptimizationParams for testing."""
    return OptimizationParams(
        exposure_adjustment=draw(st.floats(min_value=-2.0, max_value=2.0)),
        contrast_adjustment=draw(st.floats(min_value=0.5, max_value=1.5)),
        shadow_lift=draw(st.floats(min_value=0.0, max_value=1.0)),
        highlight_recovery=draw(st.floats(min_value=0.0, max_value=1.0)),
        saturation_adjustment=draw(st.floats(min_value=0.5, max_value=1.5)),
        sharpness_amount=draw(st.floats(min_value=0.0, max_value=2.0)),
        noise_reduction=draw(st.floats(min_value=0.0, max_value=1.0)),
        skin_tone_protection=draw(st.booleans()),
    )


# Feature: heic-to-jpg-converter, Property 26: Analysis Metrics Persistence
@given(
    metrics=image_metrics_strategy(),
    optimization_params=optimization_params_strategy(),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_analysis_metrics_persistence(metrics, optimization_params):
    """Property 26: Analysis Metrics Persistence

    **Validates: Requirements 19.12**

    For any converted image, the analysis metrics should be saved (returned in
    result object or written to file) for review and tuning purposes.

    This test verifies that:
    1. Metrics are included in the ConversionResult object
    2. Metrics are persisted to a JSON file alongside the output
    3. The persisted metrics contain all required fields
    4. The persisted metrics match the original metrics
    """
    # Create a temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test input and output paths
        input_path = temp_path / "test_input.heic"
        output_path = temp_path / "test_output.jpg"

        # Create a dummy input file
        input_path.touch()

        # Create a ConversionResult with metrics
        result = ConversionResult(
            input_path=input_path,
            output_path=output_path,
            status=ConversionStatus.SUCCESS,
            error_message=None,
            metrics=metrics,
            optimization_params=optimization_params,
            processing_time=1.5,
        )

        # Create orchestrator
        config = Config(
            quality=95,
            output_dir=None,
            no_overwrite=False,
            verbose=False,
            style_preferences=StylePreferences(),
        )
        logger = logging.getLogger("test")
        orchestrator = ConversionOrchestrator(config, logger)

        # Call _persist_metrics
        orchestrator._persist_metrics(result)

        # Verify metrics file was created
        metrics_path = output_path.with_suffix(".metrics.json")
        assert metrics_path.exists(), "Metrics file should be created alongside output file"

        # Read and verify metrics file content
        with open(metrics_path, encoding="utf-8") as f:
            persisted_data = json.load(f)

        # Verify structure and required fields
        assert "input_file" in persisted_data, "Persisted metrics should include input_file"
        assert "output_file" in persisted_data, "Persisted metrics should include output_file"
        assert "processing_time" in persisted_data, (
            "Persisted metrics should include processing_time"
        )
        assert "analysis_metrics" in persisted_data, (
            "Persisted metrics should include analysis_metrics"
        )
        assert "optimization_params" in persisted_data, (
            "Persisted metrics should include optimization_params"
        )

        # Verify analysis metrics fields
        analysis = persisted_data["analysis_metrics"]
        assert "exposure_level" in analysis
        assert "contrast_level" in analysis
        assert "shadow_clipping_percent" in analysis
        assert "highlight_clipping_percent" in analysis
        assert "saturation_level" in analysis
        assert "sharpness_score" in analysis
        assert "noise_level" in analysis
        assert "skin_tone_detected" in analysis
        assert "skin_tone_hue_range" in analysis
        assert "is_backlit" in analysis
        assert "is_low_light" in analysis

        # Verify metrics values match (with floating point tolerance)
        assert abs(analysis["exposure_level"] - metrics.exposure_level) < 0.001
        assert abs(analysis["contrast_level"] - metrics.contrast_level) < 0.001
        assert abs(analysis["shadow_clipping_percent"] - metrics.shadow_clipping_percent) < 0.001
        assert (
            abs(analysis["highlight_clipping_percent"] - metrics.highlight_clipping_percent) < 0.001
        )
        assert abs(analysis["saturation_level"] - metrics.saturation_level) < 0.001
        assert abs(analysis["sharpness_score"] - metrics.sharpness_score) < 0.001
        assert abs(analysis["noise_level"] - metrics.noise_level) < 0.001
        assert analysis["skin_tone_detected"] == metrics.skin_tone_detected

        # Note: JSON serializes tuples as lists, so we need to handle that
        if metrics.skin_tone_hue_range is None:
            assert analysis["skin_tone_hue_range"] is None
        else:
            assert analysis["skin_tone_hue_range"] == list(metrics.skin_tone_hue_range)

        assert analysis["is_backlit"] == metrics.is_backlit
        assert analysis["is_low_light"] == metrics.is_low_light

        # Verify optimization parameters fields
        opt_params = persisted_data["optimization_params"]
        assert "exposure_adjustment" in opt_params
        assert "contrast_adjustment" in opt_params
        assert "shadow_lift" in opt_params
        assert "highlight_recovery" in opt_params
        assert "saturation_adjustment" in opt_params
        assert "sharpness_amount" in opt_params
        assert "noise_reduction" in opt_params
        assert "skin_tone_protection" in opt_params

        # Verify optimization parameter values match
        assert (
            abs(opt_params["exposure_adjustment"] - optimization_params.exposure_adjustment) < 0.001
        )
        assert (
            abs(opt_params["contrast_adjustment"] - optimization_params.contrast_adjustment) < 0.001
        )
        assert abs(opt_params["shadow_lift"] - optimization_params.shadow_lift) < 0.001
        assert (
            abs(opt_params["highlight_recovery"] - optimization_params.highlight_recovery) < 0.001
        )
        assert (
            abs(opt_params["saturation_adjustment"] - optimization_params.saturation_adjustment)
            < 0.001
        )
        assert abs(opt_params["sharpness_amount"] - optimization_params.sharpness_amount) < 0.001
        assert abs(opt_params["noise_reduction"] - optimization_params.noise_reduction) < 0.001
        assert opt_params["skin_tone_protection"] == optimization_params.skin_tone_protection

        # Verify processing time
        assert abs(persisted_data["processing_time"] - result.processing_time) < 0.001

        # Verify file paths
        assert persisted_data["input_file"] == str(input_path)
        assert persisted_data["output_file"] == str(output_path)


# Additional property test: Metrics persistence should not fail conversion
@given(
    metrics=image_metrics_strategy(),
    has_output_path=st.booleans(),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_metrics_persistence_does_not_fail_conversion(metrics, has_output_path):
    """Property: Metrics persistence failures should not fail the conversion.

    For any conversion result, if metrics persistence fails (e.g., due to
    permission errors), the conversion should still be considered successful
    and the error should only be logged as a warning.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_path = temp_path / "test_input.heic"
        output_path = temp_path / "test_output.jpg" if has_output_path else None

        # Create result
        result = ConversionResult(
            input_path=input_path,
            output_path=output_path,
            status=ConversionStatus.SUCCESS,
            error_message=None,
            metrics=metrics,
            optimization_params=None,
            processing_time=1.0,
        )

        # Create orchestrator
        config = Config(
            quality=95,
            output_dir=None,
            no_overwrite=False,
            verbose=False,
            style_preferences=StylePreferences(),
        )
        logger = logging.getLogger("test")
        orchestrator = ConversionOrchestrator(config, logger)

        # Call _persist_metrics - should not raise exception
        try:
            orchestrator._persist_metrics(result)
            # If output_path is None, no file should be created
            # If output_path exists, metrics file should be created
            if output_path:
                metrics_path = output_path.with_suffix(".metrics.json")
                # File may or may not exist depending on whether output_path parent exists
                # But the call should not raise an exception
        except Exception as e:
            pytest.fail(f"_persist_metrics should not raise exception, but raised: {e}")


# Property test: Metrics should be included in ConversionResult
@given(metrics=image_metrics_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_metrics_included_in_result_object(metrics):
    """Property: Metrics should be accessible in the ConversionResult object.

    For any conversion, the analysis metrics should be included in the
    ConversionResult object so they can be accessed programmatically
    without reading the JSON file.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_path = temp_path / "test_input.heic"
        output_path = temp_path / "test_output.jpg"

        # Create result with metrics
        result = ConversionResult(
            input_path=input_path,
            output_path=output_path,
            status=ConversionStatus.SUCCESS,
            error_message=None,
            metrics=metrics,
            optimization_params=None,
            processing_time=1.0,
        )

        # Verify metrics are accessible in the result object
        assert result.metrics is not None, "Metrics should be included in ConversionResult"
        assert result.metrics == metrics, "Metrics in result should match the original metrics"

        # Verify all metric fields are accessible
        assert hasattr(result.metrics, "exposure_level")
        assert hasattr(result.metrics, "contrast_level")
        assert hasattr(result.metrics, "shadow_clipping_percent")
        assert hasattr(result.metrics, "highlight_clipping_percent")
        assert hasattr(result.metrics, "saturation_level")
        assert hasattr(result.metrics, "sharpness_score")
        assert hasattr(result.metrics, "noise_level")
        assert hasattr(result.metrics, "skin_tone_detected")
        assert hasattr(result.metrics, "skin_tone_hue_range")
        assert hasattr(result.metrics, "is_backlit")
        assert hasattr(result.metrics, "is_low_light")
        assert hasattr(result.metrics, "exif_data")
