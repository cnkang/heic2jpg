"""Image converter core for HEIC to JPG conversion."""

from __future__ import annotations

import contextlib
from time import perf_counter
from typing import TYPE_CHECKING, Any, cast

import cv2
import numpy as np
import piexif
import pillow_heif
from PIL import Image

from heic_converter.errors import InvalidFileError, ProcessingError
from heic_converter.models import (
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

    def __init__(self, config: Config):
        """Initialize with configuration.

        Args:
            config: Configuration for conversion
        """
        self.config = config
        # Register HEIF opener with Pillow
        pillow_heif.register_heif_opener()

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        optimization_params: OptimizationParams,
    ) -> ConversionResult:
        """Convert HEIC to JPG with optimizations.

        Args:
            input_path: Path to input HEIC file
            output_path: Path to output JPG file
            optimization_params: Optimization parameters to apply

        Returns:
            ConversionResult with conversion status and details

        Raises:
            InvalidFileError: If input file cannot be read
            ProcessingError: If conversion fails
        """
        start_time = perf_counter()

        try:
            # Decode HEIC file
            image_array, exif_dict = self._decode_heic(input_path)

            # Apply optimizations
            optimized_image = self._apply_optimizations(image_array, optimization_params)

            # Encode as JPG
            self._encode_jpg(optimized_image, output_path, self.config.quality, exif_dict)

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

    def _decode_heic(self, path: Path) -> tuple[NDArray[np.uint8], ExifDict]:
        """Decode HEIC file and extract EXIF metadata.

        Args:
            path: Path to HEIC file

        Returns:
            Tuple of (image_array, exif_dict)
            image_array is RGB numpy array (uint8)
            exif_dict is EXIF data dictionary

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

                # Convert to RGB if necessary
                rgb_img: Image.Image = img.convert("RGB") if img.mode != "RGB" else img

                # Convert to numpy array
                image_array = np.array(rgb_img, dtype=np.uint8)

            return image_array, exif_dict

        except Exception as e:
            raise InvalidFileError(f"Failed to decode HEIC file {path}: {str(e)}") from e

    def _apply_optimizations(
        self,
        image: NDArray[np.uint8],
        params: OptimizationParams,
    ) -> NDArray[np.uint8]:
        """Apply optimization parameters to image.

        Optimizations are applied in this order:
        1. Exposure adjustment
        2. Contrast adjustment
        3. Shadow lift
        4. Highlight recovery
        5. Saturation adjustment
        6. Noise reduction (for low-light images)
        7. Sharpening

        Args:
            image: Image as numpy array (RGB format, uint8)
            params: Optimization parameters

        Returns:
            Optimized image as numpy array (RGB format, uint8)
        """
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
        if params.highlight_recovery > 0.01:
            img_float = self._recover_highlights(img_float, params.highlight_recovery)

        # 5. Saturation adjustment (modify in HSV space)
        if abs(params.saturation_adjustment - 1.0) > 0.01:
            img_float = self._adjust_saturation(
                img_float, params.saturation_adjustment, params.skin_tone_protection
            )

        # 6. Noise reduction (adaptive bilateral filter)
        if params.noise_reduction > 0.01:
            img_float = self._reduce_noise(img_float, params.noise_reduction)

        # 7. Sharpening (unsharp mask)
        if params.sharpness_amount > 0.01:
            img_float = self._sharpen(img_float, params.sharpness_amount)

        # Convert back to uint8
        img_float = np.clip(img_float, 0.0, 1.0)
        return cast("NDArray[np.uint8]", (img_float * 255.0).astype(np.uint8))

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
        # Create shadow mask (stronger effect on darker pixels)
        # Use luminance to determine shadows
        luminance = 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]
        shadow_mask = 1.0 - luminance  # Inverted: 1 for dark, 0 for bright

        # Apply lift with mask
        lift = amount * shadow_mask[:, :, np.newaxis]
        adjusted = image + lift

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
    ) -> None:
        """Encode image as JPG with EXIF metadata.

        Args:
            image: Image as numpy array (RGB format, uint8)
            path: Output path for JPG file
            quality: JPG quality (0-100)
            exif: EXIF metadata dictionary

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

            # Save as JPG
            if exif_bytes:
                pil_image.save(path, format="JPEG", quality=quality, optimize=True, exif=exif_bytes)
            else:
                pil_image.save(path, format="JPEG", quality=quality, optimize=True)

        except Exception as e:
            raise ProcessingError(f"Failed to encode JPG file {path}: {str(e)}") from e
