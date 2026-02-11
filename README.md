# HEIC to JPG Converter

A Python application that converts iPhone HEIC photos to high-quality JPG format optimized for silver halide (analog) printing.

## Features

- **High Quality**: Default quality 100 (minimal JPEG compression) for optimal print quality
- **Per-Image Optimization**: Each photo is analyzed and optimized individually
- **Parallel Processing**: Fast batch conversion using multiple CPU cores
- **EXIF Preservation**: Maintains all metadata from original files
- **Cross-Platform**: Works on macOS, Windows, and Linux
- **Smart Adjustments**: Handles challenging lighting conditions (overexposed, backlit, low-light)

## Requirements

- Python 3.14 or higher
- uv package manager

## Installation

```bash
# Install uv if you haven't already
pip install uv

# Clone the repository
git clone https://github.com/yourusername/heic-to-jpg-converter.git
cd heic-to-jpg-converter

# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

## Usage

```bash
# Convert a single file
heic-converter input.heic

# Convert with custom quality
heic-converter input.heic --quality 95

# Batch convert directory
heic-converter *.heic --output-dir ./converted

# Batch convert with no overwrite
heic-converter *.heic --no-overwrite

# Verbose logging
heic-converter input.heic --verbose

# Show help
heic-converter --help

# Show version
heic-converter --version
```

## Development

### Setup

```bash
# Install development dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src

# Run formatting
uv run ruff format .
```

### Testing

The project uses both unit tests and property-based tests:

```bash
# Run all tests
uv run pytest

# Run only unit tests
uv run pytest tests/unit

# Run only property tests
uv run pytest tests/property -v --hypothesis-show-statistics

# Run with coverage
uv run pytest --cov=heic_converter --cov-report=html
```

## Documentation

- [中文文档](README.zh-CN.md) - Chinese documentation
- [AGENTS.md](AGENTS.md) - AI agent guidance
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines

## License

MIT License - see LICENSE file for details

## Status

🚧 **Under Development** - This project is currently in active development.
