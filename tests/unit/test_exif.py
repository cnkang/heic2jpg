"""Unit tests for EXIF metadata extraction."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from PIL import Image

from heic_converter.exif import EXIFExtractor
from heic_converter.models import EXIFMetadata


class TestEXIFExtractor:
    """Tests for EXIFExtractor class."""

    def test_extract_from_image_with_complete_exif(self):
        """Test extraction from images with complete EXIF data.

        Requirements: 1.3, 21.6, 21.7, 21.8, 21.9
        """
        extractor = EXIFExtractor()

        # Create a mock image with EXIF data
        mock_image = Mock(spec=Image.Image)
        mock_exif = {
            extractor.ISO_TAG: 800,
            extractor.EXPOSURE_TIME_TAG: (1, 125),  # 1/125 second
            extractor.F_NUMBER_TAG: (18, 10),  # f/1.8
            extractor.EXPOSURE_COMPENSATION_TAG: (-5, 10),  # -0.5 EV
            extractor.FLASH_TAG: 1,  # Flash fired
            extractor.SCENE_TYPE_TAG: 3,  # Night scene
            extractor.BRIGHTNESS_VALUE_TAG: (35, 10),  # 3.5
            extractor.METERING_MODE_TAG: 3,  # Spot metering
        }
        mock_image.getexif.return_value = mock_exif

        # Extract EXIF
        result = extractor.extract_from_image(mock_image)

        # Verify all fields are extracted correctly
        assert result.iso == 800
        assert result.exposure_time == pytest.approx(1 / 125, rel=1e-6)
        assert result.f_number == pytest.approx(1.8, rel=1e-6)
        assert result.exposure_compensation == pytest.approx(-0.5, rel=1e-6)
        assert result.flash_fired is True
        assert result.scene_type == "night"
        assert result.brightness_value == pytest.approx(3.5, rel=1e-6)
        assert result.metering_mode == "spot"

    def test_extract_from_image_with_partial_exif(self):
        """Test extraction from images with partial EXIF data.

        Requirements: 1.3, 21.10
        """
        extractor = EXIFExtractor()

        # Create a mock image with only some EXIF fields
        mock_image = Mock(spec=Image.Image)
        mock_exif = {
            extractor.ISO_TAG: 400,
            extractor.F_NUMBER_TAG: (28, 10),  # f/2.8
            # Missing: exposure_time, exposure_compensation, flash, scene_type, brightness, metering
        }
        mock_image.getexif.return_value = mock_exif

        # Extract EXIF
        result = extractor.extract_from_image(mock_image)

        # Verify present fields are extracted
        assert result.iso == 400
        assert result.f_number == pytest.approx(2.8, rel=1e-6)

        # Verify missing fields are None
        assert result.exposure_time is None
        assert result.exposure_compensation is None
        assert result.flash_fired is None
        assert result.scene_type is None
        assert result.brightness_value is None
        assert result.metering_mode is None

    def test_extract_from_image_with_no_exif(self):
        """Test extraction from images with no EXIF data.

        Requirements: 1.3, 21.10
        """
        extractor = EXIFExtractor()

        # Create a mock image with no EXIF data
        mock_image = Mock(spec=Image.Image)
        mock_image.getexif.return_value = None

        # Extract EXIF
        result = extractor.extract_from_image(mock_image)

        # Verify all fields are None
        assert result.iso is None
        assert result.exposure_time is None
        assert result.f_number is None
        assert result.exposure_compensation is None
        assert result.flash_fired is None
        assert result.scene_type is None
        assert result.brightness_value is None
        assert result.metering_mode is None

    def test_extract_from_image_with_empty_exif(self):
        """Test extraction from images with empty EXIF dictionary.

        Requirements: 21.10
        """
        extractor = EXIFExtractor()

        # Create a mock image with empty EXIF data
        mock_image = Mock(spec=Image.Image)
        mock_image.getexif.return_value = {}

        # Extract EXIF
        result = extractor.extract_from_image(mock_image)

        # Verify all fields are None
        assert result.iso is None
        assert result.exposure_time is None
        assert result.f_number is None
        assert result.exposure_compensation is None
        assert result.flash_fired is None
        assert result.scene_type is None
        assert result.brightness_value is None
        assert result.metering_mode is None

    def test_extract_from_path_with_nonexistent_file(self):
        """Test extraction from non-existent file path.

        Requirements: 21.10
        """
        extractor = EXIFExtractor()

        # Try to extract from non-existent file
        non_existent_path = Path("/tmp/nonexistent_test_file.heic")
        result = extractor.extract_from_path(non_existent_path)

        # Should return empty metadata without crashing
        assert isinstance(result, EXIFMetadata)
        assert result.iso is None
        assert result.exposure_time is None
        assert result.f_number is None

    def test_parse_rational_with_tuple(self):
        """Test parsing rational numbers from tuples."""
        extractor = EXIFExtractor()

        # Test valid rational
        assert extractor._parse_rational((1, 125)) == pytest.approx(1 / 125, rel=1e-6)
        assert extractor._parse_rational((18, 10)) == pytest.approx(1.8, rel=1e-6)

        # Test zero denominator
        assert extractor._parse_rational((1, 0)) is None

        # Test invalid tuple
        assert extractor._parse_rational((1,)) is None
        assert extractor._parse_rational((1, 2, 3)) is None

    def test_parse_rational_with_numbers(self):
        """Test parsing rational numbers from int/float."""
        extractor = EXIFExtractor()

        # Test int
        assert extractor._parse_rational(800) == 800.0

        # Test float
        assert extractor._parse_rational(1.8) == pytest.approx(1.8, rel=1e-6)

    def test_parse_rational_with_invalid_input(self):
        """Test parsing rational numbers with invalid input."""
        extractor = EXIFExtractor()

        # Test None
        assert extractor._parse_rational(None) is None

        # Test string
        assert extractor._parse_rational("invalid") is None

        # Test list
        assert extractor._parse_rational([1, 2]) is None

    def test_iso_extraction_from_list(self):
        """Test ISO extraction when value is a list."""
        extractor = EXIFExtractor()

        # Create mock image with ISO as list
        mock_image = Mock(spec=Image.Image)
        mock_exif = {
            extractor.ISO_TAG: [800, 1600],  # Some cameras store multiple ISO values
        }
        mock_image.getexif.return_value = mock_exif

        # Extract EXIF
        result = extractor.extract_from_image(mock_image)

        # Should extract first value
        assert result.iso == 800

    def test_flash_fired_bit_extraction(self):
        """Test flash fired extraction from bit field."""
        extractor = EXIFExtractor()

        # Test flash fired (bit 0 set)
        mock_image = Mock(spec=Image.Image)
        mock_exif = {extractor.FLASH_TAG: 0x01}  # Flash fired
        mock_image.getexif.return_value = mock_exif
        result = extractor.extract_from_image(mock_image)
        assert result.flash_fired is True

        # Test flash not fired (bit 0 not set)
        mock_exif = {extractor.FLASH_TAG: 0x00}  # Flash not fired
        mock_image.getexif.return_value = mock_exif
        result = extractor.extract_from_image(mock_image)
        assert result.flash_fired is False

        # Test flash fired with other bits set
        mock_exif = {extractor.FLASH_TAG: 0x09}  # Flash fired + other flags
        mock_image.getexif.return_value = mock_exif
        result = extractor.extract_from_image(mock_image)
        assert result.flash_fired is True

    def test_scene_type_mapping(self):
        """Test scene type value mapping."""
        extractor = EXIFExtractor()

        # Test known scene types
        for scene_value, scene_name in extractor.SCENE_TYPE_MAP.items():
            mock_image = Mock(spec=Image.Image)
            mock_exif = {extractor.SCENE_TYPE_TAG: scene_value}
            mock_image.getexif.return_value = mock_exif
            result = extractor.extract_from_image(mock_image)
            assert result.scene_type == scene_name

        # Test unknown scene type
        mock_image = Mock(spec=Image.Image)
        mock_exif = {extractor.SCENE_TYPE_TAG: 99}  # Unknown value
        mock_image.getexif.return_value = mock_exif
        result = extractor.extract_from_image(mock_image)
        assert result.scene_type == "unknown"

    def test_scene_type_from_bytes(self):
        """Test scene type extraction when stored as bytes."""
        extractor = EXIFExtractor()

        # Test scene type as bytes
        mock_image = Mock(spec=Image.Image)
        mock_exif = {extractor.SCENE_TYPE_TAG: b"\x03"}  # Night scene as bytes
        mock_image.getexif.return_value = mock_exif
        result = extractor.extract_from_image(mock_image)
        assert result.scene_type == "night"

    def test_metering_mode_mapping(self):
        """Test metering mode value mapping."""
        extractor = EXIFExtractor()

        # Test known metering modes
        for mode_value, mode_name in extractor.METERING_MODE_MAP.items():
            mock_image = Mock(spec=Image.Image)
            mock_exif = {extractor.METERING_MODE_TAG: mode_value}
            mock_image.getexif.return_value = mock_exif
            result = extractor.extract_from_image(mock_image)
            assert result.metering_mode == mode_name

        # Test unknown metering mode
        mock_image = Mock(spec=Image.Image)
        mock_exif = {extractor.METERING_MODE_TAG: 99}  # Unknown value
        mock_image.getexif.return_value = mock_exif
        result = extractor.extract_from_image(mock_image)
        assert result.metering_mode == "unknown"

    def test_extract_from_image_handles_exceptions(self):
        """Test that extraction handles exceptions gracefully."""
        extractor = EXIFExtractor()

        # Create a mock image that raises an exception
        mock_image = Mock(spec=Image.Image)
        mock_image.getexif.side_effect = Exception("Test exception")

        # Extract EXIF (should not crash)
        result = extractor.extract_from_image(mock_image)

        # Should return empty metadata
        assert isinstance(result, EXIFMetadata)
        assert result.iso is None

    def test_extract_from_path_handles_exceptions(self):
        """Test that path extraction handles exceptions gracefully."""
        extractor = EXIFExtractor()

        # Create a temporary file that's not a valid image
        with tempfile.NamedTemporaryFile(suffix=".heic", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(b"not a valid image")

        try:
            # Extract EXIF (should not crash)
            result = extractor.extract_from_path(tmp_path)

            # Should return empty metadata
            assert isinstance(result, EXIFMetadata)
            assert result.iso is None
        finally:
            # Clean up
            if tmp_path.exists():
                tmp_path.unlink()

    def test_exposure_compensation_positive_and_negative(self):
        """Test exposure compensation with positive and negative values."""
        extractor = EXIFExtractor()

        # Test positive compensation
        mock_image = Mock(spec=Image.Image)
        mock_exif = {extractor.EXPOSURE_COMPENSATION_TAG: (10, 10)}  # +1.0 EV
        mock_image.getexif.return_value = mock_exif
        result = extractor.extract_from_image(mock_image)
        assert result.exposure_compensation == pytest.approx(1.0, rel=1e-6)

        # Test negative compensation
        mock_exif = {extractor.EXPOSURE_COMPENSATION_TAG: (-15, 10)}  # -1.5 EV
        mock_image.getexif.return_value = mock_exif
        result = extractor.extract_from_image(mock_image)
        assert result.exposure_compensation == pytest.approx(-1.5, rel=1e-6)

        # Test zero compensation
        mock_exif = {extractor.EXPOSURE_COMPENSATION_TAG: (0, 10)}  # 0.0 EV
        mock_image.getexif.return_value = mock_exif
        result = extractor.extract_from_image(mock_image)
        assert result.exposure_compensation == pytest.approx(0.0, rel=1e-6)
