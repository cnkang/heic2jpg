"""Image converter core for HEIC to JPG conversion."""

from __future__ import annotations

import contextlib
from time import perf_counter
from typing import TYPE_CHECKING, Any, cast

import cv2
import numpy as np
import piexif
import pillow_heif
from defusedxml import ElementTree as ET
from PIL import Image

from heic2jpg.errors import InvalidFileError, ProcessingError
from heic2jpg.models import (
    Config,
    ConversionResult,
    ConversionStatus,
    OptimizationParams,
)

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

ExifDict = dict[str, Any]


class ImageConverter:
    """Convert HEIC files to JPG with optimizations."""

    INTERNAL_XMP_KEY = "__xmp__"
    EXIF_IFD_KEYS = frozenset({"0th", "Exif", "GPS", "Interop", "1st", "thumbnail"})
    XMP_NAMESPACES = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "mwg-rs": "http://www.metadataworkinggroup.com/schemas/regions/",
        "stArea": "http://ns.adobe.com/xmp/sType/Area#",
    }
    AUTO_HIGHLIGHT_TRIGGER_PERCENT = 0.7
    AUTO_HIGHLIGHT_BASE = 0.10
    AUTO_HIGHLIGHT_SLOPE = 0.04
    AUTO_HIGHLIGHT_MAX = 0.45
    FACE_RELIGHT_MIN_TRIGGER = 0.08
    FACE_RELIGHT_MAX = 0.6
    FACE_DETECT_MAX_DIMENSION = 1280

    def __init__(self, config: Config):
        """Initialize with configuration.

        Args:
            config: Configuration for conversion
        """
        self.config = config
        # Register HEIF opener with Pillow
        pillow_heif.register_heif_opener()
        self._face_detector = self._load_face_detector()

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        optimization_params: OptimizationParams,
        decoded_image: NDArray[np.uint8] | None = None,
        decoded_exif: ExifDict | None = None,
        decoded_icc_profile: bytes | None = None,
    ) -> ConversionResult:
        """Convert HEIC to JPG with optimizations.

        Args:
            input_path: Path to input HEIC file
            output_path: Path to output JPG file
            optimization_params: Optimization parameters to apply
            decoded_image: Optional pre-decoded RGB image array to avoid re-decoding
            decoded_exif: Optional EXIF dictionary associated with decoded_image
            decoded_icc_profile: Optional ICC profile associated with decoded_image

        Returns:
            ConversionResult with conversion status and details

        Raises:
            InvalidFileError: If input file cannot be read
            ProcessingError: If conversion fails
        """
        start_time = perf_counter()

        try:
            if decoded_image is None:
                # Decode HEIC file
                image_array, exif_dict, icc_profile = self._decode_heic(input_path)
            else:
                # Reuse pre-decoded image/exif when already available in the caller.
                image_array = decoded_image
                exif_dict = decoded_exif or {}
                icc_profile = decoded_icc_profile

            # Apply optimizations
            optimized_image = self._apply_optimizations(image_array, optimization_params, exif_dict)
            encoded_exif = self._sanitize_exif_for_jpeg(exif_dict)

            # Encode as JPG
            self._encode_jpg(
                optimized_image,
                output_path,
                self.config.quality,
                encoded_exif,
                icc_profile,
            )

            processing_time = perf_counter() - start_time

            return ConversionResult(
                input_path=input_path,
                output_path=output_path,
                status=ConversionStatus.SUCCESS,
                optimization_params=optimization_params,
                processing_time=processing_time,
            )

        except Exception as e:
            processing_time = perf_counter() - start_time
            error_message = f"Conversion failed: {str(e)}"

            return ConversionResult(
                input_path=input_path,
                output_path=None,
                status=ConversionStatus.FAILED,
                error_message=error_message,
                processing_time=processing_time,
            )

    def _decode_heic(self, path: Path) -> tuple[NDArray[np.uint8], ExifDict, bytes | None]:
        """Decode HEIC file and extract EXIF metadata.

        Args:
            path: Path to HEIC file

        Returns:
            Tuple of (image_array, exif_dict, icc_profile)
            image_array is RGB numpy array (uint8)
            exif_dict is EXIF data dictionary
            icc_profile is raw ICC profile bytes if available

        Raises:
            InvalidFileError: If file cannot be decoded
        """
        try:
            # Open HEIC file using Pillow with pillow-heif
            with Image.open(path) as img:
                # Parse EXIF from the original image metadata.
                # This avoids depending on converted-image info propagation.
                exif_blob = img.info.get("exif")
                exif_dict: ExifDict = {}
                if exif_blob:
                    with contextlib.suppress(Exception):
                        loaded_exif = piexif.load(exif_blob)
                        if isinstance(loaded_exif, dict):
                            exif_dict = loaded_exif
                xmp_blob = img.info.get("xmp")
                if isinstance(xmp_blob, (bytes, str)):
                    exif_dict[self.INTERNAL_XMP_KEY] = xmp_blob
                icc_profile = (
                    img.info.get("icc_profile")
                    if isinstance(img.info.get("icc_profile"), bytes)
                    else None
                )

                # Convert to RGB if necessary
                rgb_img: Image.Image = img.convert("RGB") if img.mode != "RGB" else img

                # Convert to numpy array
                image_array = np.array(rgb_img, dtype=np.uint8)

            return image_array, exif_dict, icc_profile

        except Exception as e:
            raise InvalidFileError(f"Failed to decode HEIC file {path}: {str(e)}") from e

    def _apply_optimizations(
        self,
        image: NDArray[np.uint8],
        params: OptimizationParams,
        exif_dict: ExifDict | None = None,
    ) -> NDArray[np.uint8]:
        """Apply optimization parameters to image.

        Optimizations are applied in this order:
        1. Exposure adjustment
        2. Contrast adjustment
        3. Shadow lift
        4. Highlight recovery
        5. Local face relighting
        6. Saturation adjustment
        7. Noise reduction (for low-light images)
        8. Sharpening

        Args:
            image: Image as numpy array (RGB format, uint8)
            params: Optimization parameters
            exif_dict: Optional EXIF dictionary for embedded face-region metadata

        Returns:
            Optimized image as numpy array (RGB format, uint8)
        """
        face_relight_strength = float(
            np.clip(params.face_relight_strength, 0.0, self.FACE_RELIGHT_MAX)
        )
        embedded_face_regions = self._extract_embedded_face_regions(
            exif_dict, image.shape[1], image.shape[0]
        )
        detector_face_regions = self._detect_faces(image) if not embedded_face_regions else []

        # Convert to float for processing
        img_float = image.astype(np.float32) / 255.0

        # 1. Exposure adjustment (multiply luminance)
        if abs(params.exposure_adjustment) > 0.01:
            img_float = self._adjust_exposure(img_float, params.exposure_adjustment)

        # 2. Contrast adjustment (apply curve)
        if abs(params.contrast_adjustment - 1.0) > 0.01:
            img_float = self._adjust_contrast(img_float, params.contrast_adjustment)

        # 3. Shadow lift (lift dark values)
        if params.shadow_lift > 0.01:
            img_float = self._lift_shadows(img_float, params.shadow_lift)

        # 4. Highlight recovery (compress bright values)
        # Add adaptive recovery only when prior operations may have increased clipping.
        effective_highlight_recovery = max(
            params.highlight_recovery,
            self._calculate_auto_highlight_recovery(img_float, params),
        )
        if effective_highlight_recovery > 0.01:
            img_float = self._recover_highlights(img_float, effective_highlight_recovery)

        # 5. Local face relighting (for backlit portraits)
        face_regions = embedded_face_regions or detector_face_regions
        if face_regions:
            # Auto-trigger a conservative relight when faces are much darker than bright scene areas.
            if face_relight_strength < self.FACE_RELIGHT_MIN_TRIGGER:
                face_relight_strength = max(
                    face_relight_strength,
                    self._estimate_auto_face_relight_strength(img_float, face_regions),
                )

            if face_relight_strength >= self.FACE_RELIGHT_MIN_TRIGGER:
                params.face_relight_strength = face_relight_strength
                img_float = self._relight_faces(img_float, face_regions, face_relight_strength)
            else:
                params.face_relight_strength = 0.0
        else:
            params.face_relight_strength = 0.0

        # 6. Saturation adjustment (modify in HSV space)
        if abs(params.saturation_adjustment - 1.0) > 0.01:
            img_float = self._adjust_saturation(
                img_float, params.saturation_adjustment, params.skin_tone_protection
            )

        # 7. Noise reduction (adaptive bilateral filter)
        if params.noise_reduction > 0.01:
            img_float = self._reduce_noise(img_float, params.noise_reduction)

        # 8. Sharpening (unsharp mask)
        if params.sharpness_amount > 0.01:
            img_float = self._sharpen(img_float, params.sharpness_amount)

        # Convert back to uint8
        img_float = np.clip(img_float, 0.0, 1.0)
        return cast("NDArray[np.uint8]", (img_float * 255.0).astype(np.uint8))

    def _estimate_auto_face_relight_strength(
        self,
        image: NDArray[np.float32],
        face_regions: list[tuple[int, int, int, int]],
    ) -> float:
        """Estimate conservative face relight strength from luminance contrast.

        This fallback handles cases where analyzer-side backlit detection is conservative
        but a detected face is still notably darker than bright scene regions.
        """
        if not face_regions:
            return 0.0

        luminance = 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]
        scene_mean = float(np.mean(luminance))
        bright_reference = float(np.quantile(luminance, 0.90))

        face_means: list[float] = []
        for x, y, w, h in face_regions:
            if w <= 0 or h <= 0:
                continue
            face_means.append(float(np.mean(luminance[y : y + h, x : x + w])))
        if not face_means:
            return 0.0

        face_mean = float(np.mean(face_means))
        if face_mean >= 0.62:
            return 0.0
        if bright_reference < 0.72:
            return 0.0

        darkness_gap = max(0.0, scene_mean - face_mean)
        bright_gap = max(0.0, bright_reference - face_mean)
        if darkness_gap < 0.05 and bright_gap < 0.18:
            return 0.0

        strength = 0.14 + darkness_gap * 0.9 + bright_gap * 0.35
        return float(np.clip(strength, 0.0, 0.45))

    def _load_face_detector(self) -> cv2.CascadeClassifier | None:
        """Load OpenCV Haar face detector if available."""
        try:
            cv2_data = getattr(cv2, "data", None)
            if cv2_data is None or not hasattr(cv2_data, "haarcascades"):
                return None

            haarcascades_dir = cv2_data.haarcascades
            if not isinstance(haarcascades_dir, str):
                return None

            cascade_path = f"{haarcascades_dir}haarcascade_frontalface_default.xml"
            detector = cv2.CascadeClassifier(cascade_path)
            if detector.empty():
                return None
            return detector
        except Exception:
            return None

    def _extract_embedded_face_regions(
        self,
        exif_dict: ExifDict | None,
        width: int,
        height: int,
    ) -> list[tuple[int, int, int, int]]:
        """Extract normalized face regions from embedded XMP metadata when present."""
        if not exif_dict:
            return []
        xmp_data = exif_dict.get(self.INTERNAL_XMP_KEY)
        if not isinstance(xmp_data, (bytes, str)):
            return []
        return self._extract_face_regions_from_xmp(xmp_data, width, height)

    def _extract_face_regions_from_xmp(
        self, xmp_data: bytes | str, width: int, height: int
    ) -> list[tuple[int, int, int, int]]:
        """Parse standard MWG face regions from XMP payload."""
        if isinstance(xmp_data, bytes):
            xmp_text = xmp_data.decode("utf-8", errors="ignore")
        else:
            xmp_text = xmp_data
        if not xmp_text:
            return []

        try:
            root = ET.fromstring(xmp_text)
        except ET.ParseError:
            return []

        regions: list[tuple[int, int, int, int]] = []
        for li in root.findall(".//rdf:li", self.XMP_NAMESPACES):
            for attrs in [li.attrib] + [
                area.attrib for area in li.findall(".//mwg-rs:Area", self.XMP_NAMESPACES)
            ]:
                normalized_region = self._parse_xmp_region(attrs)
                if normalized_region is None:
                    continue
                regions.append(self._normalized_region_to_pixels(normalized_region, width, height))

        # Deduplicate while preserving order.
        deduped: list[tuple[int, int, int, int]] = []
        seen: set[tuple[int, int, int, int]] = set()
        for region in regions:
            if region in seen:
                continue
            seen.add(region)
            deduped.append(region)
        return deduped

    def _parse_xmp_region(
        self, attributes: dict[str, str]
    ) -> tuple[float, float, float, float] | None:
        """Parse a normalized XMP face area (x, y, w, h)."""
        x_raw = attributes.get(f"{{{self.XMP_NAMESPACES['stArea']}}}x") or attributes.get(
            "stArea:x"
        )
        y_raw = attributes.get(f"{{{self.XMP_NAMESPACES['stArea']}}}y") or attributes.get(
            "stArea:y"
        )
        w_raw = attributes.get(f"{{{self.XMP_NAMESPACES['stArea']}}}w") or attributes.get(
            "stArea:w"
        )
        h_raw = attributes.get(f"{{{self.XMP_NAMESPACES['stArea']}}}h") or attributes.get(
            "stArea:h"
        )
        if not (x_raw and y_raw and w_raw and h_raw):
            return None

        with contextlib.suppress(ValueError):
            x = float(x_raw)
            y = float(y_raw)
            w = float(w_raw)
            h = float(h_raw)
            # Some tools store percentages [0, 100] instead of normalized [0, 1].
            if max(abs(x), abs(y), abs(w), abs(h)) > 2.0:
                x /= 100.0
                y /= 100.0
                w /= 100.0
                h /= 100.0
            return x, y, w, h
        return None

    def _normalized_region_to_pixels(
        self,
        normalized_region: tuple[float, float, float, float],
        width: int,
        height: int,
    ) -> tuple[int, int, int, int]:
        """Convert normalized center-based area to pixel rectangle."""
        x, y, w, h = normalized_region
        x = float(np.clip(x, 0.0, 1.0))
        y = float(np.clip(y, 0.0, 1.0))
        w = float(np.clip(w, 0.0, 1.0))
        h = float(np.clip(h, 0.0, 1.0))

        left = int((x - w / 2.0) * width)
        top = int((y - h / 2.0) * height)
        right = int((x + w / 2.0) * width)
        bottom = int((y + h / 2.0) * height)

        left = int(np.clip(left, 0, max(width - 1, 0)))
        top = int(np.clip(top, 0, max(height - 1, 0)))
        right = int(np.clip(right, left + 1, width))
        bottom = int(np.clip(bottom, top + 1, height))

        return left, top, right - left, bottom - top

    def _detect_faces(self, image: NDArray[np.uint8]) -> list[tuple[int, int, int, int]]:
        """Detect face regions with Haar cascade as fallback when metadata is absent."""
        if self._face_detector is None:
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        height, width = gray.shape
        max_dimension = max(height, width)
        scale = (
            max_dimension / self.FACE_DETECT_MAX_DIMENSION
            if max_dimension > self.FACE_DETECT_MAX_DIMENSION
            else 1.0
        )

        if scale > 1.0:
            resized_width = max(1, int(width / scale))
            resized_height = max(1, int(height / scale))
            detect_image = cv2.resize(
                gray, (resized_width, resized_height), interpolation=cv2.INTER_AREA
            )
        else:
            detect_image = gray

        min_size = max(24, int(min(detect_image.shape[:2]) * 0.04))
        detections = self._face_detector.detectMultiScale(
            detect_image,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(min_size, min_size),
        )

        regions: list[tuple[int, int, int, int]] = []
        for x, y, w, h in detections:
            if scale > 1.0:
                x = int(x * scale)
                y = int(y * scale)
                w = int(w * scale)
                h = int(h * scale)
            if w <= 0 or h <= 0:
                continue
            regions.append((x, y, w, h))
        return regions

    def _relight_faces(
        self,
        image: NDArray[np.float32],
        face_regions: list[tuple[int, int, int, int]],
        amount: float,
    ) -> NDArray[np.float32]:
        """Apply local face relighting with highlight protection."""
        if not face_regions:
            return image

        height, width = image.shape[:2]
        mask = np.zeros((height, width), dtype=np.float32)

        for x, y, w, h in face_regions:
            if w < 8 or h < 8:
                continue

            center_x = x + w * 0.5
            center_y = y + h * 0.52
            radius_x = max(4.0, w * 0.95)
            radius_y = max(4.0, h * 1.20)

            left = max(0, int(center_x - radius_x * 1.6))
            right = min(width, int(center_x + radius_x * 1.6))
            top = max(0, int(center_y - radius_y * 1.4))
            bottom = min(height, int(center_y + radius_y * 1.4))
            if left >= right or top >= bottom:
                continue

            yy, xx = np.ogrid[top:bottom, left:right]
            normalized_distance = ((xx - center_x) / radius_x) ** 2 + (
                (yy - center_y) / radius_y
            ) ** 2
            roi_mask = np.power(np.clip(1.0 - normalized_distance, 0.0, 1.0), 1.5).astype(
                np.float32
            )
            mask[top:bottom, left:right] = np.maximum(mask[top:bottom, left:right], roi_mask)

        if float(mask.max()) <= 0.0:
            return image

        luminance = 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]
        dark_weight = np.power(np.clip((0.75 - luminance) / 0.75, 0.0, 1.0), 0.8)
        highlight_guard = np.clip((0.95 - luminance) / 0.2, 0.0, 1.0)

        local_strength = amount * mask * dark_weight * highlight_guard
        gain = 1.0 + local_strength * 0.9
        adjusted = image * gain[:, :, np.newaxis]

        return cast("NDArray[np.float32]", np.clip(adjusted, 0.0, 1.0))

    def _sanitize_exif_for_jpeg(self, exif_dict: ExifDict) -> ExifDict:
        """Strip internal metadata keys before serializing EXIF to JPEG."""
        if not exif_dict:
            return {}
        return {key: value for key, value in exif_dict.items() if key in self.EXIF_IFD_KEYS}

    def _calculate_auto_highlight_recovery(
        self,
        image: NDArray[np.float32],
        params: OptimizationParams,
    ) -> float:
        """Estimate additional highlight recovery needed after brightening steps.

        This guard is intentionally conservative: it only activates when exposure,
        contrast, or shadow lifting can push bright tones into clipping.
        """
        has_brightening_step = (
            params.exposure_adjustment > 0.0
            or params.contrast_adjustment > 1.0
            or params.shadow_lift > 0.0
        )
        if not has_brightening_step:
            return 0.0

        highlight_clipping = self._estimate_highlight_clipping_percent(image)
        if highlight_clipping <= self.AUTO_HIGHLIGHT_TRIGGER_PERCENT:
            return 0.0

        auto_recovery = (
            self.AUTO_HIGHLIGHT_BASE
            + (highlight_clipping - self.AUTO_HIGHLIGHT_TRIGGER_PERCENT) * self.AUTO_HIGHLIGHT_SLOPE
        )
        return float(np.clip(auto_recovery, 0.0, self.AUTO_HIGHLIGHT_MAX))

    def _estimate_highlight_clipping_percent(self, image: NDArray[np.float32]) -> float:
        """Estimate highlight clipping percentage on a float RGB image."""
        luminance = 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]
        clipped = np.sum(luminance >= (250.0 / 255.0))
        return float((clipped / luminance.size) * 100.0)

    def _adjust_exposure(
        self, image: NDArray[np.float32], adjustment_ev: float
    ) -> NDArray[np.float32]:
        """Adjust exposure by multiplying luminance.

        Args:
            image: Image as float array (0-1 range, RGB)
            adjustment_ev: Exposure adjustment in EV stops

        Returns:
            Adjusted image
        """
        # Convert EV to multiplier (2^EV)
        multiplier = 2.0**adjustment_ev

        # Apply to all channels
        return cast("NDArray[np.float32]", np.clip(image * multiplier, 0.0, 1.0))

    def _adjust_contrast(
        self, image: NDArray[np.float32], multiplier: float
    ) -> NDArray[np.float32]:
        """Adjust contrast using a curve.

        Args:
            image: Image as float array (0-1 range, RGB)
            multiplier: Contrast multiplier (0.5 to 1.5)

        Returns:
            Adjusted image
        """
        # Apply contrast curve: (x - 0.5) * multiplier + 0.5
        # This pivots around middle gray
        adjusted = (image - 0.5) * multiplier + 0.5
        return cast("NDArray[np.float32]", np.clip(adjusted, 0.0, 1.0))

    def _lift_shadows(self, image: NDArray[np.float32], amount: float) -> NDArray[np.float32]:
        """Lift shadow values without affecting highlights.

        Args:
            image: Image as float array (0-1 range, RGB)
            amount: Shadow lift amount (0-1)

        Returns:
            Adjusted image
        """
        # Build a soft shadow mask so adjustments stay focused on darker tones.
        luminance = 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]
        shadow_mask = np.clip((0.55 - luminance) / 0.55, 0.0, 1.0)
        # Higher exponent reduces midtone lift and helps preserve overall contrast.
        gain = 1.0 + amount * np.power(shadow_mask, 1.8)
        adjusted = image * gain[:, :, np.newaxis]

        return cast("NDArray[np.float32]", np.clip(adjusted, 0.0, 1.0))

    def _recover_highlights(self, image: NDArray[np.float32], amount: float) -> NDArray[np.float32]:
        """Recover highlight detail by compressing bright values.

        Args:
            image: Image as float array (0-1 range, RGB)
            amount: Highlight recovery amount (0-1)

        Returns:
            Adjusted image
        """
        # Create highlight mask (stronger effect on brighter pixels)
        luminance = 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]

        # Apply compression curve to highlights
        # Use a soft knee to compress values above 0.7
        threshold = 0.7
        compression_factor = 1.0 - (amount * 0.3)  # Reduce by up to 30%

        # Apply compression only to bright areas
        mask = (luminance > threshold).astype(np.float32)
        # Fix: expand mask dimensions properly
        compression = (
            mask[:, :, np.newaxis]
            * (1.0 - compression_factor)
            * (luminance[:, :, np.newaxis] - threshold)
        )
        adjusted = image - compression

        return cast("NDArray[np.float32]", np.clip(adjusted, 0.0, 1.0))

    def _adjust_saturation(
        self,
        image: NDArray[np.float32],
        multiplier: float,
        protect_skin_tones: bool,
    ) -> NDArray[np.float32]:
        """Adjust saturation in HSV color space.

        Args:
            image: Image as float array (0-1 range, RGB)
            multiplier: Saturation multiplier (0.5 to 1.5)
            protect_skin_tones: Whether to protect skin tone hues

        Returns:
            Adjusted image
        """
        # Convert to uint8 for OpenCV
        img_uint8 = (image * 255.0).astype(np.uint8)

        # Convert to HSV
        hsv = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2HSV).astype(np.float32)
        original_saturation = hsv[:, :, 1].copy()

        # Adjust saturation
        hsv[:, :, 1] *= multiplier

        # If protecting skin tones, reduce saturation adjustment in skin tone range
        if protect_skin_tones:
            # Skin tone hue range: 0-50 degrees (0-25 in OpenCV's 0-179 scale)
            hue = hsv[:, :, 0]
            skin_mask = (hue >= 0) & (hue <= 25)

            # Reduce saturation adjustment by 50% in skin tone areas
            hsv[:, :, 1] = np.where(
                skin_mask,
                original_saturation * (1.0 + (multiplier - 1.0) * 0.5),
                hsv[:, :, 1],
            )

        # Clip saturation to valid range
        hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)

        # Convert back to RGB
        hsv_uint8 = hsv.astype(np.uint8)
        rgb = cv2.cvtColor(hsv_uint8, cv2.COLOR_HSV2RGB)

        return rgb.astype(np.float32) / 255.0

    def _reduce_noise(self, image: NDArray[np.float32], amount: float) -> NDArray[np.float32]:
        """Apply adaptive bilateral noise reduction.

        Args:
            image: Image as float array (0-1 range, RGB)
            amount: Noise reduction amount (0-1)

        Returns:
            Denoised image
        """
        # Convert to uint8 for OpenCV
        img_uint8 = (image * 255.0).astype(np.uint8)

        # Bilateral filter parameters scale with noise reduction amount
        # Diameter: 5-15 pixels
        diameter = int(5 + amount * 10)

        # Sigma color: 25-75 (how much color difference to consider)
        sigma_color = 25 + amount * 50

        # Sigma space: same as diameter
        sigma_space = diameter

        # Apply bilateral filter (preserves edges while smoothing)
        denoised = cv2.bilateralFilter(
            img_uint8,
            d=diameter,
            sigmaColor=sigma_color,
            sigmaSpace=sigma_space,
        )

        return denoised.astype(np.float32) / 255.0

    def _sharpen(self, image: NDArray[np.float32], amount: float) -> NDArray[np.float32]:
        """Apply unsharp mask sharpening.

        Args:
            image: Image as float array (0-1 range, RGB)
            amount: Sharpening amount (0-2)

        Returns:
            Sharpened image
        """
        # Convert to uint8 for OpenCV
        img_uint8 = (image * 255.0).astype(np.uint8)

        # Create Gaussian blur
        kernel_size = 5
        blurred = cv2.GaussianBlur(img_uint8, (kernel_size, kernel_size), 0)

        # Unsharp mask: original + amount * (original - blurred)
        sharpened = cv2.addWeighted(
            img_uint8,
            1.0 + amount,
            blurred,
            -amount,
            0,
        )

        return cast("NDArray[np.float32]", np.clip(sharpened, 0, 255).astype(np.float32) / 255.0)

    def _encode_jpg(
        self,
        image: NDArray[np.uint8],
        path: Path,
        quality: int,
        exif: ExifDict,
        icc_profile: bytes | None = None,
    ) -> None:
        """Encode image as JPG with EXIF metadata.

        Args:
            image: Image as numpy array (RGB format, uint8)
            path: Output path for JPG file
            quality: JPG quality (0-100)
            exif: EXIF metadata dictionary
            icc_profile: Optional ICC profile bytes to preserve source color profile

        Raises:
            ProcessingError: If encoding fails
        """
        try:
            # Convert numpy array to PIL Image
            pil_image = Image.fromarray(image, mode="RGB")

            # Prepare EXIF data if available
            exif_bytes = None
            if exif:
                with contextlib.suppress(Exception):
                    exif_bytes = piexif.dump(exif)

            save_kwargs: dict[str, Any] = {
                "format": "JPEG",
                "quality": quality,
                "optimize": True,
            }
            if exif_bytes:
                save_kwargs["exif"] = exif_bytes
            if icc_profile:
                save_kwargs["icc_profile"] = icc_profile

            # Save as JPG
            pil_image.save(path, **save_kwargs)

        except Exception as e:
            raise ProcessingError(f"Failed to encode JPG file {path}: {str(e)}") from e
