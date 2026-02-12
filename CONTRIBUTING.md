# Contributing to HEIC to JPG Converter

Thank you for your interest in contributing to the HEIC to JPG Converter project! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Testing Requirements](#testing-requirements)
- [Code Style Guidelines](#code-style-guidelines)
- [Commit Message Conventions](#commit-message-conventions)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Assume good intentions
- Respect differing viewpoints and experiences

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment
4. Create a new branch for your changes
5. Make your changes
6. Run tests and linting
7. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.14 or higher
- uv package manager
- Git

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/heic2jpg.git
cd heic2jpg

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/heic2jpg.git

# Install dependencies
uv sync --all-extras

# Install pre-commit hooks (optional but recommended)
uv run pre-commit install
```

### Verify Installation

```bash
# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src
```

## Development Workflow

### 1. Create a Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes

- Write clean, readable code
- Follow the code style guidelines
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

### 3. Test Your Changes

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_your_module.py

# Run with coverage
uv run pytest --cov=heic2jpg --cov-report=html

# Check coverage report
open htmlcov/index.html
```

### 4. Lint and Format

```bash
# Format code
uv run ruff format .

# Check for linting issues
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .

# Type check
uv run mypy src
```

### 5. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add new optimization parameter"
```

Commit guidance:
- Use English for all commit messages.
- Keep commits atomic and split changes into logical batches (code, tests, docs) when practical.

### 6. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
```

## Testing Requirements

All contributions must include appropriate tests:

### Unit Tests

- Test individual functions and classes
- Use synthetic data and mocks
- Fast execution (< 1 second per test)
- Place in `tests/unit/`

Example:
```python
def test_exposure_calculation():
    """Test exposure level calculation with known histogram."""
    analyzer = ImageAnalyzer()
    # Create synthetic image with known exposure
    image = np.full((100, 100, 3), 128, dtype=np.uint8)
    metrics = analyzer.analyze(image, None)
    assert 0.4 <= metrics.exposure_level <= 0.6
```

### Property-Based Tests

- Test universal properties using Hypothesis
- Generate random inputs
- Verify invariants hold across all inputs
- Place in `tests/property/`

Example:
```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=0, max_value=100))
def test_quality_validation(quality):
    """Test that quality validation accepts valid values."""
    config = create_config(quality=quality)
    assert 0 <= config.quality <= 100
```

### Integration Tests

- Test end-to-end workflows
- Use real or generated HEIC files
- Verify component integration
- Place in `tests/integration/`

### Coverage Requirements

- Minimum 90% line coverage
- Minimum 85% branch coverage
- All new code must be tested

## Code Style Guidelines

### Python Style

- Follow PEP 8
- Use type hints for all functions
- Write docstrings for public APIs
- Line length: 100 characters
- Use f-strings for formatting

### Naming Conventions

```python
# Classes: PascalCase
class ImageAnalyzer:
    pass

# Functions/methods: snake_case
def calculate_exposure_level():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_FILE_SIZE = 500 * 1024 * 1024

# Private members: _leading_underscore
def _internal_helper():
    pass
```

### Import Order

```python
# 1. Standard library
import logging
from pathlib import Path

# 2. Third-party packages
import numpy as np
from PIL import Image

# 3. Local modules
from heic2jpg.models import Config
from heic2jpg.errors import ConversionError
```

### Docstring Format

Use Google-style docstrings:

```python
def convert_image(input_path: Path, quality: int) -> ConversionResult:
    """Convert a HEIC image to JPG format.

    Args:
        input_path: Path to the input HEIC file
        quality: JPG quality level (0-100)

    Returns:
        ConversionResult with conversion status and details

    Raises:
        InvalidFileError: If input file is not a valid HEIC file
        SecurityError: If input path fails security validation
    """
    pass
```

## Commit Message Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

Additional requirements:
- Commit messages must be in English.
- Prefer small, reviewable commits and split by concern whenever possible.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```bash
# Feature
git commit -m "feat(analyzer): add skin tone detection"

# Bug fix
git commit -m "fix(converter): correct EXIF preservation for rotated images"

# Documentation
git commit -m "docs: update installation instructions"

# Breaking change
git commit -m "feat(cli)!: change default quality to 95

BREAKING CHANGE: Default quality changed from 100 to 95 for better file sizes"
```

## Pull Request Process

### Before Submitting

1. ✅ All tests pass
2. ✅ Code is formatted and linted
3. ✅ Type checking passes
4. ✅ Coverage meets requirements
5. ✅ Documentation is updated
6. ✅ Commit messages follow conventions

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Property tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests pass

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Coverage maintained/improved
```

### Review Process

1. Automated checks run (tests, linting, type checking)
2. Maintainer reviews code
3. Address feedback and update PR
4. Maintainer approves and merges

### After Merge

- Delete your feature branch
- Update your local main branch
- Close related issues

## Reporting Bugs

### Before Reporting

1. Check existing issues
2. Verify bug in latest version
3. Collect relevant information

### Bug Report Template

```markdown
**Describe the bug**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Run command '...'
2. With file '...'
3. See error

**Expected behavior**
What you expected to happen

**Actual behavior**
What actually happened

**Environment**
- OS: [e.g., macOS 14.0]
- Python version: [e.g., 3.14.3]
- Package version: [e.g., 0.1.0]

**Additional context**
- Error messages
- Log output (with --verbose)
- Sample files (if possible)
```

## Suggesting Enhancements

### Enhancement Template

```markdown
**Is your feature request related to a problem?**
Clear description of the problem

**Describe the solution you'd like**
Clear description of desired solution

**Describe alternatives you've considered**
Alternative solutions or features

**Additional context**
- Use cases
- Examples
- Mockups/diagrams
```

## Development Tips

### Running Specific Tests

```bash
# Single test
uv run pytest tests/unit/test_converter.py::TestImageConverter::test_heic_decoding

# Test class
uv run pytest tests/unit/test_converter.py::TestImageConverter

# Tests matching pattern
uv run pytest -k "test_exposure"
```

### Debugging Tests

```bash
# Show print statements
uv run pytest -s

# Stop on first failure
uv run pytest -x

# Show local variables on failure
uv run pytest -l

# Enter debugger on failure
uv run pytest --pdb
```

### Performance Profiling

```bash
# Profile code
python -m cProfile -o profile.stats -m heic2jpg input.heic

# View results
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

## Questions?

- Open an issue for questions
- Check existing documentation
- Review AGENTS.md for architecture details

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
