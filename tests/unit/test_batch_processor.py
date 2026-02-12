"""Unit tests for BatchProcessor."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from heic2jpg.batch_processor import BatchProcessor
from heic2jpg.config import Config
from heic2jpg.models import ConversionResult, ConversionStatus


class TestBatchProcessor:
    """Test BatchProcessor class."""

    def test_init_with_explicit_workers(self):
        """Test initialization with explicit worker count."""
        config = Config(parallel_workers=4)
        processor = BatchProcessor(config)

        assert processor.worker_count == 4
        assert processor.config == config

    def test_init_with_auto_workers(self):
        """Test initialization with auto-detected worker count."""
        config = Config(parallel_workers=None)

        with patch("os.cpu_count", return_value=16):
            processor = BatchProcessor(config)
            # Should cap at 8
            assert processor.worker_count == 8

    def test_init_with_auto_workers_low_cpu(self):
        """Test initialization with auto-detected worker count on low-CPU system."""
        config = Config(parallel_workers=None)

        with patch("os.cpu_count", return_value=2):
            processor = BatchProcessor(config)
            # Should use all 2 cores
            assert processor.worker_count == 2

    def test_init_with_auto_workers_fallback(self):
        """Test initialization when cpu_count returns None."""
        config = Config(parallel_workers=None)

        with patch("os.cpu_count", return_value=None):
            processor = BatchProcessor(config)
            # Should use fallback default of 4
            assert processor.worker_count == 4

    def test_process_batch_empty(self):
        """Test processing an empty batch."""
        config = Config()
        processor = BatchProcessor(config)

        results = processor.process_batch([])

        assert results.total_files == 0
        assert results.successful == 0
        assert results.failed == 0
        assert results.skipped == 0
        assert len(results.results) == 0

    def test_worker_count_determination(self):
        """Test worker count determination logic."""
        # Test with explicit worker count
        config1 = Config(parallel_workers=6)
        processor1 = BatchProcessor(config1)
        assert processor1.worker_count == 6

        # Test with auto-detection (mocked)
        config2 = Config(parallel_workers=None)
        with patch("os.cpu_count", return_value=4):
            processor2 = BatchProcessor(config2)
            assert processor2.worker_count == 4

        # Test capping at 8
        config3 = Config(parallel_workers=None)
        with patch("os.cpu_count", return_value=32):
            processor3 = BatchProcessor(config3)
            assert processor3.worker_count == 8

    def test_progress_callback_called(self):
        """Test that progress callback is called during processing."""
        config = Config()
        progress_callback = Mock()
        processor = BatchProcessor(config, progress_callback=progress_callback)

        # Create a mock file that will succeed
        test_file = Path("test.heic")

        # Mock the worker function to return a success result
        mock_result = ConversionResult(
            input_path=test_file,
            output_path=Path("test.jpg"),
            status=ConversionStatus.SUCCESS,
        )

        with patch(
            "heic2jpg.batch_processor._process_single_file_worker",
            return_value=mock_result,
        ):
            processor.process_batch([test_file])

        # Progress callback should have been called
        assert progress_callback.called
        # Should be called with (current, total, filename)
        progress_callback.assert_called_with(1, 1, "test.heic")

    def test_result_aggregation(self):
        """Test that results are properly aggregated."""
        config = Config()
        processor = BatchProcessor(config)

        # Create mock files
        files = [Path(f"test{i}.heic") for i in range(5)]

        # Mock worker to return different statuses
        def mock_worker(file_path, config, output_path=None):
            if "test0" in str(file_path) or "test1" in str(file_path):
                return ConversionResult(
                    input_path=file_path,
                    output_path=Path(str(file_path).replace(".heic", ".jpg")),
                    status=ConversionStatus.SUCCESS,
                )
            elif "test2" in str(file_path):
                return ConversionResult(
                    input_path=file_path,
                    output_path=None,
                    status=ConversionStatus.FAILED,
                    error_message="Test error",
                )
            elif "test3" in str(file_path):
                return ConversionResult(
                    input_path=file_path,
                    output_path=Path(str(file_path).replace(".heic", ".jpg")),
                    status=ConversionStatus.SKIPPED,
                )
            else:
                return ConversionResult(
                    input_path=file_path,
                    output_path=Path(str(file_path).replace(".heic", ".jpg")),
                    status=ConversionStatus.SUCCESS,
                )

        # Use ThreadPoolExecutor for testing to avoid pickling issues
        from concurrent.futures import ThreadPoolExecutor

        with (
            patch("heic2jpg.batch_processor.ProcessPoolExecutor", ThreadPoolExecutor),
            patch(
                "heic2jpg.batch_processor._process_single_file_worker",
                side_effect=mock_worker,
            ),
        ):
            results = processor.process_batch(files)

        assert results.total_files == 5
        assert results.successful == 3  # test0, test1, test4
        assert results.failed == 1  # test2
        assert results.skipped == 1  # test3
        assert len(results.results) == 5

    def test_error_isolation(self):
        """Test that one file failure doesn't stop batch processing."""
        config = Config()
        processor = BatchProcessor(config)

        files = [Path(f"test{i}.heic") for i in range(3)]

        # Mock worker to fail on second file
        def mock_worker(file_path, config, output_path=None):
            if "test1" in str(file_path):
                raise Exception("Test error")
            return ConversionResult(
                input_path=file_path,
                output_path=Path(str(file_path).replace(".heic", ".jpg")),
                status=ConversionStatus.SUCCESS,
            )

        # Use ThreadPoolExecutor for testing to avoid pickling issues
        from concurrent.futures import ThreadPoolExecutor

        with (
            patch("heic2jpg.batch_processor.ProcessPoolExecutor", ThreadPoolExecutor),
            patch(
                "heic2jpg.batch_processor._process_single_file_worker",
                side_effect=mock_worker,
            ),
        ):
            results = processor.process_batch(files)

        # Should have processed all 3 files
        assert results.total_files == 3
        assert len(results.results) == 3

        # Two should succeed, one should fail
        assert results.successful == 2
        assert results.failed == 1

        # Check that the failed result has an error message
        failed_results = [r for r in results.results if r.status == ConversionStatus.FAILED]
        assert len(failed_results) == 1
        assert failed_results[0].error_message is not None

    def test_process_batch_avoids_output_name_collisions(self):
        """Test that output names are made unique when batch inputs collide."""
        from concurrent.futures import ThreadPoolExecutor

        output_dir = Path("/tmp/output")
        config = Config(output_dir=output_dir)
        processor = BatchProcessor(config)

        files = [Path("/a/IMG_0001.heic"), Path("/b/IMG_0001.heic")]
        output_names: list[str] = []

        def mock_worker(file_path, config, output_path=None):
            assert output_path is not None
            output_names.append(output_path.name)
            return ConversionResult(
                input_path=file_path,
                output_path=output_path,
                status=ConversionStatus.SUCCESS,
            )

        with (
            patch("heic2jpg.batch_processor.ProcessPoolExecutor", ThreadPoolExecutor),
            patch(
                "heic2jpg.batch_processor._process_single_file_worker",
                side_effect=mock_worker,
            ),
        ):
            results = processor.process_batch(files)

        assert results.successful == 2
        assert len(output_names) == 2
        assert len(set(output_names)) == 2
        assert "IMG_0001.jpg" in output_names
        assert any(name.startswith("IMG_0001_") and name.endswith(".jpg") for name in output_names)


