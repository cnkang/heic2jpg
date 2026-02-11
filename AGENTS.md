# AI Agent Development Guide

This document provides guidance for AI agents working on the HEIC to JPG Converter project.

## Project Architecture

### Overview

The HEIC to JPG Converter follows a modular, layered architecture:

```
┌─────────────────────────────────────────┐
│           CLI Interface (cli.py)         │
│  - Click-based argument parsing          │
│  - Rich progress bars and formatting     │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│    Orchestrator (orchestrator.py)        │
│  - Single/batch conversion coordination  │
│  - Component integration                 │
│  - Metrics persistence                   │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
┌───────▼────────┐  ┌──────▼──────────┐
│ BatchProcessor │  │ Single File Flow│
│ (parallel)     │  │                 │
└───────┬────────┘  └──────┬──────────┘
        │                   │
        └─────────┬─────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼────┐  ┌────▼─────┐  ┌───▼────┐
│FileSystem│ │Analyzer  │  │Converter│
│Handler   │ │          │  │         │
└──────────┘ └────┬─────┘  └────────┘
                   │
              ┌────▼─────┐
              │Optimizer │
              │          │
              └──────────┘
```

### Core Components

#### 1. Data Models (`models.py`)
- **Config**: Application configuration (quality, output dir, flags)
- **ImageMetrics**: Analysis results (exposure, contrast, noise, etc.)
- **EXIFMetadata**: Camera metadata from HEIC files
- **OptimizationParams**: Per-image adjustment parameters
- **ConversionResult**: Single conversion outcome
- **BatchResults**: Aggregated batch conversion results

#### 2. File System Handler (`filesystem.py`)
- Path validation with traversal prevention
- File size validation (max 500MB)
- Extension validation (.heic, .heif only)
- Platform-independent path operations
- Output path generation

#### 3. EXIF Extractor (`exif.py`)
- Extracts camera metadata from HEIC files
- Handles missing/incomplete EXIF gracefully
- Provides fallback values for missing data

#### 4. Image Analyzer (`analyzer.py`)
- Per-image analysis (no batch state)
- Metrics calculated:
  - Exposure level (histogram + EXIF)
  - Contrast level (luminance std dev)
  - Clipping detection (shadows/highlights)
  - Saturation level (HSV space)
  - Sharpness score (Laplacian variance)
  - Noise estimation (high-freq + ISO)
  - Skin tone detection (HSV hue range)
  - Backlit subject detection
  - Low-light detection

#### 5. Optimization Parameter Generator (`optimizer.py`)
- Generates per-image optimization parameters
- Based on analysis metrics and style preferences
- Adjustments:
  - Exposure correction
  - Contrast enhancement
  - Shadow lift (stronger for backlit)
  - Highlight recovery (stronger for overexposed)
  - Saturation adjustment (with skin tone protection)
  - Adaptive sharpening
  - Adaptive noise reduction (ISO-informed)

#### 6. Image Converter (`converter.py`)
- HEIC decoding using pillow-heif
- Applies optimizations in correct order:
  1. Exposure adjustment
  2. Contrast adjustment
  3. Shadow lift
  4. Highlight recovery
  5. Saturation adjustment
  6. Noise reduction (bilateral filter)
  7. Sharpening (unsharp mask)
- JPG encoding with quality setting
- EXIF metadata preservation

