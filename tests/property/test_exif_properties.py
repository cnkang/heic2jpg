"""Property-based tests for EXIF metadata handling.

These tests validate universal properties that should hold across all inputs.
"""

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from PIL import Image

from heic_converter.exif import EXIFExtractor
from heic_converter.models import EXIFMetadata


# Custom strategies for generating test data
@st.composite
def exif_metadata_values(draw):
    """Generate random but valid EXIF metadata values."""
    return {
        "iso": draw(st.one_of(st.none(), st.integers(min_value=50, max_value=102400))),
        "exposure_time": draw(st.one_of(st.none(), st.floats(min_value=0.0001, max_value=30.0))),
        "f_number": draw(st.one_of(st.none(), st.floats(min_value=1.0, max_value=32.0))),
        "exposure_compensation": draw(
            st.one_of(st.none(), st.floats(min_value=-5.0, max_value=5.0))
        ),
        "flash_fired": draw(st.one_of(st.none(), st.booleans())),
        "brightness_value": draw(st.one_of(st.none(), st.floats(min_value=-10.0, max_value=10.0))),
    }


@st.composite
def simple_test_images(draw):
    """Generate simple test images with random dimensions and colors.

    Returns a PIL Image object.
    """
    width = draw(st.integers(min_value=10, max_value=200))
    height = draw(st.integers(min_value=10, max_value=200))

    # Create a simple RGB image with random color
    r = draw(st.integers(min_value=0, max_value=255))
    g = draw(st.integers(min_value=0, max_value=255))
    b = draw(st.integers(min_value=0, max_value=255))

    img = Image.new("RGB", (width, height), color=(r, g, b))
    return img


# Feature: heic2jpg, Property 2: EXIF Metadata Preservation
# Note: This test validates EXIF extraction. Full preservation test requires converter implementation.
@given(image=simple_test_images())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_exif_extraction_handles_missing_data(image):
    """Property 2: EXIF Metadata Preservation (Extraction Component)

    **Validates: Requirements 1.3**

    For any image (with or without EXIF metadata), the EXIF extractor should
    successfully extract metadata without crashing. When EXIF data is missing,
    it should return an EXIFMetadata object with None values.

    Note: Full EXIF preservation test will be implemented when converter is available.
    """
    extractor = EXIFExtractor()

    # Extract EXIF from image (which has no EXIF data)
    result = extractor.extract_from_image(image)

    # Should return an EXIFMetadata object
    assert isinstance(result, EXIFMetadata), "Extractor should return EXIFMetadata object"

    # All fields should be None for image without EXIF
    assert result.iso is None
    assert result.exposure_time is None
    assert result.f_number is None
    assert result.exposure_compensation is None
    assert result.flash_fired is None
    assert result.scene_type is None
    assert result.brightness_value is None
    assert result.metering_mode is None


# Feature: heic2jpg, Property 32: EXIF Data Fallback
@given(image=simple_test_images())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_exif_fallback_graceful_handling(image):
    """Property 32: EXIF Data Fallback

    **Validates: Requirements 21.10**

    For any image without EXIF data or with incomplete EXIF data, the converter
    should successfully analyze and optimize the image using image analysis alone.

    This test validates that EXIF extraction gracefully handles missing data.
    """
    extractor = EXIFExtractor()

    # Extract EXIF from image without EXIF data
    result = extractor.extract_from_image(image)

    # Should not raise an exception
    assert isinstance(result, EXIFMetadata), "Extractor should handle missing EXIF gracefully"

    # Should return valid EXIFMetadata object (even if all fields are None)
    assert result.iso is None or isinstance(result.iso, int)
    assert result.exposure_time is None or isinstance(result.exposure_time, float)
    assert result.f_number is None or isinstance(result.f_number, float)
    assert result.exposure_compensation is None or isinstance(result.exposure_compensation, float)
    assert result.flash_fired is None or isinstance(result.flash_fired, bool)
    assert result.scene_type is None or isinstance(result.scene_type, str)
    assert result.brightness_value is None or isinstance(result.brightness_value, float)
    assert result.metering_mode is None or isinstance(result.metering_mode, str)


# Test that EXIF extraction from non-existent files returns empty metadata
@given(
    filename=st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"),
        min_size=1,
        max_size=20,
    )
)
@settings(max_examples=100)
@pytest.mark.property_test
def test_exif_extraction_from_nonexistent_file(filename):
    """Property: EXIF extraction from non-existent files should return empty metadata.

    For any non-existent file path, the EXIF extractor should gracefully handle
    the error and return an empty EXIFMetadata object.
    """
    extractor = EXIFExtractor()

    # Create a path to a non-existent file
    non_existent_path = Path(f"/tmp/nonexistent_{filename}.heic")

    # Extract EXIF (should not crash)
    result = extractor.extract_from_path(non_existent_path)

    # Should return an EXIFMetadata object with all None values
    assert isinstance(result, EXIFMetadata)
    assert result.iso is None
    assert result.exposure_time is None
    assert result.f_number is None
    assert result.exposure_compensation is None
    assert result.flash_fired is None
    assert result.scene_type is None
    assert result.brightness_value is None
    assert result.metering_mode is None
