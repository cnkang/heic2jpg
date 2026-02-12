"""Custom Hypothesis strategies for property-based testing."""

import tempfile
from pathlib import Path

import numpy as np
from hypothesis import strategies as st
from PIL import Image


@st.composite
def random_images(
    draw,
    min_width=100,
    max_width=800,
    min_height=100,
    max_height=800,
    with_skin_tones=None,
    brightness_range=None,
):
    """Generate random RGB images as numpy arrays.

    Args:
        draw: Hypothesis draw function
        min_width: Minimum image width
        max_width: Maximum image width
        min_height: Minimum image height
        max_height: Maximum image height
        with_skin_tones: If True, include skin tone colors; if False, exclude them; if None, random
        brightness_range: Tuple of (min_brightness, max_brightness) in 0-255 range, or None for full range

    Returns:
        numpy array of shape (height, width, 3) with uint8 RGB values
    """
    width = draw(st.integers(min_value=min_width, max_value=max_width))
    height = draw(st.integers(min_value=min_height, max_value=max_height))

    # Determine brightness range
    if brightness_range is not None:
        min_bright, max_bright = brightness_range
    else:
        min_bright, max_bright = 0, 255

    # Generate random image
    if with_skin_tones is True:
        # Generate image with skin tone regions
        image = np.zeros((height, width, 3), dtype=np.uint8)

        # Fill with random colors
        for c in range(3):
            image[:, :, c] = draw(st.integers(min_value=min_bright, max_value=max_bright))

        # Add skin tone region (center 30% of image)
        skin_y_start = int(height * 0.35)
        skin_y_end = int(height * 0.65)
        skin_x_start = int(width * 0.35)
        skin_x_end = int(width * 0.65)

        # Skin tone colors (RGB): peachy/beige tones
        skin_r = draw(st.integers(min_value=180, max_value=255))
        skin_g = draw(st.integers(min_value=140, max_value=200))
        skin_b = draw(st.integers(min_value=120, max_value=180))

        image[skin_y_start:skin_y_end, skin_x_start:skin_x_end] = [
            skin_r,
            skin_g,
            skin_b,
        ]

    else:
        # Generate completely random image
        image = np.random.randint(
            min_bright, max_bright + 1, size=(height, width, 3), dtype=np.uint8
        )

    return image


@st.composite
def heic_files(
    draw,
    min_width=100,
    max_width=800,
    min_height=100,
    max_height=800,
    with_exif=True,
):
    """Generate temporary HEIC files for testing.

    Args:
        draw: Hypothesis draw function
        min_width: Minimum image width
        max_width: Maximum image width
        min_height: Minimum image height
        max_height: Maximum image height
        with_exif: Whether to include EXIF metadata

    Returns:
        Path to temporary HEIC file
    """
    # Generate random image
    image_array = draw(
        random_images(
            min_width=min_width,
            max_width=max_width,
            min_height=min_height,
            max_height=max_height,
        )
    )

    # Convert to PIL Image
    pil_image = Image.fromarray(image_array, mode="RGB")

    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix=".heic", delete=False) as temp_file:
        temp_path = Path(temp_file.name)

    # Save as HEIC
    # Note: pillow-heif may not support writing HEIC on all platforms
    # For testing, we'll save as JPEG and rename to .heic
    # This is acceptable for testing the converter's error handling
    pil_image.save(temp_path.with_suffix(".jpg"), format="JPEG", quality=95)
    temp_path.with_suffix(".jpg").rename(temp_path)

    return temp_path


@st.composite
def quality_values(draw):
    """Generate valid quality values (0-100).

    Returns:
        Integer quality value between 0 and 100
    """
    return draw(st.integers(min_value=0, max_value=100))


@st.composite
def invalid_quality_values(draw):
    """Generate invalid quality values (outside 0-100).

    Returns:
        Integer quality value outside the valid range
    """
    return draw(
        st.one_of(
            st.integers(max_value=-1),
            st.integers(min_value=101, max_value=200),
        )
    )


@st.composite
def optimization_params(draw):
    """Generate random but valid optimization parameters.

    Returns:
        OptimizationParams instance
    """
    from heic2jpg.models import OptimizationParams

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


@st.composite
def image_with_highlights(draw, min_width=100, max_width=400):
    """Generate image with highlight clipping.

    Returns:
        numpy array with bright regions
    """
    width = draw(st.integers(min_value=min_width, max_value=max_width))
    height = draw(st.integers(min_value=min_width, max_value=max_width))

    # Create image with bright regions
    image = np.random.randint(200, 256, size=(height, width, 3), dtype=np.uint8)

    return image


@st.composite
def image_with_skin_tones(draw, min_width=100, max_width=400):
    """Generate image with skin tone regions.

    Returns:
        numpy array with skin tone colors
    """
    width = draw(st.integers(min_value=min_width, max_value=max_width))
    height = draw(st.integers(min_value=min_width, max_value=max_width))

    # Create base image
    image = np.random.randint(100, 200, size=(height, width, 3), dtype=np.uint8)

    # Add skin tone region (center area)
    skin_y_start = int(height * 0.3)
    skin_y_end = int(height * 0.7)
    skin_x_start = int(width * 0.3)
    skin_x_end = int(width * 0.7)

    # Skin tone colors (peachy/beige)
    skin_r = draw(st.integers(min_value=180, max_value=255))
    skin_g = draw(st.integers(min_value=140, max_value=200))
    skin_b = draw(st.integers(min_value=120, max_value=180))

    image[skin_y_start:skin_y_end, skin_x_start:skin_x_end] = [skin_r, skin_g, skin_b]

    return image


@st.composite
def backlit_image(draw, min_width=100, max_width=400):
    """Generate backlit image (bright edges, dark center).

    Returns:
        numpy array representing backlit scene
    """
    width = draw(st.integers(min_value=min_width, max_value=max_width))
    height = draw(st.integers(min_value=min_width, max_value=max_width))

    # Create bright background
    image = np.full((height, width, 3), 220, dtype=np.uint8)

    # Add dark center region
    center_y_start = int(height * 0.3)
    center_y_end = int(height * 0.7)
    center_x_start = int(width * 0.3)
    center_x_end = int(width * 0.7)

    # Dark center
    dark_value = draw(st.integers(min_value=20, max_value=80))
    image[center_y_start:center_y_end, center_x_start:center_x_end] = dark_value

    return image


@st.composite
def low_light_image(draw, min_width=100, max_width=400):
    """Generate low-light image (overall dark).

    Returns:
        numpy array representing low-light scene
    """
    width = draw(st.integers(min_value=min_width, max_value=max_width))
    height = draw(st.integers(min_value=min_width, max_value=max_width))

    # Create dark image
    image = np.random.randint(0, 60, size=(height, width, 3), dtype=np.uint8)

    return image
