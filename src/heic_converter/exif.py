"""EXIF metadata extraction for HEIC images."""

from typing import TYPE_CHECKING, Any

import pillow_heif
from PIL import Image

from heic_converter.models import EXIFMetadata

if TYPE_CHECKING:
    from pathlib import Path


class EXIFExtractor:
    """Extract EXIF metadata from HEIC images."""

    # EXIF tag mappings
    ISO_TAG = 34855  # ISOSpeedRatings
    EXPOSURE_TIME_TAG = 33434  # ExposureTime
    F_NUMBER_TAG = 33437  # FNumber
    EXPOSURE_COMPENSATION_TAG = 37380  # ExposureCompensation
    FLASH_TAG = 37385  # Flash
    SCENE_TYPE_TAG = 41729  # SceneType
    BRIGHTNESS_VALUE_TAG = 37379  # BrightnessValue
    METERING_MODE_TAG = 37383  # MeteringMode

    # Scene type mappings
    SCENE_TYPE_MAP = {
        0: "standard",
        1: "landscape",
        2: "portrait",
        3: "night",
    }

    # Metering mode mappings
    METERING_MODE_MAP = {
        0: "unknown",
        1: "average",
        2: "center-weighted-average",
        3: "spot",
        4: "multi-spot",
        5: "pattern",
        6: "partial",
        255: "other",
    }

    def extract_from_path(self, image_path: Path) -> EXIFMetadata:
        """Extract EXIF metadata from a HEIC file.

        Args:
            image_path: Path to the HEIC file

        Returns:
            EXIFMetadata object with extracted data (fields may be None if not available)
        """
        try:
            # Register HEIF opener
            pillow_heif.register_heif_opener()

            # Open image and get EXIF data
            with Image.open(image_path) as img:
                exif_data = img.getexif()
                if exif_data is None:
                    return EXIFMetadata()

                return self._parse_exif_dict(exif_data)

        except Exception:
            # If any error occurs during extraction, return empty metadata
            # This ensures graceful fallback to image analysis alone
            return EXIFMetadata()

    def extract_from_image(self, image: Image.Image) -> EXIFMetadata:
        """Extract EXIF metadata from a PIL Image object.

        Args:
            image: PIL Image object

        Returns:
            EXIFMetadata object with extracted data (fields may be None if not available)
        """
        try:
            exif_data = image.getexif()
            if exif_data is None:
                return EXIFMetadata()

            return self._parse_exif_dict(exif_data)

        except Exception:
            # If any error occurs during extraction, return empty metadata
            return EXIFMetadata()

    def extract_from_dict(self, exif_dict: dict) -> EXIFMetadata:
        """Extract EXIF metadata from a piexif dictionary.

        Args:
            exif_dict: EXIF dictionary from piexif.load()

        Returns:
            EXIFMetadata object with extracted data (fields may be None if not available)
        """
        try:
            if not exif_dict:
                return EXIFMetadata()

            # piexif uses a different structure - EXIF data is in the "Exif" key
            exif_ifd = exif_dict.get("Exif", {})
            if not exif_ifd:
                return EXIFMetadata()

            return self._parse_exif_dict(exif_ifd)

        except Exception:
            # If any error occurs during extraction, return empty metadata
            return EXIFMetadata()

    def _parse_exif_dict(self, exif_data: Any) -> EXIFMetadata:
        """Parse EXIF dictionary and extract relevant fields.

        Args:
            exif_data: EXIF data dictionary from PIL

        Returns:
            EXIFMetadata object with extracted fields
        """
        metadata = EXIFMetadata()

        # Extract ISO
        if self.ISO_TAG in exif_data:
            iso_value = exif_data[self.ISO_TAG]
            if isinstance(iso_value, (int, float)):
                metadata.iso = int(iso_value)
            elif isinstance(iso_value, (list, tuple)) and len(iso_value) > 0:
                metadata.iso = int(iso_value[0])

        # Extract exposure time
        if self.EXPOSURE_TIME_TAG in exif_data:
            exposure = exif_data[self.EXPOSURE_TIME_TAG]
            metadata.exposure_time = self._parse_rational(exposure)

        # Extract f-number
        if self.F_NUMBER_TAG in exif_data:
            f_number = exif_data[self.F_NUMBER_TAG]
            metadata.f_number = self._parse_rational(f_number)

        # Extract exposure compensation
        if self.EXPOSURE_COMPENSATION_TAG in exif_data:
            compensation = exif_data[self.EXPOSURE_COMPENSATION_TAG]
            metadata.exposure_compensation = self._parse_rational(compensation)

        # Extract flash information
        if self.FLASH_TAG in exif_data:
            flash_value = exif_data[self.FLASH_TAG]
            if isinstance(flash_value, int):
                # Bit 0 indicates if flash fired
                metadata.flash_fired = bool(flash_value & 0x01)

        # Extract scene type
        if self.SCENE_TYPE_TAG in exif_data:
            scene_value = exif_data[self.SCENE_TYPE_TAG]
            if isinstance(scene_value, int):
                metadata.scene_type = self.SCENE_TYPE_MAP.get(scene_value, "unknown")
            elif isinstance(scene_value, bytes) and len(scene_value) > 0:
                # Scene type can be stored as bytes
                scene_int = int.from_bytes(scene_value, byteorder="big")
                metadata.scene_type = self.SCENE_TYPE_MAP.get(scene_int, "unknown")

        # Extract brightness value
        if self.BRIGHTNESS_VALUE_TAG in exif_data:
            brightness = exif_data[self.BRIGHTNESS_VALUE_TAG]
            metadata.brightness_value = self._parse_rational(brightness)

        # Extract metering mode
        if self.METERING_MODE_TAG in exif_data:
            metering_value = exif_data[self.METERING_MODE_TAG]
            if isinstance(metering_value, int):
                metadata.metering_mode = self.METERING_MODE_MAP.get(metering_value, "unknown")

        return metadata

    def _parse_rational(self, value: Any) -> float | None:
        """Parse a rational number (fraction) from EXIF data.

        Args:
            value: Value from EXIF data (can be tuple, float, or int)

        Returns:
            Float value or None if parsing fails
        """
        try:
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, tuple) and len(value) == 2:
                numerator, denominator = value
                if denominator != 0:
                    return float(numerator) / float(denominator)
            return None
        except ValueError, TypeError, ZeroDivisionError:
            return None
