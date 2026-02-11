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

### Prerequisites

1. **Python 3.14+**: Ensure Python 3.14 or higher is installed
   ```bash
   python --version  # Should show 3.14.x or higher
   ```

2. **uv package manager**: If you don't have uv installed
   ```bash
   pip install uv
   ```

### Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/cnkang/heic2jpg.git
cd heic2jpg

# 2. Install dependencies
uv sync

# 3. Install the command-line tool (in development mode)
uv pip install -e .

# 4. Verify installation
heic-converter --version
```

After installation, the `heic-converter` command will be available from any directory.

### Quick Test

```bash
# Test conversion (assuming you have a test.heic file)
heic-converter test.heic

# If you don't have HEIC files, run tests to ensure everything works
uv run pytest tests/unit -v
```

## Usage

### Single File Conversion

```bash
# Convert a single file (output to same directory)
heic-converter photo.heic

# Convert with custom quality
heic-converter photo.heic --quality 95

# Convert to specific directory
heic-converter photo.heic --output-dir ./converted
```

### Batch Convert All HEIC Files in a Directory

```bash
# Method 1: Use wildcards (recommended)
heic-converter *.heic

# Method 2: Use wildcards with output directory
heic-converter *.heic --output-dir ./converted

# Method 3: Explicitly specify multiple files
heic-converter photo1.heic photo2.heic photo3.heic

# Method 4: Batch convert without overwriting existing files
heic-converter *.heic --no-overwrite

# Method 5: Batch convert with verbose logging
heic-converter *.heic --verbose
```

### Advanced Usage

```bash
# Batch convert with custom quality and output directory
heic-converter *.heic --quality 95 --output-dir ./converted

# Batch convert without overwriting, with verbose logging
heic-converter *.heic --no-overwrite --verbose

# Show help
heic-converter --help

# Show version
heic-converter --version
```

### Usage Examples

Suppose you have a directory with multiple iPhone photos:

```bash
# Current directory structure
photos/
  ├── IMG_0001.heic
  ├── IMG_0002.heic
  ├── IMG_0003.heic
  └── IMG_0004.heic

# Navigate to photos directory
cd photos

# Batch convert all HEIC files to current directory
heic-converter *.heic

# Directory structure after conversion
photos/
  ├── IMG_0001.heic
  ├── IMG_0001.jpg    ← newly created
  ├── IMG_0002.heic
  ├── IMG_0002.jpg    ← newly created
  ├── IMG_0003.heic
  ├── IMG_0003.jpg    ← newly created
  ├── IMG_0004.heic
  └── IMG_0004.jpg    ← newly created
```

Or output to a separate directory:

```bash
# Batch convert and output to converted directory
heic-converter *.heic --output-dir ./converted

# Directory structure after conversion
photos/
  ├── IMG_0001.heic
  ├── IMG_0002.heic
  ├── IMG_0003.heic
  ├── IMG_0004.heic
  └── converted/
      ├── IMG_0001.jpg
      ├── IMG_0002.jpg
      ├── IMG_0003.jpg
      └── IMG_0004.jpg
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