class TestProcessSingleFileWorker:
    """Test the worker function."""

    def test_worker_validates_input(self, tmp_path):
        """Test that worker validates input file."""
        from heic2jpg.batch_processor import _process_single_file_worker

        # Non-existent file
        config = Config()
        result = _process_single_file_worker(Path("nonexistent.heic"), config)

        assert result.status == ConversionStatus.FAILED
        assert (
            "not found" in result.error_message.lower() or "invalid" in result.error_message.lower()
        )

    def test_worker_handles_no_overwrite(self, tmp_path):
        """Test that worker respects no-overwrite flag."""
        from heic2jpg.batch_processor import _process_single_file_worker

        # Create a fake input file
        input_file = tmp_path / "test.heic"
        input_file.write_bytes(b"fake heic data")

        # Create output file that already exists
        output_file = tmp_path / "test.jpg"
        output_file.write_bytes(b"existing jpg")

        config = Config(no_overwrite=True, output_dir=tmp_path)

        # Mock validation to pass
        with patch(
            "heic2jpg.batch_processor.FileSystemHandler.validate_input_file"
        ) as mock_validate:
            mock_validate.return_value = MagicMock(valid=True)

            result = _process_single_file_worker(input_file, config)

        assert result.status == ConversionStatus.SKIPPED
        assert "already exists" in result.error_message.lower()
