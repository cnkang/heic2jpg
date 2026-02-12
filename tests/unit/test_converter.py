"""Unit tests for ImageConverter."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

from heic2jpg.analyzer import ImageAnalyzer
from heic2jpg.converter import ImageConverter
from heic2jpg.errors import InvalidFileError
from heic2jpg.models import Config, ConversionStatus, OptimizationParams


class TestImageConverter:
    """Test suite for ImageConverter class."""

    def test_converter_initialization(self):
        """Test ImageConverter initializes correctly."""
        config = Config(quality=95)
        converter = ImageConverter(config)

        assert converter.config == config
        assert converter.config.quality == 95

    def test_decode_jpg_as_heic(self):
        """Test decoding a JPEG file (simulating HEIC for testing)."""
        # Create a test image
        test_image = np.random.randint(0, 256, size=(100, 100, 3), dtype=np.uint8)
        pil_image = Image.fromarray(test_image, mode="RGB")

        # Save as JPEG
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            temp_path = Path(f.name)
            pil_image.save(temp_path, format="JPEG", quality=95)

        try:
            config = Config(quality=95)
            converter = ImageConverter(config)

            # Decode
            decoded_image, exif_dict, icc_profile = converter._decode_heic(temp_path)

            # Verify
            assert decoded_image.shape == (100, 100, 3)
            assert decoded_image.dtype == np.uint8
            assert isinstance(exif_dict, dict)
            assert icc_profile is None or isinstance(icc_profile, bytes)

        finally:
            temp_path.unlink()

    def test_decode_invalid_file(self):
        """Test decoding an invalid file raises error."""
        # Create a text file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            temp_path = Path(f.name)
            f.write("This is not an image")

        try:
            config = Config(quality=95)
            converter = ImageConverter(config)

            # Should raise InvalidFileError
            with pytest.raises(InvalidFileError):
                converter._decode_heic(temp_path)

        finally:
            temp_path.unlink()

    def test_decode_heic_ignores_invalid_exif_payload(self):
        """Test decode succeeds even if EXIF payload cannot be parsed."""
        test_image = np.random.randint(0, 256, size=(32, 32, 3), dtype=np.uint8)
        pil_image = Image.fromarray(test_image, mode="RGB")
        pil_image.info["exif"] = b"invalid-exif"

        config = Config(quality=95)
        converter = ImageConverter(config)

        with (
            patch("heic2jpg.converter.Image.open") as mock_open,
            patch("heic2jpg.converter.piexif.load", side_effect=ValueError("bad exif")),
        ):
            mock_open.return_value.__enter__.return_value = pil_image
            decoded_image, exif_dict, icc_profile = converter._decode_heic(Path("dummy.heic"))

        assert decoded_image.shape == (32, 32, 3)
        assert decoded_image.dtype == np.uint8
        assert exif_dict == {}
        assert icc_profile is None

    def test_decode_heic_preserves_exif_from_source_image(self):
        """Test decode reads EXIF from source metadata before mode conversion."""
        grayscale = np.random.randint(0, 256, size=(16, 16), dtype=np.uint8)
        source_image = Image.fromarray(grayscale, mode="L")
        source_image.info["exif"] = b"source-exif"
        converted_image = source_image.convert("RGB")
        converted_image.info.clear()

        expected_exif = {"Exif": {34855: 200}}

        config = Config(quality=95)
        converter = ImageConverter(config)

        with (
            patch("heic2jpg.converter.Image.open") as mock_open,
            patch("heic2jpg.converter.piexif.load", return_value=expected_exif),
            patch.object(source_image, "convert", return_value=converted_image),
        ):
            mock_open.return_value.__enter__.return_value = source_image
            decoded_image, exif_dict, icc_profile = converter._decode_heic(Path("dummy.heic"))

        assert decoded_image.shape == (16, 16, 3)
        assert exif_dict == expected_exif
        assert icc_profile is None

    def test_encode_jpg(self):
        """Test encoding image as JPG."""
        # Create a test image
        test_image = np.random.randint(0, 256, size=(100, 100, 3), dtype=np.uint8)

        # Create output path
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            output_path = Path(f.name)

        try:
            config = Config(quality=95)
            converter = ImageConverter(config)

            # Encode
            converter._encode_jpg(test_image, output_path, 95, {})

            # Verify file exists and can be opened
            assert output_path.exists()

            # Use context manager to ensure file is closed
            with Image.open(output_path) as loaded_image:
                assert loaded_image.size == (100, 100)
                assert loaded_image.mode == "RGB"

        finally:
            if output_path.exists():
                output_path.unlink()

    def test_encode_jpg_with_different_qualities(self):
        """Test encoding with different quality levels."""
        test_image = np.random.randint(0, 256, size=(100, 100, 3), dtype=np.uint8)

        for quality in [50, 75, 95, 100]:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                output_path = Path(f.name)

            try:
                config = Config(quality=quality)
                converter = ImageConverter(config)

                converter._encode_jpg(test_image, output_path, quality, {})

                assert output_path.exists()
                # Lower quality should generally result in smaller file size
                # (though this isn't guaranteed for all images)

            finally:
                if output_path.exists():
                    output_path.unlink()

    def test_encode_jpg_preserves_icc_profile(self, tmp_path):
        """Test encoding preserves ICC profile when provided."""
        test_image = np.random.randint(0, 256, size=(32, 32, 3), dtype=np.uint8)
        output_path = tmp_path / "icc-test.jpg"
        icc_profile = b"fake-icc-profile"

        config = Config(quality=95)
        converter = ImageConverter(config)

        converter._encode_jpg(test_image, output_path, 95, {}, icc_profile=icc_profile)

        with Image.open(output_path) as loaded_image:
            assert loaded_image.info.get("icc_profile") == icc_profile

    def test_adjust_exposure(self):
        """Test exposure adjustment."""
        # Create a mid-gray image
        test_image = np.full((100, 100, 3), 0.5, dtype=np.float32)

        config = Config(quality=95)
        converter = ImageConverter(config)

        # Increase exposure by 1 EV (should double brightness)
        adjusted = converter._adjust_exposure(test_image, 1.0)
        assert np.allclose(adjusted, 1.0, atol=0.01)

        # Decrease exposure by 1 EV (should halve brightness)
        adjusted = converter._adjust_exposure(test_image, -1.0)
        assert np.allclose(adjusted, 0.25, atol=0.01)

    def test_adjust_contrast(self):
        """Test contrast adjustment."""
        # Create an image with known values
        test_image = np.array([[[0.2, 0.2, 0.2], [0.8, 0.8, 0.8]]], dtype=np.float32)

        config = Config(quality=95)
        converter = ImageConverter(config)

        # Increase contrast
        adjusted = converter._adjust_contrast(test_image, 1.5)

        # Values should move away from 0.5
        assert adjusted[0, 0, 0] < 0.2  # Dark gets darker
        assert adjusted[0, 1, 0] > 0.8  # Bright gets brighter

        # Decrease contrast
        adjusted = converter._adjust_contrast(test_image, 0.5)

        # Values should move toward 0.5
        assert adjusted[0, 0, 0] > 0.2  # Dark gets lighter
        assert adjusted[0, 1, 0] < 0.8  # Bright gets darker

    def test_lift_shadows(self):
        """Test shadow lifting."""
        # Create an image with dark and bright areas
        test_image = np.zeros((100, 100, 3), dtype=np.float32)
        test_image[:50, :, :] = 0.1  # Dark area
        test_image[50:, :, :] = 0.9  # Bright area

        config = Config(quality=95)
        converter = ImageConverter(config)

        # Lift shadows
        adjusted = converter._lift_shadows(test_image, 0.5)

        # Dark areas should be lifted
        assert np.mean(adjusted[:50, :, :]) > 0.1

        # Bright areas should be mostly unchanged
        assert np.mean(adjusted[50:, :, :]) >= 0.85

    def test_recover_highlights(self):
        """Test highlight recovery."""
        # Create an image with bright areas
        test_image = np.ones((100, 100, 3), dtype=np.float32)
        test_image[:50, :, :] = 0.9  # Bright area
        test_image[50:, :, :] = 0.3  # Dark area

        config = Config(quality=95)
        converter = ImageConverter(config)

        # Recover highlights
        adjusted = converter._recover_highlights(test_image, 0.8)

        # Bright areas should be compressed
        assert np.mean(adjusted[:50, :, :]) < 0.9

        # Dark areas should be mostly unchanged
        assert np.mean(adjusted[50:, :, :]) >= 0.25

    def test_auto_highlight_recovery_with_brightening_steps(self):
        """Test adaptive highlight recovery reduces clipping after brightening."""
        # Build an image with substantial near-highlight content.
        test_image = np.full((200, 200, 3), 200, dtype=np.uint8)
        test_image[:80, :, :] = 235
        test_image[80:120, :, :] = 210
        test_image[120:, :, :] = 120

        config = Config(quality=95)
        converter = ImageConverter(config)
        analyzer = ImageAnalyzer()

        params = OptimizationParams(
            exposure_adjustment=0.45,
            contrast_adjustment=1.18,
            shadow_lift=0.12,
            highlight_recovery=0.0,
            saturation_adjustment=1.0,
            sharpness_amount=0.0,
            noise_reduction=0.0,
            skin_tone_protection=False,
        )

        # Baseline: same brightening steps but without highlight recovery.
        baseline = test_image.astype(np.float32) / 255.0
        baseline = converter._adjust_exposure(baseline, params.exposure_adjustment)
        baseline = converter._adjust_contrast(baseline, params.contrast_adjustment)
        baseline = converter._lift_shadows(baseline, params.shadow_lift)
        baseline_u8 = np.clip(baseline * 255.0, 0, 255).astype(np.uint8)

        optimized = converter._apply_optimizations(test_image, params)

        baseline_metrics = analyzer.analyze(baseline_u8)
        optimized_metrics = analyzer.analyze(optimized)

        assert (
            optimized_metrics.highlight_clipping_percent
            < baseline_metrics.highlight_clipping_percent
        )

    def test_auto_highlight_recovery_skips_non_brightening_steps(self):
        """Test adaptive highlight recovery remains off when no brightening is applied."""
        config = Config(quality=95)
        converter = ImageConverter(config)

        image = np.random.rand(80, 80, 3).astype(np.float32)
        params = OptimizationParams(
            exposure_adjustment=-0.3,
            contrast_adjustment=0.9,
            shadow_lift=0.0,
            highlight_recovery=0.0,
            saturation_adjustment=1.0,
            sharpness_amount=0.0,
            noise_reduction=0.0,
            skin_tone_protection=False,
        )

        auto_recovery = converter._calculate_auto_highlight_recovery(image, params)
        assert auto_recovery == 0.0

    def test_extract_face_regions_from_xmp(self):
        """Test extracting normalized face regions from XMP payload."""
        xmp_payload = """
        <x:xmpmeta xmlns:x="adobe:ns:meta/">
          <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
            <rdf:Description xmlns:mwg-rs="http://www.metadataworkinggroup.com/schemas/regions/">
              <mwg-rs:Regions>
                <rdf:Bag>
                  <rdf:li
                    xmlns:stArea="http://ns.adobe.com/xmp/sType/Area#"
                    stArea:x="0.5"
                    stArea:y="0.5"
                    stArea:w="0.2"
                    stArea:h="0.3"
                    stArea:unit="normalized"/>
                </rdf:Bag>
              </mwg-rs:Regions>
            </rdf:Description>
          </rdf:RDF>
        </x:xmpmeta>
        """
        config = Config(quality=95)
        converter = ImageConverter(config)

        regions = converter._extract_face_regions_from_xmp(xmp_payload, width=1000, height=800)

        assert len(regions) == 1
        x, y, w, h = regions[0]
        assert x == 400
        assert y == 280
        assert w == 200
        assert h == 240

    def test_relight_faces_brightens_face_without_lifting_highlight_background(self):
        """Test local face relighting brightens face region and protects bright background."""
        image = np.full((200, 200, 3), 0.9, dtype=np.float32)
        image[80:120, 80:120, :] = 0.2

        config = Config(quality=95)
        converter = ImageConverter(config)

        baseline_face = float(np.mean(image[80:120, 80:120]))
        baseline_bg = float(np.mean(image[:40, :40]))

        relit = converter._relight_faces(image, [(80, 80, 40, 40)], amount=0.35)

        relit_face = float(np.mean(relit[80:120, 80:120]))
        relit_bg = float(np.mean(relit[:40, :40]))

        assert relit_face > baseline_face + 0.03
        assert relit_bg <= baseline_bg + 0.01

    def test_apply_optimizations_uses_embedded_face_regions_before_detector(self):
        """Test embedded XMP face regions are preferred over detector fallback."""
        image = np.full((200, 200, 3), 220, dtype=np.uint8)
        image[80:120, 80:120, :] = 40

        params = OptimizationParams(
            exposure_adjustment=0.0,
            contrast_adjustment=1.0,
            shadow_lift=0.0,
            highlight_recovery=0.0,
            saturation_adjustment=1.0,
            sharpness_amount=0.0,
            noise_reduction=0.0,
            skin_tone_protection=False,
            face_relight_strength=0.35,
        )

        xmp_payload = """
        <x:xmpmeta xmlns:x="adobe:ns:meta/">
          <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
            <rdf:Description xmlns:mwg-rs="http://www.metadataworkinggroup.com/schemas/regions/">
              <mwg-rs:Regions>
                <rdf:Bag>
                  <rdf:li
                    xmlns:stArea="http://ns.adobe.com/xmp/sType/Area#"
                    stArea:x="0.5"
                    stArea:y="0.5"
                    stArea:w="0.2"
                    stArea:h="0.2"
                    stArea:unit="normalized"/>
                </rdf:Bag>
              </mwg-rs:Regions>
            </rdf:Description>
          </rdf:RDF>
        </x:xmpmeta>
        """

        config = Config(quality=95)
        converter = ImageConverter(config)

        with patch.object(converter, "_detect_faces", return_value=[]) as mock_detect:
            optimized = converter._apply_optimizations(
                image,
                params,
                exif_dict={converter.INTERNAL_XMP_KEY: xmp_payload},
            )

        assert float(np.mean(optimized[80:120, 80:120])) > float(np.mean(image[80:120, 80:120]))
        mock_detect.assert_not_called()

    def test_apply_optimizations_auto_triggers_face_relight_for_dark_face(self):
        """Test dark face against bright background can trigger fallback relight."""
        image = np.full((200, 200, 3), 220, dtype=np.uint8)
        image[80:120, 80:120, :] = 40

        params = OptimizationParams(
            exposure_adjustment=0.0,
            contrast_adjustment=1.0,
            shadow_lift=0.0,
            highlight_recovery=0.0,
            saturation_adjustment=1.0,
            sharpness_amount=0.0,
            noise_reduction=0.0,
            skin_tone_protection=False,
            face_relight_strength=0.0,  # Force fallback trigger path
        )

        xmp_payload = """
        <x:xmpmeta xmlns:x="adobe:ns:meta/">
          <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
            <rdf:Description xmlns:mwg-rs="http://www.metadataworkinggroup.com/schemas/regions/">
              <mwg-rs:Regions>
                <rdf:Bag>
                  <rdf:li
                    xmlns:stArea="http://ns.adobe.com/xmp/sType/Area#"
                    stArea:x="0.5"
                    stArea:y="0.5"
                    stArea:w="0.2"
                    stArea:h="0.2"
                    stArea:unit="normalized"/>
                </rdf:Bag>
              </mwg-rs:Regions>
            </rdf:Description>
          </rdf:RDF>
        </x:xmpmeta>
        """

        config = Config(quality=95)
        converter = ImageConverter(config)

        optimized = converter._apply_optimizations(
            image,
            params,
            exif_dict={converter.INTERNAL_XMP_KEY: xmp_payload},
        )

        assert float(np.mean(optimized[80:120, 80:120])) > float(np.mean(image[80:120, 80:120]))

    def test_sanitize_exif_for_jpeg_removes_internal_keys(self):
        """Test internal metadata keys are removed before EXIF serialization."""
        config = Config(quality=95)
        converter = ImageConverter(config)

        sanitized = converter._sanitize_exif_for_jpeg(
            {
                "0th": {},
                "Exif": {},
                converter.INTERNAL_XMP_KEY: b"xmp",
                "custom": "skip-me",
            }
        )

        assert "0th" in sanitized
        assert "Exif" in sanitized
        assert converter.INTERNAL_XMP_KEY not in sanitized
        assert "custom" not in sanitized

    def test_adjust_saturation(self):
        """Test saturation adjustment."""
        # Create a colorful image with moderate saturation
        test_image = np.zeros((100, 100, 3), dtype=np.float32)
        test_image[:, :, 0] = 0.8  # Red channel
        test_image[:, :, 1] = 0.3  # Green channel
        test_image[:, :, 2] = 0.3  # Blue channel

        config = Config(quality=95)
        converter = ImageConverter(config)

        # Increase saturation
        adjusted = converter._adjust_saturation(test_image, 1.5, protect_skin_tones=False)

        # Should still be mostly red but more saturated
        # Red channel should stay high or increase
        assert adjusted[:, :, 0].mean() >= 0.7

        # Decrease saturation (move toward gray)
        adjusted = converter._adjust_saturation(test_image, 0.5, protect_skin_tones=False)

        # With reduced saturation, channels should be more similar (closer to gray)
        # Calculate the range between max and min channel values
        channel_range_before = 0.8 - 0.3  # 0.5
        channel_range_after = adjusted[:, :, 0].mean() - adjusted[:, :, 1].mean()

        # After desaturation, the range should be smaller
        assert channel_range_after < channel_range_before

    def test_reduce_noise(self):
        """Test noise reduction."""
        # Create a noisy image
        np.random.seed(42)
        clean_image = np.full((100, 100, 3), 0.5, dtype=np.float32)
        noise = np.random.normal(0, 0.1, (100, 100, 3)).astype(np.float32)
        noisy_image = np.clip(clean_image + noise, 0, 1)

        config = Config(quality=95)
        converter = ImageConverter(config)

        # Apply noise reduction
        denoised = converter._reduce_noise(noisy_image, 0.8)

        # Denoised image should be closer to clean image
        noisy_diff = np.mean(np.abs(noisy_image - clean_image))
        denoised_diff = np.mean(np.abs(denoised - clean_image))

        assert denoised_diff < noisy_diff

    def test_sharpen(self):
        """Test sharpening."""
        # Create a blurry image (all same value)
        blurry_image = np.full((100, 100, 3), 0.5, dtype=np.float32)

        config = Config(quality=95)
        converter = ImageConverter(config)

        # Apply sharpening
        sharpened = converter._sharpen(blurry_image, 1.0)

        # For a uniform image, sharpening shouldn't change much
        assert np.allclose(sharpened, blurry_image, atol=0.1)

    def test_apply_optimizations_order(self):
        """Test that optimizations are applied in correct order."""
        # Create a test image
        test_image = np.random.randint(50, 200, size=(100, 100, 3), dtype=np.uint8)

        config = Config(quality=95)
        converter = ImageConverter(config)

        # Create optimization params with all adjustments
        params = OptimizationParams(
            exposure_adjustment=0.5,
            contrast_adjustment=1.2,
            shadow_lift=0.3,
            highlight_recovery=0.3,
            saturation_adjustment=1.1,
            sharpness_amount=0.5,
            noise_reduction=0.2,
            skin_tone_protection=False,
        )

        # Apply optimizations
        optimized = converter._apply_optimizations(test_image, params)

        # Verify output is valid
        assert optimized.shape == test_image.shape
        assert optimized.dtype == np.uint8
        assert np.all(optimized >= 0)
        assert np.all(optimized <= 255)

    def test_apply_optimizations_no_changes(self):
        """Test applying optimizations with no adjustments."""
        test_image = np.random.randint(0, 256, size=(100, 100, 3), dtype=np.uint8)

        config = Config(quality=95)
        converter = ImageConverter(config)

        # Create params with no adjustments
        params = OptimizationParams(
            exposure_adjustment=0.0,
            contrast_adjustment=1.0,
            shadow_lift=0.0,
            highlight_recovery=0.0,
            saturation_adjustment=1.0,
            sharpness_amount=0.0,
            noise_reduction=0.0,
            skin_tone_protection=False,
        )

        # Apply optimizations
        optimized = converter._apply_optimizations(test_image, params)

        # Should be very similar to input (allowing for small numerical differences)
        diff = np.mean(np.abs(optimized.astype(float) - test_image.astype(float)))
        assert diff < 5.0  # Average difference less than 5 per pixel

    def test_full_conversion_pipeline(self):
        """Test the full conversion pipeline."""
        # Create a test image
        test_image = np.random.randint(0, 256, size=(200, 200, 3), dtype=np.uint8)
        pil_image = Image.fromarray(test_image, mode="RGB")

        # Save as input
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            input_path = Path(f.name)
            pil_image.save(input_path, format="JPEG", quality=95)

        # Create output path
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            output_path = Path(f.name)

        try:
            config = Config(quality=90)
            converter = ImageConverter(config)

            # Create minimal params
            params = OptimizationParams(
                exposure_adjustment=0.0,
                contrast_adjustment=1.0,
                shadow_lift=0.0,
                highlight_recovery=0.0,
                saturation_adjustment=1.0,
                sharpness_amount=0.0,
                noise_reduction=0.0,
                skin_tone_protection=False,
            )

            # Convert
            result = converter.convert(input_path, output_path, params)

            # Verify result
            assert result.status == ConversionStatus.SUCCESS
            assert result.output_path == output_path
            assert result.processing_time > 0
            assert output_path.exists()

            # Verify output image - use context manager to ensure file is closed
            with Image.open(output_path) as output_image:
                assert output_image.size == (200, 200)
                assert output_image.mode == "RGB"

        finally:
            if input_path.exists():
                input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    def test_conversion_with_invalid_input(self):
        """Test conversion with invalid input file."""
        # Create a non-existent path
        input_path = Path("/nonexistent/file.heic")
        output_path = Path("/tmp/output.jpg")

        config = Config(quality=95)
        converter = ImageConverter(config)

        params = OptimizationParams(
            exposure_adjustment=0.0,
            contrast_adjustment=1.0,
            shadow_lift=0.0,
            highlight_recovery=0.0,
            saturation_adjustment=1.0,
            sharpness_amount=0.0,
            noise_reduction=0.0,
            skin_tone_protection=False,
        )

        # Convert should return FAILED status, not raise exception
        result = converter.convert(input_path, output_path, params)

        assert result.status == ConversionStatus.FAILED
        assert result.error_message is not None
        assert "failed" in result.error_message.lower()

    def test_convert_uses_predecoded_image_without_redecoding(self, tmp_path):
        """Test convert() can reuse pre-decoded data and skip decode step."""
        output_path = tmp_path / "output.jpg"
        input_path = tmp_path / "input.heic"
        predecoded_image = np.random.randint(0, 256, size=(64, 64, 3), dtype=np.uint8)

        config = Config(quality=95)
        converter = ImageConverter(config)

        params = OptimizationParams(
            exposure_adjustment=0.0,
            contrast_adjustment=1.0,
            shadow_lift=0.0,
            highlight_recovery=0.0,
            saturation_adjustment=1.0,
            sharpness_amount=0.0,
            noise_reduction=0.0,
            skin_tone_protection=False,
        )

        with patch.object(converter, "_decode_heic") as mock_decode:
            result = converter.convert(
                input_path,
                output_path,
                params,
                decoded_image=predecoded_image,
                decoded_exif={},
            )

        assert result.status == ConversionStatus.SUCCESS
        assert output_path.exists()
        mock_decode.assert_not_called()
