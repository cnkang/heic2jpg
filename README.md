# HEIC to JPG Converter

[![Tests](https://github.com/cnkang/heic2jpg/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/cnkang/heic2jpg/actions/workflows/test.yml)
[![Linting](https://github.com/cnkang/heic2jpg/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/cnkang/heic2jpg/actions/workflows/lint.yml)
[![Security](https://github.com/cnkang/heic2jpg/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/cnkang/heic2jpg/actions/workflows/security.yml)
[![Snyk Security](https://snyk.io/test/github/cnkang/heic2jpg/badge.svg)](https://app.snyk.io/org/cnkang/project/2f2047b4-1dda-4279-829d-288e99acd28a)
[![codecov](https://codecov.io/gh/cnkang/heic2jpg/graph/badge.svg?branch=main)](https://codecov.io/gh/cnkang/heic2jpg)
[![Python](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcnkang%2Fheic2jpg%2Fmain%2Fpyproject.toml&query=%24.project.requires-python&label=python&logo=python)](https://github.com/cnkang/heic2jpg/blob/main/pyproject.toml)
[![License: MIT](https://img.shields.io/github/license/cnkang/heic2jpg)](LICENSE)

A Python application that converts iPhone HEIC photos to high-quality JPG format optimized for silver halide (analog) printing.

## Status

- 🚧 **Alpha / In Active Development**
- ✅ **CI Checks**: tests, linting, and security scans run via GitHub Actions
- 📊 **Coverage**: tracked automatically with Codecov
- 📦 **Project ID**: `heic2jpg`

## Naming and Structure

- `heic2jpg` is the repository name, project identifier, and primary CLI command.
- `src/heic2jpg` is intentionally kept as the Python package namespace to avoid breaking existing imports and test/tooling integrations.
- `.kiro/specs/heic2jpg` keeps the spec directory aligned with the current project ID.

## Why This Is Not Reinventing the Wheel

- This project uses mature libraries (`pillow`, `pillow-heif`, `opencv-python`) instead of re-implementing image codecs or generic filters.
- The added value is print-focused optimization logic that generic converters do not provide: per-image analysis, adaptive adjustments, and conservative handling for backlit/highlight/low-light scenes.
- It preserves print-relevant metadata and workflow artifacts (EXIF, ICC profile, metrics JSON) for traceable quality review.
- It includes engineering guardrails for real usage: secure file/path validation, batch error isolation, and automated CI/security checks.

## Features

- **High Quality**: Default quality 100 (minimal JPEG compression) for optimal print quality
- **Per-Image Optimization**: Each photo is analyzed and optimized individually
- **Parallel Processing**: Fast batch conversion using multiple CPU cores
- **Metadata & Color Profile Preservation**: Preserves EXIF metadata and embedded ICC profile
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
heic2jpg --version
```

After installation, the `heic2jpg` command will be available from any directory.

### Quick Test

```bash
# Test conversion (assuming you have a test.heic file)
heic2jpg test.heic

# If you don't have HEIC files, run tests to ensure everything works
uv run pytest tests/unit -v
```

## Usage

### Single File Conversion

```bash
# Convert a single file (output to same directory)
heic2jpg photo.heic

# Convert with custom quality
heic2jpg photo.heic --quality 95

# Convert to specific directory
heic2jpg photo.heic --output-dir ./converted
```

### Batch Convert All HEIC Files in a Directory

```bash
# Method 1: Use wildcards (recommended)
heic2jpg *.heic

# Method 2: Use wildcards with output directory
heic2jpg *.heic --output-dir ./converted

# Method 3: Explicitly specify multiple files
heic2jpg photo1.heic photo2.heic photo3.heic

# Method 4: Batch convert without overwriting existing files
heic2jpg *.heic --no-overwrite

# Method 5: Batch convert with verbose logging
heic2jpg *.heic --verbose
```

### Advanced Usage

```bash
# Batch convert with custom quality and output directory
heic2jpg *.heic --quality 95 --output-dir ./converted

# Batch convert without overwriting, with verbose logging
heic2jpg *.heic --no-overwrite --verbose

# Show help
heic2jpg --help

# Show version
heic2jpg --version
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
heic2jpg *.heic

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
heic2jpg *.heic --output-dir ./converted

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
uv run pytest --cov=heic2jpg --cov-report=html
```

## Quality Validation and Manual Review

For optimization changes, validate on a diverse real-image sample set rather than a single case.

Recommended workflow:

```bash
# Convert a representative sample directory
heic2jpg samples/*.HEIC samples/*.heic --output-dir /tmp/sample-output
```

- Check flagged or borderline images manually (input vs output side-by-side).
- If automated metrics and visual quality disagree, prioritize human visual judgment.
- Keep a short review list of `input -> output` file pairs for final acceptance.

## Documentation

- [中文文档](README.zh-CN.md) - Chinese documentation
- [AGENTS.md](AGENTS.md) - AI agent guidance
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines

## License

MIT License - see LICENSE file for details

## Status

🚧 **Under Development** - This project is currently in active development.
