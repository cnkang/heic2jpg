# Implementation Plan: HEIC to JPG Converter

## Overview

This implementation plan breaks down the HEIC to JPG converter into incremental, testable steps. The approach follows a bottom-up strategy: build core components first, add analysis and optimization layers, then wire everything together with the CLI interface. Each step includes corresponding tests to validate functionality early.

## Tasks

- [x] 1. Project setup and core data models
  - Create project structure following Python best practices (src layout)
  - Set up pyproject.toml with uv for Python 3.14
  - Define core data models (Config, ImageMetrics, EXIFMetadata, OptimizationParams, ConversionResult, etc.)
  - Set up pytest and hypothesis for testing
  - Configure ruff for linting, mypy for type checking
  - _Requirements: 4.1, 4.2, 4.5, 12.1, 12.2_

- [x] 1.1 Write unit tests for data models
  - Test dataclass initialization and validation
  - Test ConversionStatus enum values
  - Test BatchResults.success_rate() calculation
  - _Requirements: 4.1_

- [x] 2. File system handler with security validation
  - [x] 2.1 Implement FileSystemHandler class
    - Implement path validation with traversal prevention using Path.resolve()
    - Implement file size validation (max 500MB)
    - Implement extension validation (only .heic, .heif)
    - Implement platform-independent path operations using pathlib
    - Implement output path generation
    - _Requirements: 14.1, 14.2, 20.4_
  
  - [x] 2.2 Write property test for path traversal prevention
    - **Property 10: Path Traversal Prevention**
    - **Validates: Requirements 14.1**
  
  - [x] 2.3 Write property test for file size validation
    - **Property 11: File Size Validation**
    - **Validates: Requirements 14.2**
  
  - [x] 2.4 Write property test for platform-independent paths
    - **Property 27: Platform-Independent Path Handling**
    - **Validates: Requirements 20.4**
  
  - [x] 2.5 Write unit tests for file system operations
    - Test output path generation from input path
    - Test directory creation
    - Test file existence checks
    - _Requirements: 18.1, 18.2_

- [x] 3. EXIF metadata extraction
  - [x] 3.1 Implement EXIF metadata extraction
    - Create EXIFMetadata dataclass
    - Implement extraction of ISO, exposure time, f-number, exposure compensation
    - Implement extraction of flash information, scene type, brightness value
    - Handle missing or incomplete EXIF data gracefully
    - _Requirements: 21.6, 21.7, 21.8, 21.9, 21.10_
  
  - [x] 3.2 Write property test for EXIF preservation
    - **Property 2: EXIF Metadata Preservation**
    - **Validates: Requirements 1.3**
  
  - [x] 3.3 Write property test for EXIF fallback
    - **Property 32: EXIF Data Fallback**
    - **Validates: Requirements 21.10**
  
  - [x] 3.4 Write unit tests for EXIF extraction
    - Test extraction from images with complete EXIF
    - Test extraction from images with partial EXIF
    - Test extraction from images with no EXIF
    - _Requirements: 1.3, 21.10_

- [x] 4. Image analysis engine
  - [x] 4.1 Implement ImageAnalyzer class
    - Implement exposure calculation using histogram and EXIF
    - Implement contrast calculation using luminance std dev
    - Implement clipping detection (shadow and highlight)
    - Implement saturation calculation in HSV space
    - Implement sharpness calculation using Laplacian variance
    - Implement noise estimation using high-frequency analysis and ISO
    - Implement skin tone detection using HSV hue range
    - Implement backlit subject detection
    - Implement low-light detection using histogram and EXIF
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 21.1, 21.2, 21.3, 21.6_
  
  - [x] 4.2 Write property test for per-image analysis independence
    - **Property 22: Per-Image Analysis Independence**
    - **Validates: Requirements 19.1, 19.2, 19.3, 19.4, 19.5, 19.6**
  
  - [x] 4.3 Write unit tests for analysis components
    - Test exposure calculation with known histograms
    - Test contrast calculation with known images
    - Test clipping detection with synthetic images
    - Test backlit detection with backlit test images
    - Test low-light detection with dark test images
    - _Requirements: 19.1, 19.2, 19.3, 21.2, 21.3_

