"""Image analysis engine for HEIC to JPG converter."""

from typing import TYPE_CHECKING

import cv2
import numpy as np

from heic_converter.models import EXIFMetadata, ImageMetrics

if TYPE_CHECKING:
    from numpy.typing import NDArray


class ImageAnalyzer:
    """Analyze images for exposure, contrast, clipping, saturation, sharpness, and noise."""

    # Thresholds for various detections
    SHADOW_THRESHOLD = 5  # Pixel values 0-5 considered shadow clipping
    HIGHLIGHT_THRESHOLD = 250  # Pixel values 250-255 considered highlight clipping
    SKIN_TONE_HUE_MIN = 0  # Minimum hue for skin tones (degrees)
    SKIN_TONE_HUE_MAX = 50  # Maximum hue for skin tones (degrees)
    LOW_LIGHT_THRESHOLD = 0.3  # Mean luminance below this is low-light
    HIGH_ISO_THRESHOLD = 800  # ISO above this indicates likely noise
    BACKLIT_CONTRAST_RATIO = 1.5  # Center/edge brightness ratio for backlit detection

    def analyze(self, image: NDArray[np.uint8], exif: EXIFMetadata | None = None) -> ImageMetrics:
        """Analyze image and return comprehensive metrics.

        Args:
            image: Image as numpy array (RGB format, uint8)
            exif: Optional EXIF metadata to inform analysis

        Returns:
            ImageMetrics with all analysis results
        """
        # Calculate exposure level
        exposure_level = self._calculate_exposure(image, exif)

        # Calculate contrast
        contrast_level = self._calculate_contrast(image)

        # Detect clipping
        shadow_clipping, highlight_clipping = self._detect_clipping(image)

        # Calculate saturation
        saturation_level = self._calculate_saturation(image)

        # Calculate sharpness
        sharpness_score = self._calculate_sharpness(image)

        # Estimate noise
        noise_level = self._estimate_noise(image, exif)

        # Detect skin tones
        skin_tone_detected, skin_tone_hue_range = self._detect_skin_tones(image)

        # Detect backlit subject
        is_backlit = self._detect_backlit_subject(image)

        # Detect low-light conditions
        is_low_light = self._detect_low_light(image, exif)

        return ImageMetrics(
            exposure_level=exposure_level,
            contrast_level=contrast_level,
            shadow_clipping_percent=shadow_clipping,
            highlight_clipping_percent=highlight_clipping,
            saturation_level=saturation_level,
            sharpness_score=sharpness_score,
            noise_level=noise_level,
            skin_tone_detected=skin_tone_detected,
            skin_tone_hue_range=skin_tone_hue_range,
            is_backlit=is_backlit,
            is_low_light=is_low_light,
            exif_data=exif,
        )

    def _calculate_exposure(self, image: NDArray[np.uint8], exif: EXIFMetadata | None) -> float:
        """Calculate exposure level using histogram analysis and EXIF data.

        Args:
            image: Image as numpy array (RGB format)
            exif: Optional EXIF metadata

        Returns:
            Exposure level in EV (-2.0 to +2.0, where 0 is properly exposed)
        """
        # Convert to grayscale for luminance analysis
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        # Calculate histogram
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten() / hist.sum()  # Normalize

        # Calculate mean luminance of middle 50% (ignore extreme shadows/highlights)
        cumsum = np.cumsum(hist)
        lower_idx = np.searchsorted(cumsum, 0.25)
        upper_idx = np.searchsorted(cumsum, 0.75)

        # Calculate weighted mean of middle range
        middle_values = np.arange(lower_idx, upper_idx + 1)
        middle_weights = hist[lower_idx : upper_idx + 1]
        if middle_weights.sum() > 0:
            mean_luminance = np.average(middle_values, weights=middle_weights) / 255.0
        else:
            mean_luminance = gray.mean() / 255.0

        # Target is middle gray (0.5)
        # Convert to EV scale: each stop is a doubling/halving
        if mean_luminance > 0:
            exposure_ev = np.log2(mean_luminance / 0.5)
        else:
            exposure_ev = -2.0

        # Apply EXIF exposure compensation if available
        if exif and exif.exposure_compensation is not None:
            exposure_ev += exif.exposure_compensation

        # Clamp to reasonable range
        return float(np.clip(exposure_ev, -2.0, 2.0))

    def _calculate_contrast(self, image: NDArray[np.uint8]) -> float:
        """Calculate contrast using standard deviation of luminance.

        Args:
            image: Image as numpy array (RGB format)

        Returns:
            Contrast level (0.0 to 1.0, where higher is more contrast)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        # Calculate standard deviation of luminance
        std_dev = np.std(gray.astype(np.float32))

        # Normalize to 0-1 range (typical std dev is 0-128 for 8-bit images)
        contrast = std_dev / 128.0

        return float(np.clip(contrast, 0.0, 1.0))

    def _detect_clipping(self, image: NDArray[np.uint8]) -> tuple[float, float]:
        """Detect shadow and highlight clipping percentages.

        Args:
            image: Image as numpy array (RGB format)

        Returns:
            Tuple of (shadow_clipping_percent, highlight_clipping_percent)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        total_pixels = gray.size

        # Count shadow clipping (0-5)
        shadow_clipped = np.sum(gray <= self.SHADOW_THRESHOLD)
        shadow_percent = (shadow_clipped / total_pixels) * 100.0

        # Count highlight clipping (250-255)
        highlight_clipped = np.sum(gray >= self.HIGHLIGHT_THRESHOLD)
        highlight_percent = (highlight_clipped / total_pixels) * 100.0

        return float(shadow_percent), float(highlight_percent)

    def _calculate_saturation(self, image: NDArray[np.uint8]) -> float:
        """Calculate average saturation in HSV color space.

        Args:
            image: Image as numpy array (RGB format)

        Returns:
            Saturation level (0.0 to 2.0, where 1.0 is normal)
        """
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

        # Extract saturation channel (0-255)
        saturation = hsv[:, :, 1]

        # Calculate mean saturation
        mean_sat = np.mean(saturation) / 255.0

        # Scale to 0-2 range (1.0 is normal)
        return float(mean_sat * 2.0)

    def _calculate_sharpness(self, image: NDArray[np.uint8]) -> float:
        """Calculate sharpness using Laplacian variance.

        Args:
            image: Image as numpy array (RGB format)

        Returns:
            Sharpness score (0.0 to 1.0, where higher is sharper)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        # Calculate Laplacian
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)

        # Calculate variance of Laplacian
        variance = laplacian.var()

        # Normalize to 0-1 range (typical variance is 0-1000 for sharp images)
        sharpness = variance / 1000.0

        return float(np.clip(sharpness, 0.0, 1.0))

    def _estimate_noise(self, image: NDArray[np.uint8], exif: EXIFMetadata | None) -> float:
        """Estimate noise level using high-frequency analysis and ISO information.

        Args:
            image: Image as numpy array (RGB format)
            exif: Optional EXIF metadata with ISO information

        Returns:
            Noise level (0.0 to 1.0, where higher is more noise)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)

        # Apply high-pass filter to isolate noise
        # Use Gaussian blur and subtract from original
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        high_freq = gray - blurred

        # Calculate standard deviation of high-frequency components
        noise_std = np.std(high_freq)

        # Normalize to 0-1 range (typical noise std is 0-20)
        noise_from_analysis = noise_std / 20.0

        # If ISO information is available, use it to inform noise estimate
        if exif and exif.iso is not None:
            # Higher ISO typically means more noise
            # ISO 100 = minimal noise, ISO 3200+ = significant noise
            iso_factor = min(exif.iso / 3200.0, 1.0)

            # Combine analysis and ISO information (weighted average)
            noise_level = 0.6 * noise_from_analysis + 0.4 * iso_factor
        else:
            noise_level = noise_from_analysis

        return float(np.clip(noise_level, 0.0, 1.0))

    def _detect_skin_tones(
        self, image: NDArray[np.uint8]
    ) -> tuple[bool, tuple[float, float] | None]:
        """Detect presence and hue range of skin tones.

        Args:
            image: Image as numpy array (RGB format)

        Returns:
            Tuple of (skin_tone_detected, hue_range)
            hue_range is (min_hue, max_hue) in degrees if detected, None otherwise
        """
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

        # Extract hue channel (0-179 in OpenCV)
        hue = hsv[:, :, 0]

        # Convert hue range to OpenCV scale (0-179 instead of 0-360)
        hue_min_cv = int(self.SKIN_TONE_HUE_MIN * 179 / 360)
        hue_max_cv = int(self.SKIN_TONE_HUE_MAX * 179 / 360)

        # Create mask for skin tone hue range
        skin_mask = (hue >= hue_min_cv) & (hue <= hue_max_cv)

        # Also check saturation and value to avoid false positives
        # Skin tones typically have moderate saturation (20-170) and value (50-255)
        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        skin_mask = skin_mask & (saturation >= 20) & (saturation <= 170)
        skin_mask = skin_mask & (value >= 50)

        # Count skin tone pixels
        skin_pixels = np.sum(skin_mask)
        total_pixels = image.shape[0] * image.shape[1]
        skin_percent = (skin_pixels / total_pixels) * 100.0

        # Consider skin tones detected if > 5% of image
        if skin_percent > 5.0:
            # Calculate actual hue range of detected skin tones
            skin_hues = hue[skin_mask]
            if len(skin_hues) > 0:
                # Convert to float first to avoid overflow
                min_hue = float(np.min(skin_hues).astype(np.float32) * 360.0 / 179.0)
                max_hue = float(np.max(skin_hues).astype(np.float32) * 360.0 / 179.0)
                return True, (min_hue, max_hue)

        return False, None

    def _detect_backlit_subject(self, image: NDArray[np.uint8]) -> bool:
        """Detect backlit subjects by analyzing luminance distribution.

        Backlit images typically have bright backgrounds and dark foregrounds.

        Args:
            image: Image as numpy array (RGB format)

        Returns:
            True if image appears to be backlit
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        height, width = gray.shape

        # Define center region (middle 40% of image)
        center_y_start = int(height * 0.3)
        center_y_end = int(height * 0.7)
        center_x_start = int(width * 0.3)
        center_x_end = int(width * 0.7)
        center_region = gray[center_y_start:center_y_end, center_x_start:center_x_end]

        # Define edge regions (outer 20% on each side)
        edge_thickness = int(min(height, width) * 0.2)
        top_edge = gray[:edge_thickness, :]
        bottom_edge = gray[-edge_thickness:, :]
        left_edge = gray[:, :edge_thickness]
        right_edge = gray[:, -edge_thickness:]

        # Calculate mean brightness
        center_brightness = np.mean(center_region)
        edge_brightness = np.mean(
            [
                np.mean(top_edge),
                np.mean(bottom_edge),
                np.mean(left_edge),
                np.mean(right_edge),
            ]
        )

        # Backlit if edges are significantly brighter than center
        if edge_brightness > 0:
            brightness_ratio = edge_brightness / (center_brightness + 1e-6)
            return bool(brightness_ratio > self.BACKLIT_CONTRAST_RATIO)

        return False

    def _detect_low_light(self, image: NDArray[np.uint8], exif: EXIFMetadata | None) -> bool:
        """Detect low-light conditions using histogram analysis and EXIF data.

        Args:
            image: Image as numpy array (RGB format)
            exif: Optional EXIF metadata

        Returns:
            True if image was taken in low-light conditions
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        # Calculate mean luminance
        mean_luminance = np.mean(gray) / 255.0

        # Check histogram-based darkness
        is_dark = mean_luminance < self.LOW_LIGHT_THRESHOLD

        # Check EXIF indicators if available
        high_iso = False
        slow_shutter = False

        if exif:
            # High ISO indicates low-light
            if exif.iso is not None:
                high_iso = exif.iso > self.HIGH_ISO_THRESHOLD

            # Slow shutter speed indicates low-light (> 1/30s)
            if exif.exposure_time is not None:
                slow_shutter = exif.exposure_time > 1.0 / 30.0

        # Low-light if dark AND (high ISO OR slow shutter)
        # Or if very dark regardless of EXIF
        if mean_luminance < 0.2 or is_dark and (high_iso or slow_shutter):  # Very dark
            return True

        return False