#### 7. Batch Processor (`batch_processor.py`)
- Parallel processing using ProcessPoolExecutor
- Worker count from CPU cores or config
- Error isolation (one failure doesn't stop batch)
- Progress tracking across workers
- Result aggregation

#### 8. Orchestrator (`orchestrator.py`)
- Main entry point for conversions
- Coordinates all components
- Handles single and batch flows
- Persists metrics to JSON files

#### 9. Error Handler (`errors.py`)
- Centralized error handling
- Error classification (conversion, invalid file, security, processing)
- User-friendly error messages
- Error logging with context

#### 10. CLI (`cli.py`)
- Click-based command-line interface
- Rich progress bars and formatted output
- Arguments: files, --quality, --output-dir, --no-overwrite, --verbose
- Display functions for results and summaries

## Key Design Decisions

### 1. Per-Image Analysis (No Batch State)
Each image is analyzed independently without batch-level state. This ensures:
- Consistent results regardless of batch composition
- Parallel processing without race conditions
- Reproducible conversions

### 2. Pillow-HEIF (Not ImageMagick)
We use pillow-heif for HEIC decoding because:
- Pure Python integration
- Better EXIF preservation
- No external binary dependencies
- Cross-platform compatibility

### 3. Style Preferences
Three style preferences guide optimizations:
- **Natural appearance**: Reduces aggressive adjustments
- **Preserve highlights**: Prioritizes highlight recovery
- **Stable skin tones**: Protects skin tone saturation

### 4. Metrics Persistence
Analysis metrics are saved as JSON files alongside outputs for:
- Review and tuning
- Debugging optimization parameters
- Future improvements

### 5. Security First
- Path traversal prevention using Path.resolve()
- File size limits (500MB max)
- Extension validation
- No arbitrary code execution

### 6. Quality Guardrails and Human Review
- Optimize for broad real-world scenes, not only one failing sample:
  - backlit subjects
  - high dynamic range / bright specular highlights
  - low-light and mixed indoor lighting
  - high-ISO noise + fine detail
- Any change in `analyzer.py`, `optimizer.py`, or `converter.py` must be validated on a diverse sample set (not just synthetic tests).
- When automated metrics are inconclusive or confidence is low, do **not** over-correct aggressively.
- In uncertain cases, allow and request human-in-the-loop visual judgment:
  - produce a clear flagged list (`input -> output`) for manual review
  - document why items were flagged (e.g., highlight clipping increase)
  - treat human acceptance as the final decision for borderline cases

## Development Workflow

### Adding New Features

1. **Update Data Models**: Add new fields to dataclasses if needed
2. **Implement Core Logic**: Add functionality to appropriate module
3. **Write Tests**: Unit tests + property tests + integration tests
4. **Update CLI**: Add new arguments/options if needed
5. **Update Documentation**: README, AGENTS.md, docstrings

### Testing Strategy

#### Unit Tests (`tests/unit/`)
- Test individual functions and classes
- Use synthetic data and mocks
- Fast execution
- High coverage target (>90%)

#### Property-Based Tests (`tests/property/`)
- Test universal properties using Hypothesis
- Generate random inputs
- Verify invariants hold across all inputs
- 100 iterations per property

#### Integration Tests (`tests/integration/`)
- Test end-to-end workflows
- Use real HEIC files (generated or fixtures)
- Verify component integration
- Test error handling

### Code Style Guidelines

#### Python Style
- Follow PEP 8
- Use type hints everywhere
- Docstrings for all public functions/classes
- Line length: 100 characters

#### Naming Conventions
- Classes: PascalCase
- Functions/methods: snake_case
- Constants: UPPER_SNAKE_CASE
- Private members: _leading_underscore

#### Import Order
1. Standard library
2. Third-party packages
3. Local modules

#### Error Handling
- Use custom exception classes
- Provide descriptive error messages
- Log errors with context
- Don't fail silently

## Commit and Review Best Practices

### Conventional Commits (Required)

All commits **must** use Conventional Commit format:

```
<type>(<scope>): <subject>
```

Examples:
- `feat(cli): add batch progress summary table`
- `fix(converter): preserve EXIF when converting non-RGB images`
- `refactor(orchestrator): simplify batch flow control`
- `test(converter): add regression tests for invalid EXIF payload`
- `docs(agents): clarify commit and validation requirements`

Allowed `type` values:
- `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `ci`, `build`

Rules:
- Use imperative mood in subject (`add`, `fix`, `refactor`), not past tense.
- Keep subject concise and specific (preferably <= 72 chars).
- Make atomic commits: one logical concern per commit.
- Separate source changes and test/doc updates into different commits when practical.
- Commit messages must be written in English.
- Split work into necessary commit batches following best practices. Recommended order when applicable:
  1. production code changes (`feat`/`fix`/`refactor`)
  2. test updates (`test`)
  3. documentation updates (`docs`)

### Commit Validation Checklist

Before every commit, run relevant checks locally:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest tests/unit -v
uv run pytest tests/integration -v
uv run pytest tests/property -v --ignore=tests/property/test_batch_processor_properties.py
uv run bandit -r src/
uv run pip-audit --desc
```

Minimum expectation:
- No lint or type-check errors.
- Updated/new tests for behavior changes.
- No security scanner findings with unresolved risks.

### Additional Engineering Practices

- Prefer `time.perf_counter()` for duration measurement (avoid `time.time()` for elapsed timing).
- Preserve exception chains with `raise ... from e` for debuggability.
- Degrade gracefully for non-critical metadata failures (e.g., EXIF parse failure should not fail conversion).
- Avoid redundant expensive operations in hot paths (e.g., duplicate disk reads/decodes in batch flow).
- Keep performance-sensitive image operations vectorized with NumPy/OpenCV.
- Document any intentional tradeoffs in code comments or commit body when behavior is non-obvious.

## Common Tasks

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/unit/test_converter.py

# Specific test
uv run pytest tests/unit/test_converter.py::TestImageConverter::test_heic_decoding

# With coverage
uv run pytest --cov=heic_converter --cov-report=html

# Property tests with statistics
uv run pytest tests/property -v --hypothesis-show-statistics
```

### Linting and Type Checking

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy src
```

### Adding a New Optimization

1. Add parameter to `OptimizationParams` dataclass
2. Update `OptimizationParamGenerator.generate()` to calculate parameter
3. Update `ImageConverter._apply_optimizations()` to apply adjustment
4. Add unit tests for parameter generation
5. Add property test for optimization effect
6. Update documentation

### Debugging Conversions

1. Enable verbose logging: `--verbose`
2. Check metrics JSON file alongside output
3. Review analysis metrics (exposure, contrast, etc.)
4. Review optimization parameters
5. Adjust `OptimizationParamGenerator` logic if needed

### Performance Optimization

- Use NumPy vectorized operations
- Minimize image copies
- Use appropriate data types (uint8 for images)
- Profile with `cProfile` if needed
- Batch processor uses all CPU cores by default

## Testing Considerations

### Test Coverage

Current local baseline (as of 2026-02-11): 94% code coverage with 302 passing tests.
- Unit tests: Test individual functions and classes
- Integration tests: Test end-to-end workflows
- Property-based tests: Test universal properties with Hypothesis

All tests pass without warnings or skipped tests.

### Test Data

- Use `tests/fixtures/` for test HEIC files
- Generate synthetic images for unit tests
- Use Hypothesis strategies for property tests
- Clean up temporary files in teardown

### Resolved Issues

#### Batch Processor Property Tests (Resolved)
Previously, property tests for batch processor caused segmentation faults due to a bug in pillow-heif's libx265 library when generating test HEIC files. 

**Resolution**: These tests have been removed as the batch processor functionality is comprehensively validated through unit and integration tests. The property tests were conceptually correct but triggered a library bug that was outside our control.

## Architecture Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Dependency Injection**: Pass dependencies explicitly (no globals)
3. **Testability**: Design for easy testing (pure functions, dependency injection)
4. **Error Handling**: Fail gracefully with descriptive messages
5. **Performance**: Optimize hot paths, use parallel processing
6. **Security**: Validate all inputs, prevent path traversal
7. **Cross-Platform**: Use pathlib, avoid platform-specific code

## Future Improvements

- [ ] Support for additional input formats (AVIF, WebP)
- [ ] GPU acceleration for image processing
- [ ] Machine learning-based optimization
- [ ] Web interface
- [ ] Batch processing resume capability
- [ ] Custom optimization profiles
- [ ] Before/after preview mode

## Resources

- [Pillow Documentation](https://pillow.readthedocs.io/)
- [pillow-heif Documentation](https://pillow-heif.readthedocs.io/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Click Documentation](https://click.palletsprojects.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