- [x] 5. Chec//kpoint - Ensure analysis tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Optimization parameter generator
  - [x] 6.1 Implement OptimizationParamGenerator class
    - Implement exposure adjustment calculation
    - Implement contrast adjustment calculation
    - Implement highlight recovery calculation (stronger for overexposed images)
    - Implement shadow lift calculation (stronger for backlit images)
    - Implement saturation adjustment calculation with skin tone protection
    - Implement sharpness calculation
    - Implement adaptive noise reduction calculation based on ISO and noise level
    - Apply style preferences (natural, preserve highlights, stable skin tones)
    - _Requirements: 19.7, 19.8, 19.9, 19.10, 21.1, 21.2, 21.3, 21.4, 21.6_
  
  - [x] 6.2 Write property test for per-image optimization parameters
    - **Property 23: Per-Image Optimization Parameters**
    - **Validates: Requirements 19.7**
  
  - [x] 6.3 Write property test for EXIF-informed noise reduction
    - **Property 29: EXIF-Informed Noise Reduction**
    - **Validates: Requirements 21.6**
  
  - [x] 6.4 Write unit tests for optimization parameter generation
    - Test exposure adjustment for underexposed images
    - Test highlight recovery for overexposed images
    - Test shadow lift for backlit images
    - Test noise reduction scaling with ISO
    - Test skin tone protection
    - _Requirements: 19.7, 19.9, 19.10, 21.1, 21.2, 21.6_

- [x] 7. Image converter core
  - [x] 7.1 Implement ImageConverter class
    - Implement HEIC decoding using pillow-heif
    - Implement JPG encoding using Pillow with quality setting
    - Implement exposure adjustment (multiply luminance)
    - Implement contrast adjustment (apply curve)
    - Implement shadow lift (lift dark values)
    - Implement highlight recovery (compress bright values)
    - Implement saturation adjustment in HSV space
    - Implement adaptive bilateral noise reduction
    - Implement unsharp mask sharpening
    - Apply optimizations in correct order
    - Preserve EXIF metadata in output
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 19.9, 19.10, 21.3, 21.4_
  
  - [x] 7.2 Write property test for conversion success
    - **Property 1: HEIC to JPG Conversion Success**
    - **Validates: Requirements 1.1, 1.2**
  
  - [x] 7.3 Write property test for highlight preservation
    - **Property 24: Highlight Preservation**
    - **Validates: Requirements 19.9**
  
  - [x] 7.4 Write property test for skin tone stability
    - **Property 25: Skin Tone Stability**
    - **Validates: Requirements 19.10**
  
  - [x] 7.5 Write property test for backlit shadow recovery
    - **Property 30: Backlit Subject Shadow Recovery**
    - **Validates: Requirements 21.2**
  
  - [x] 7.6 Write property test for low-light noise reduction
    - **Property 31: Low-Light Noise Reduction Quality**
    - **Validates: Requirements 21.3, 21.4**
  
  - [x] 7.7 Write unit tests for image converter
    - Test HEIC decoding
    - Test JPG encoding with different quality levels
    - Test each optimization step individually
    - Test optimization order
    - _Requirements: 1.1, 2.1, 2.2_

- [x] 8. Checkpoint - Ensure core conversion tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Error handling and validation
  - [x] 9.1 Implement error classes and ErrorHandler
    - Define ConversionError, InvalidFileError, SecurityError, ProcessingError
    - Implement ErrorHandler with error classification
    - Implement user-friendly error message generation
    - Implement error logging with context
    - _Requirements: 16.1, 16.2_
  
  - [x] 9.2 Write property test for invalid input error handling
    - **Property 3: Invalid Input Error Handling**
    - **Validates: Requirements 1.4, 1.5**
  
  - [x] 9.3 Write property test for descriptive error messages
    - **Property 13: Descriptive Error Messages**
    - **Validates: Requirements 16.1**
  
  - [x] 9.4 Write unit tests for error handling
    - Test error classification
    - Test error message generation
    - Test error logging
    - _Requirements: 16.1, 16.2_

- [x] 10. Quality configuration and validation
  - [x] 10.1 Implement quality configuration handling
    - Implement quality validation (0-100 range)
    - Implement default quality (100)
    - Implement quality from config variable
    - Implement quality from environment variable
    - Implement fallback to default on invalid quality
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [x] 10.2 Write property test for quality configuration
    - **Property 4: Quality Configuration Acceptance**
    - **Validates: Requirements 2.2, 2.3**
  
  - [x] 10.3 Write property test for quality validation
    - **Property 5: Quality Validation**
    - **Validates: Requirements 2.4, 2.5**
  
  - [x] 10.4 Write unit test for default quality
    - Test that default quality is 100
    - _Requirements: 2.1_

