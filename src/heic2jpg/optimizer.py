"""Optimization parameter generator for HEIC to JPG converter."""

import numpy as np

from heic2jpg.models import (
    ImageMetrics,
    OptimizationParams,
    StylePreferences,
)


class OptimizationParamGenerator:
    """Generate per-image optimization parameters based on analysis and style preferences."""

    def __init__(self, style_prefs: StylePreferences):
        """Initialize with style preferences.

        Args:
            style_prefs: Style preferences for optimization
        """
        self.style_prefs = style_prefs

    def generate(self, metrics: ImageMetrics) -> OptimizationParams:
        """Generate optimization parameters from metrics and style preferences.

        Args:
            metrics: Image analysis metrics

        Returns:
            OptimizationParams with calculated adjustments
        """
        # Calculate each parameter based on metrics and style preferences
        exposure_adjustment = self._calculate_exposure_adjustment(metrics)
        contrast_adjustment = self._calculate_contrast_adjustment(metrics)
        highlight_recovery = self._calculate_highlight_recovery(metrics)
        shadow_lift = self._calculate_shadow_lift(metrics)
        face_relight_strength = self._calculate_face_relight_strength(metrics)
        saturation_adjustment = self._calculate_saturation_adjustment(metrics)
        sharpness_amount = self._calculate_sharpness(metrics)
        noise_reduction = self._calculate_noise_reduction(metrics)
        skin_tone_protection = metrics.skin_tone_detected and self.style_prefs.stable_skin_tones

        return OptimizationParams(
            exposure_adjustment=exposure_adjustment,
            contrast_adjustment=contrast_adjustment,
            shadow_lift=shadow_lift,
            highlight_recovery=highlight_recovery,
            face_relight_strength=face_relight_strength,
            saturation_adjustment=saturation_adjustment,
            sharpness_amount=sharpness_amount,
            noise_reduction=noise_reduction,
            skin_tone_protection=skin_tone_protection,
        )

    def _calculate_exposure_adjustment(self, metrics: ImageMetrics) -> float:
        """Calculate exposure adjustment to target middle gray.

        Args:
            metrics: Image analysis metrics

        Returns:
            Exposure adjustment in EV (-2.0 to +2.0)
        """
        # Target is 0 EV (properly exposed)
        # Apply gentle correction towards target
        if self.style_prefs.natural_appearance:
            # Subtle adjustment - only correct 50% of the way
            adjustment = -metrics.exposure_level * 0.5
        else:
            # More aggressive adjustment - correct 80% of the way
            adjustment = -metrics.exposure_level * 0.8

        # Clamp to reasonable range
        return float(np.clip(adjustment, -2.0, 2.0))

    def _calculate_contrast_adjustment(self, metrics: ImageMetrics) -> float:
        """Calculate contrast adjustment for natural appearance.

        Args:
            metrics: Image analysis metrics

        Returns:
            Contrast multiplier (0.5 to 1.5)
        """
        # Target contrast is around 0.6-0.7 for natural appearance
        target_contrast = 0.65

        if self.style_prefs.natural_appearance:
            # Subtle adjustment
            if metrics.contrast_level < target_contrast:
                # Increase contrast slightly
                adjustment = 1.0 + (target_contrast - metrics.contrast_level) * 0.3
            else:
                # Decrease contrast slightly
                adjustment = 1.0 - (metrics.contrast_level - target_contrast) * 0.2
        else:
            # More aggressive adjustment
            if metrics.contrast_level < target_contrast:
                adjustment = 1.0 + (target_contrast - metrics.contrast_level) * 0.5
            else:
                adjustment = 1.0 - (metrics.contrast_level - target_contrast) * 0.4

        # Clamp to reasonable range
        return float(np.clip(adjustment, 0.5, 1.5))

    def _calculate_highlight_recovery(self, metrics: ImageMetrics) -> float:
        """Calculate highlight recovery to preserve detail.

        Args:
            metrics: Image analysis metrics

        Returns:
            Highlight recovery amount (0.0 to 1.0)
        """
        if not self.style_prefs.preserve_highlights:
            # Minimal highlight recovery if not prioritized
            if metrics.highlight_clipping_percent > 10.0:
                return 0.3
            return 0.0

        # Aggressive highlight recovery based on clipping percentage
        if metrics.highlight_clipping_percent > 10.0:
            # Strong recovery for significant clipping
            recovery = 0.8 + (metrics.highlight_clipping_percent - 10.0) / 100.0
        elif metrics.highlight_clipping_percent > 5.0:
            # Moderate recovery for moderate clipping
            recovery = 0.5 + (metrics.highlight_clipping_percent - 5.0) / 20.0
        elif metrics.highlight_clipping_percent > 1.0:
            # Light recovery for minor clipping
            recovery = 0.2 + (metrics.highlight_clipping_percent - 1.0) / 20.0
        else:
            # No recovery needed
            recovery = 0.0

        # Proactive protection for backlit scenes where shadow lift may push highlights.
        if metrics.is_backlit and metrics.exposure_level > -0.2:
            recovery = max(recovery, 0.12)

        return float(np.clip(recovery, 0.0, 1.0))

    def _calculate_shadow_lift(self, metrics: ImageMetrics) -> float:
        """Calculate shadow lift to prevent crushing.

        Args:
            metrics: Image analysis metrics

        Returns:
            Shadow lift amount (0.0 to 1.0)
        """
        # Base shadow lift from measured clipping (conservative by default).
        if metrics.shadow_clipping_percent > 12.0:
            base_lift = 0.4
        elif metrics.shadow_clipping_percent > 6.0:
            base_lift = 0.2
        elif metrics.shadow_clipping_percent > 2.0:
            base_lift = 0.1
        else:
            base_lift = 0.0

        # Backlit scenes still need lift, but avoid globally flattening bright images.
        if metrics.is_backlit:
            backlit_lift = 0.18
            if metrics.exposure_level < -0.35:
                backlit_lift += 0.08
            if metrics.shadow_clipping_percent > 10.0:
                backlit_lift += 0.08
            if metrics.exposure_level > 0.2:
                backlit_lift -= 0.06
            if metrics.highlight_clipping_percent > 1.0:
                backlit_lift -= 0.05
            backlit_lift = float(np.clip(backlit_lift, 0.08, 0.32))
            base_lift = max(base_lift, backlit_lift)

        # Adjust based on EXIF flash information
        if metrics.exif_data and metrics.exif_data.flash_fired:
            # Reduce shadow lift if flash was used (shadows are already lifted)
            base_lift *= 0.5

        # Apply style preference (keep natural output conservative).
        lift = base_lift * 0.85 if self.style_prefs.natural_appearance else base_lift

        return float(np.clip(lift, 0.0, 1.0))

    def _calculate_saturation_adjustment(self, metrics: ImageMetrics) -> float:
        """Calculate saturation adjustment for natural colors.

        Args:
            metrics: Image analysis metrics

        Returns:
            Saturation multiplier (0.5 to 1.5)
        """
        # Target saturation is around 1.0 (normal)
        target_saturation = 1.0

        # Protect skin tones from over-saturation
        if metrics.skin_tone_detected and self.style_prefs.stable_skin_tones:
            # Very conservative saturation adjustment
            if metrics.saturation_level < target_saturation:
                adjustment = 1.0 + (target_saturation - metrics.saturation_level) * 0.1
            else:
                adjustment = 1.0 - (metrics.saturation_level - target_saturation) * 0.1
        elif self.style_prefs.avoid_filter_look:
            # Moderate saturation adjustment
            if metrics.saturation_level < target_saturation:
                adjustment = 1.0 + (target_saturation - metrics.saturation_level) * 0.2
            else:
                adjustment = 1.0 - (metrics.saturation_level - target_saturation) * 0.2
        else:
            # More aggressive saturation adjustment
            if metrics.saturation_level < target_saturation:
                adjustment = 1.0 + (target_saturation - metrics.saturation_level) * 0.3
            else:
                adjustment = 1.0 - (metrics.saturation_level - target_saturation) * 0.3

        return float(np.clip(adjustment, 0.5, 1.5))

    def _calculate_face_relight_strength(self, metrics: ImageMetrics) -> float:
        """Calculate local face relighting strength for backlit portraits.

        The value is conservative by default and primarily activates for
        backlit scenes with shadow pressure. It is intentionally reduced when
        highlight clipping is already high to avoid flattening bright backgrounds.

        Args:
            metrics: Image analysis metrics

        Returns:
            Face relighting strength (0.0 to 1.0)
        """
        if not metrics.is_backlit:
            return 0.0

        # Base activation for backlit scenes.
        strength = 0.18

        # Darker overall exposure generally means face region needs more lift.
        if metrics.exposure_level < -0.6:
            strength += 0.12
        elif metrics.exposure_level < -0.2:
            strength += 0.06

        # Heavy shadow clipping suggests subject-side tones are crushed.
        if metrics.shadow_clipping_percent > 10.0:
            strength += 0.12
        elif metrics.shadow_clipping_percent > 4.0:
            strength += 0.06

        # If skin tones are detected, the scene is more likely portrait-relevant.
        if metrics.skin_tone_detected:
            strength += 0.04

        # Strong highlight clipping means we should avoid aggressive local lift.
        if metrics.highlight_clipping_percent > 6.0:
            strength -= 0.08
        elif metrics.highlight_clipping_percent > 2.0:
            strength -= 0.04

        if self.style_prefs.natural_appearance:
            strength *= 0.85

        return float(np.clip(strength, 0.0, 0.6))

    def _calculate_sharpness(self, metrics: ImageMetrics) -> float:
        """Calculate sharpening amount based on current sharpness.

        Args:
            metrics: Image analysis metrics

        Returns:
            Sharpness amount (0.0 to 2.0)
        """
        # Target sharpness is around 0.6-0.7
        target_sharpness = 0.65

        if metrics.sharpness_score < target_sharpness:
            # Apply sharpening
            sharpness_deficit = target_sharpness - metrics.sharpness_score
            sharpness = sharpness_deficit * 2.0  # Scale to 0-2 range
        else:
            # Already sharp enough
            sharpness = 0.0

        # Reduce sharpening if heavy noise reduction will be applied
        # (to avoid amplifying noise)
        if metrics.noise_level > 0.5:
            sharpness *= 0.5

        # Apply style preference
        if self.style_prefs.natural_appearance:
            # Reduce sharpening for more natural look
            sharpness *= 0.7

        return float(np.clip(sharpness, 0.0, 2.0))

    def _calculate_noise_reduction(self, metrics: ImageMetrics) -> float:
        """Calculate noise reduction amount based on ISO and measured noise.

        Args:
            metrics: Image analysis metrics

        Returns:
            Noise reduction amount (0.0 to 1.0)
        """
        # Base noise reduction on measured noise level
        base_reduction = metrics.noise_level

        # Adjust based on ISO if available
        if metrics.exif_data and metrics.exif_data.iso is not None:
            iso = metrics.exif_data.iso

            # ISO-based noise reduction scaling
            if iso < 400:
                # Minimal noise reduction for low ISO
                iso_factor = 0.0
            elif iso < 800:
                # Moderate noise reduction for medium ISO
                iso_factor = (iso - 400) / 400 * 0.3  # 0.0 to 0.3
            elif iso < 1600:
                # Strong noise reduction for high ISO
                iso_factor = 0.3 + (iso - 800) / 800 * 0.2  # 0.3 to 0.5
            else:
                # Very strong noise reduction for very high ISO
                iso_factor = 0.5 + min((iso - 1600) / 1600 * 0.4, 0.4)  # 0.5 to 0.9

            # Combine measured noise and ISO factor (weighted average)
            reduction = 0.6 * base_reduction + 0.4 * iso_factor
        else:
            # Use measured noise only
            reduction = base_reduction

        # Increase noise reduction for low-light images
        if metrics.is_low_light:
            reduction = min(reduction * 1.2, 1.0)

        return float(np.clip(reduction, 0.0, 1.0))
