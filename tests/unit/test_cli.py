"""Unit tests for CLI interface."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from heic_converter.cli import main
from heic_converter.models import BatchResults, ConversionResult, ConversionStatus


class TestCLIVersionAndHelp:
    """Test CLI version and help flags."""

    def test_version_flag(self) -> None:
        """Test --version flag displays version information."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "HEIC to JPG Converter" in result.output
        assert "0.1.0" in result.output

    def test_help_flag(self) -> None:
        """Test --help flag displays help information."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Convert HEIC files to high-quality JPG format" in result.output
        assert "--quality" in result.output
        assert "--output-dir" in result.output
        assert "--no-overwrite" in result.output
        assert "--verbose" in result.output

    def test_no_arguments_shows_error(self) -> None:
        """Test that running without arguments shows an error."""
        runner = CliRunner()
        result = runner.invoke(main, [])

        assert result.exit_code == 1
        assert "No files specified" in result.output


class TestCLIArgumentParsing:
    """Test CLI argument parsing."""

    @patch("heic_converter.cli.ConversionOrchestrator")
    @patch("heic_converter.cli.setup_logging")
    def test_single_file_argument(
        self, mock_setup_logging: MagicMock, mock_orchestrator: MagicMock
    ) -> None:
        """Test single file argument parsing."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create a test file
            test_file = Path("test.heic")
            test_file.touch()

            # Mock the orchestrator
            mock_instance = MagicMock()
            mock_orchestrator.return_value = mock_instance
            mock_instance.convert_single.return_value = ConversionResult(
                input_path=test_file,
                output_path=Path("test.jpg"),
                status=ConversionStatus.SUCCESS,
                processing_time=1.0,
            )

            result = runner.invoke(main, [str(test_file)])

            assert result.exit_code == 0
            mock_instance.convert_single.assert_called_once()

    @patch("heic_converter.cli.ConversionOrchestrator")
    @patch("heic_converter.cli.setup_logging")
    def test_batch_argument_parsing(
        self, mock_setup_logging: MagicMock, mock_orchestrator: MagicMock
    ) -> None:
        """Test batch file argument parsing."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create test files
            test_files = [Path("test1.heic"), Path("test2.heic")]
            for f in test_files:
                f.touch()

            # Mock the orchestrator
            mock_instance = MagicMock()
            mock_orchestrator.return_value = mock_instance
            mock_instance.convert_batch.return_value = BatchResults(
                results=[],
                total_files=2,
                successful=2,
                failed=0,
                skipped=0,
                total_time=2.0,
            )

            result = runner.invoke(main, [str(f) for f in test_files])

            assert result.exit_code == 0
            # Batch conversion should be called for multiple files
            assert mock_instance.convert_batch.called

    @patch("heic_converter.cli.ConversionOrchestrator")
    @patch("heic_converter.cli.setup_logging")
    def test_quality_argument(
        self, mock_setup_logging: MagicMock, mock_orchestrator: MagicMock
    ) -> None:
        """Test --quality argument parsing."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            test_file = Path("test.heic")
            test_file.touch()

            mock_instance = MagicMock()
            mock_orchestrator.return_value = mock_instance
            mock_instance.convert_single.return_value = ConversionResult(
                input_path=test_file,
                output_path=Path("test.jpg"),
                status=ConversionStatus.SUCCESS,
                processing_time=1.0,
            )

            result = runner.invoke(main, [str(test_file), "--quality", "95"])

            assert result.exit_code == 0
            # Check that config was created with quality=95
            call_args = mock_orchestrator.call_args
            config = call_args[0][0]
            assert config.quality == 95

    @patch("heic_converter.cli.ConversionOrchestrator")
    @patch("heic_converter.cli.setup_logging")
    def test_output_dir_argument(
        self, mock_setup_logging: MagicMock, mock_orchestrator: MagicMock
    ) -> None:
        """Test --output-dir argument parsing."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            test_file = Path("test.heic")
            test_file.touch()
            output_dir = Path("output")

            mock_instance = MagicMock()
            mock_orchestrator.return_value = mock_instance
            mock_instance.convert_single.return_value = ConversionResult(
                input_path=test_file,
                output_path=output_dir / "test.jpg",
                status=ConversionStatus.SUCCESS,
                processing_time=1.0,
            )

            result = runner.invoke(main, [str(test_file), "--output-dir", str(output_dir)])

            assert result.exit_code == 0
            # Check that config was created with output_dir
            call_args = mock_orchestrator.call_args
            config = call_args[0][0]
            assert config.output_dir == output_dir

    @patch("heic_converter.cli.ConversionOrchestrator")
    @patch("heic_converter.cli.setup_logging")
    def test_no_overwrite_flag(
        self, mock_setup_logging: MagicMock, mock_orchestrator: MagicMock
    ) -> None:
        """Test --no-overwrite flag parsing."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            test_file = Path("test.heic")
            test_file.touch()

            mock_instance = MagicMock()
            mock_orchestrator.return_value = mock_instance
            mock_instance.convert_single.return_value = ConversionResult(
                input_path=test_file,
                output_path=Path("test.jpg"),
                status=ConversionStatus.SUCCESS,
                processing_time=1.0,
            )

            result = runner.invoke(main, [str(test_file), "--no-overwrite"])

            assert result.exit_code == 0
            # Check that config was created with no_overwrite=True
            call_args = mock_orchestrator.call_args
            config = call_args[0][0]
            assert config.no_overwrite is True

    @patch("heic_converter.cli.ConversionOrchestrator")
    @patch("heic_converter.cli.setup_logging")
    def test_verbose_flag(
        self, mock_setup_logging: MagicMock, mock_orchestrator: MagicMock
    ) -> None:
        """Test --verbose flag parsing."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            test_file = Path("test.heic")
            test_file.touch()

            mock_instance = MagicMock()
            mock_orchestrator.return_value = mock_instance
            mock_instance.convert_single.return_value = ConversionResult(
                input_path=test_file,
                output_path=Path("test.jpg"),
                status=ConversionStatus.SUCCESS,
                processing_time=1.0,
            )

            result = runner.invoke(main, [str(test_file), "--verbose"])

            assert result.exit_code == 0
            # Check that config was created with verbose=True
            call_args = mock_orchestrator.call_args
            config = call_args[0][0]
            assert config.verbose is True
            # Check that setup_logging was called with verbose=True
            mock_setup_logging.assert_called_once_with(verbose=True)


class TestCLIErrorHandling:
    """Test CLI error handling."""

    @patch("heic_converter.cli.ConversionOrchestrator")
    @patch("heic_converter.cli.setup_logging")
    def test_failed_conversion_exits_with_error(
        self, mock_setup_logging: MagicMock, mock_orchestrator: MagicMock
    ) -> None:
        """Test that failed conversion exits with error code."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            test_file = Path("test.heic")
            test_file.touch()

            mock_instance = MagicMock()
            mock_orchestrator.return_value = mock_instance
            mock_instance.convert_single.return_value = ConversionResult(
                input_path=test_file,
                output_path=None,
                status=ConversionStatus.FAILED,
                error_message="Test error",
                processing_time=1.0,
            )

            result = runner.invoke(main, [str(test_file)])

            assert result.exit_code == 1
            assert "Failed" in result.output

    @patch("heic_converter.cli.ConversionOrchestrator")
    @patch("heic_converter.cli.setup_logging")
    def test_batch_with_failures_exits_with_error(
        self, mock_setup_logging: MagicMock, mock_orchestrator: MagicMock
    ) -> None:
        """Test that batch with failures exits with error code."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            test_files = [Path("test1.heic"), Path("test2.heic")]
            for f in test_files:
                f.touch()

            mock_instance = MagicMock()
            mock_orchestrator.return_value = mock_instance
            mock_instance.convert_batch.return_value = BatchResults(
                results=[],
                total_files=2,
                successful=1,
                failed=1,
                skipped=0,
                total_time=2.0,
            )

            result = runner.invoke(main, [str(f) for f in test_files])

            assert result.exit_code == 1

    @patch("heic_converter.cli.ConversionOrchestrator")
    @patch("heic_converter.cli.setup_logging")
    def test_exception_handling(
        self, mock_setup_logging: MagicMock, mock_orchestrator: MagicMock
    ) -> None:
        """Test that exceptions are handled gracefully."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            test_file = Path("test.heic")
            test_file.touch()

            mock_instance = MagicMock()
            mock_orchestrator.return_value = mock_instance
            mock_instance.convert_single.side_effect = Exception("Test exception")

            result = runner.invoke(main, [str(test_file)])

            assert result.exit_code == 1
            assert "Error" in result.output