- [x] 11. Batch processor with parallel execution
  - [x] 11.1 Implement BatchProcessor class
    - Implement parallel processing using ProcessPoolExecutor
    - Determine worker count from CPU cores or config
    - Implement error isolation (one failure doesn't stop batch)
    - Implement progress tracking across workers
    - Implement result aggregation
    - _Requirements: 3.1, 3.3, 3.4, 3.5_
  
  - [x] 11.2 Write property test for parallel processing performance
    - **Property 6: Parallel Processing Performance**
    - **Validates: Requirements 3.1**
  
  - [x] 11.3 Write property test for batch result reporting
    - **Property 7: Batch Result Reporting Accuracy**
    - **Validates: Requirements 3.3, 3.4**
  
  - [x] 11.4 Write property test for batch error isolation
    - **Property 8: Batch Error Isolation**
    - **Validates: Requirements 3.5**
  
  - [x] 11.5 Write unit tests for batch processor
    - Test worker count determination
    - Test result aggregation
    - Test progress tracking
    - _Requirements: 3.1, 3.3, 3.4_

- [x] 12. Conversion orchestrator
  - [x] 12.1 Implement ConversionOrchestrator class
    - Implement single file conversion flow
    - Implement batch conversion flow
    - Integrate FileSystemHandler, ImageAnalyzer, OptimizationParamGenerator, ImageConverter
    - Implement configuration management
    - Implement metrics persistence
    - _Requirements: 19.12_
  
  - [x] 12.2 Write property test for analysis metrics persistence
    - **Property 26: Analysis Metrics Persistence**
    - **Validates: Requirements 19.12**
  
  - [x] 12.3 Write integration tests for orchestrator
    - Test single file conversion end-to-end
    - Test batch conversion end-to-end
    - Test error handling in orchestrator
    - _Requirements: 1.1, 3.1_

- [x] 13. Checkpoint - Ensure orchestrator tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Logging system
  - [x] 14.1 Implement logging configuration
    - Set up Python logging with configurable levels
    - Implement English-only log messages
    - Implement operation logging (conversions, errors)
    - Implement verbose logging mode
    - Implement platform-independent line endings
    - _Requirements: 13.3, 16.2, 16.3, 16.4, 16.5, 20.6_
  
  - [x] 14.2 Write property test for English-only output
    - **Property 9: English-Only Output**
    - **Validates: Requirements 13.3, 13.4, 13.5**
  
  - [x] 14.3 Write property test for operation logging
    - **Property 14: Operation Logging**
    - **Validates: Requirements 16.2, 16.4**
  
  - [x] 14.4 Write property test for configurable logging levels
    - **Property 15: Configurable Logging Levels**
    - **Validates: Requirements 16.3**
  
  - [x] 14.5 Write property test for verbose logging
    - **Property 16: Verbose Logging Detail**
    - **Validates: Requirements 16.5**
  
  - [x] 14.6 Write property test for platform-independent line endings
    - **Property 28: Platform-Independent Line Endings**
    - **Validates: Requirements 20.6**

- [~] 15. Progress feedback system
  - [x] 15.1 Implement progress tracking
    - Implement progress callbacks for single conversion
    - Implement progress aggregation for batch conversion
    - Integrate with rich library for progress bars
    - _Requirements: 15.5_
  
  - [x] 15.2 Write property test for progress feedback
    - **Property 12: Progress Feedback**
    - **Validates: Requirements 15.5**

- [~] 16. Output file management
  - [x] 16.1 Implement output file handling
    - Implement filename transformation (.heic -> .jpg)
    - Implement output directory specification
    - (Not implemented) filename pattern support
    - (Not implemented) interactive overwrite confirmation prompt
    - Implement no-overwrite flag behavior
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5_
  
  - [x] 16.2 Write property test for filename transformation
    - **Property 18: Output Filename Transformation**
    - **Validates: Requirements 18.1**
  
  - [x] 16.3 Write property test for output directory
    - **Property 19: Output Directory Specification**
    - **Validates: Requirements 18.2**
  
  - [ ] 16.4 Write property test for filename patterns
    - **Property 20: Output Filename Pattern Application**
    - **Validates: Requirements 18.3**
  
  - [x] 16.5 Write property test for no-overwrite flag
    - **Property 21: No-Overwrite Flag Behavior**
    - **Validates: Requirements 18.5**
  
  - [ ] 16.6 Write unit test for overwrite prompt
    - Test that prompt is shown when file exists
    - _Requirements: 18.4_

- [x] 17. CLI interface
  - [x] 17.1 Implement CLI using click
    - Implement argument parsing for single file
    - Implement argument parsing for batch (multiple files)
    - Implement --quality argument
    - Implement --output-dir argument
    - Implement --no-overwrite flag
    - Implement --verbose flag
    - Implement --help flag
    - Implement --version flag
    - Integrate with rich for formatted output
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_
  
  - [x] 17.2 Write property test for CLI quality argument
    - **Property 17: CLI Quality Argument Parsing**
    - **Validates: Requirements 17.3**
  
  - [x] 17.3 Write unit tests for CLI
    - Test single file argument parsing
    - Test batch argument parsing
    - Test --help output
    - Test --version output
    - _Requirements: 17.1, 17.2, 17.4, 17.5_

- [x] 18. CLI display and formatting
  - [x] 18.1 Implement CLI display functions
    - Implement progress display using rich progress bars
    - Implement summary display with success/failure counts
    - Implement error display with formatting
    - Ensure all output is in English
    - _Requirements: 13.5, 15.5_
  
  - [x] 18.2 Write integration tests for CLI display
    - Test progress display during conversion
    - Test summary display after batch
    - Test error display
    - _Requirements: 15.5_

- [x] 19. Checkpoint - Ensure CLI tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 20. Documentation
  - [x] 20.1 Create README.md (English)
    - Write project overview and purpose
    - Write installation instructions using uv
    - Write quick start guide
    - Write usage examples (single file, batch)
    - Write configuration options documentation
    - Write troubleshooting section
    - Write contributing guidelines
    - _Requirements: 10.1, 10.4, 10.5_
  
  - [x] 20.2 Create README.zh-CN.md (Chinese)
    - Translate README.md to Chinese
    - Maintain parallel structure with English version
    - _Requirements: 10.2, 10.3, 10.5_
  
  - [x] 20.3 Create AGENTS.md
    - Document project architecture
    - Document key design decisions
    - Document development workflow
    - Document testing strategy
    - Document code style guidelines
    - Document common tasks
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
  
  - [x] 20.4 Create CONTRIBUTING.md
    - Document development setup
    - Document testing requirements
    - Document code review process
    - Document commit message conventions
    - _Requirements: 12.5_

- [x] 21. GitHub Actions CI/CD
  - [x] 21.1 Create test workflow
    - Set up matrix testing (macOS, Windows, Linux)
    - Run unit tests with pytest
    - Run property tests with hypothesis
    - Run integration tests
    - Upload coverage reports
    - _Requirements: 6.1, 6.2, 6.5, 20.1, 20.2, 20.3_
  
  - [x] 21.2 Create linting workflow
    - Run ruff for linting
    - Run mypy for type checking
    - Run ruff format for formatting validation
    - _Requirements: 7.1, 7.2, 7.3, 7.5_
  
  - [x] 21.3 Create security workflow
    - Run bandit for security scanning
    - Run pip-audit for dependency vulnerabilities
    - Scan for security anti-patterns
    - _Requirements: 8.1, 8.2, 8.4_
  
  - [x] 21.4 Create Dependabot configuration
    - Configure weekly dependency update checks
    - Configure automatic PR creation
    - Prioritize security updates
    - _Requirements: 9.1, 9.2, 9.4_

- [x] 22. Final integration and testing
  - [x] 22.1 Run full test suite
    - Run all unit tests
    - Run all property tests (100 iterations each)
    - Run all integration tests
    - Verify coverage meets goals (>90% line, >85% branch)
    - _Requirements: All_
  
  - [x] 22.2 Manual testing on all platforms
    - Test on macOS with real HEIC files
    - Test on Windows with real HEIC files
    - Test on Linux with real HEIC files
    - Test challenging lighting conditions (overexposed, backlit, low-light)
    - Verify visual quality of outputs
    - _Requirements: 20.1, 20.2, 20.3, 21.1, 21.2, 21.3_
  
  - [x] 22.3 Performance validation
    - Benchmark single file conversion time
    - Benchmark batch conversion with parallel processing
    - Verify CPU utilization during batch processing
    - Verify memory usage stays within bounds
    - _Requirements: 3.1, 15.1, 15.2, 15.3_

- [x] 23. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required for complete implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (100 iterations each)
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- The implementation follows a bottom-up approach: core components first, then integration
- All code must use English for comments, variable names, and output
- All code must follow Python 3.14 best practices and type hints
- Security validation is integrated throughout (path validation, file size checks)
- Cross-platform compatibility is ensured through pathlib and platform-independent code
