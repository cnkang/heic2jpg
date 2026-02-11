"""Command-line interface for the HEIC to JPG converter."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from heic_converter.config import create_config
from heic_converter.logging_config import setup_logging
from heic_converter.models import BatchResults, ConversionResult, ConversionStatus
from heic_converter.orchestrator import ConversionOrchestrator

# Version information
__version__ = "0.1.0"

# Create console for rich output
console = Console()


def display_progress_bar(files: list[Path], orchestrator: ConversionOrchestrator) -> BatchResults:
    """Display a progress bar during batch conversion.

    Args:
        files: List of files to convert
        orchestrator: Orchestrator instance to use for conversion

    Returns:
        BatchResults from the conversion
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Converting HEIC files...", total=len(files))

        # Create progress callback
        def progress_callback(current: int, _total: int, filename: str) -> None:
            progress.update(
                task,
                completed=current,
                description=f"[cyan]Converting: {filename}",
            )

        # Update orchestrator with progress callback
        orchestrator.progress_callback = progress_callback

        # Perform conversion
        results = orchestrator.convert_batch(files)

        # Update to show completion
        progress.update(
            task,
            completed=len(files),
            description="[green]Conversion complete!",
        )

    return results


def display_summary(results: BatchResults) -> None:
    """Display a summary of batch conversion results.

    Args:
        results: BatchResults to display
    """
    # Create summary table
    table = Table(title="Conversion Summary", show_header=True, header_style="bold")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Total Files", str(results.total_files))
    table.add_row("Successful", f"[green]{results.successful}[/green]")
    table.add_row("Failed", f"[red]{results.failed}[/red]")
    table.add_row("Skipped", f"[yellow]{results.skipped}[/yellow]")
    table.add_row("Success Rate", f"{results.success_rate():.1f}%")
    table.add_row("Total Time", f"{results.total_time:.2f}s")

    console.print()
    console.print(table)

    # Show failed files if any
    if results.failed > 0:
        console.print()
        console.print("[bold red]Failed Conversions:[/bold red]")
        for result in results.results:
            if result.status == ConversionStatus.FAILED:
                console.print(f"  [red]✗[/red] {result.input_path.name}: {result.error_message}")

    # Show skipped files if any
    if results.skipped > 0:
        console.print()
        console.print("[bold yellow]Skipped Files:[/bold yellow]")
        for result in results.results:
            if result.status == ConversionStatus.SKIPPED:
                console.print(
                    f"  [yellow]⊘[/yellow] {result.input_path.name}: {result.error_message}"
                )


def display_single_result(result: ConversionResult) -> None:
    """Display the result of a single file conversion.

    Args:
        result: ConversionResult to display
    """
    if result.status == ConversionStatus.SUCCESS:
        console.print(
            f"[green]✓[/green] Successfully converted: {result.input_path.name} → "
            f"{result.output_path.name if result.output_path else 'N/A'} "
            f"({result.processing_time:.2f}s)"
        )
    elif result.status == ConversionStatus.SKIPPED:
        console.print(
            f"[yellow]⊘[/yellow] Skipped: {result.input_path.name} - {result.error_message}"
        )
    else:
        console.print(f"[red]✗[/red] Failed: {result.input_path.name} - {result.error_message}")


def handle_error(error: Exception) -> None:
    """Display a formatted error message.

    Args:
        error: Exception to display
    """
    console.print(f"[bold red]Error:[/bold red] {str(error)}", style="red")


@click.command()
@click.argument(
    "files",
    nargs=-1,
    type=click.Path(exists=True, path_type=Path),
    required=False,
)
@click.option(
    "--quality",
    "-q",
    type=click.IntRange(0, 100),
    default=None,
    help="JPG quality level (0-100). Default: 100 (minimal compression).",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for converted files. Default: same as input.",
)
@click.option(
    "--no-overwrite",
    is_flag=True,
    default=False,
    help="Skip existing files without prompting.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose logging.",
)
@click.option(
    "--version",
    is_flag=True,
    default=False,
    help="Show version information and exit.",
)
@click.help_option("--help", "-h")
def main(
    files: tuple[Path, ...],
    quality: int | None,
    output_dir: Path | None,
    no_overwrite: bool,
    verbose: bool,
    version: bool,
) -> None:
    """Convert HEIC files to high-quality JPG format.

    FILES: One or more HEIC files to convert. Supports wildcards (e.g., *.heic).

    Examples:

        # Convert a single file
        heic-converter photo.heic

        # Convert with custom quality
        heic-converter photo.heic --quality 95

        # Batch convert with output directory
        heic-converter *.heic --output-dir ./converted

        # Batch convert without overwriting existing files
        heic-converter *.heic --no-overwrite

        # Verbose logging
        heic-converter photo.heic --verbose
    """
    # Handle version flag
    if version:
        console.print(f"HEIC to JPG Converter v{__version__}")
        sys.exit(0)

    try:
        # Convert files tuple to list of Paths
        file_list = list(files)

        # Validate that we have files
        if not file_list:
            console.print("[bold red]Error:[/bold red] No files specified.", style="red")
            sys.exit(1)

        # Setup logging
        logger = setup_logging(verbose=verbose)

        # Create configuration
        config = create_config(
            quality=quality,
            output_dir=output_dir,
            no_overwrite=no_overwrite,
            verbose=verbose,
        )

        # Create orchestrator
        orchestrator = ConversionOrchestrator(config, logger)

        # Display configuration info
        if verbose:
            console.print(f"[cyan]Quality:[/cyan] {config.quality}")
            console.print(
                f"[cyan]Output Directory:[/cyan] "
                f"{config.output_dir if config.output_dir else 'Same as input'}"
            )
            console.print(f"[cyan]No Overwrite:[/cyan] {config.no_overwrite}")
            console.print()

        # Single file or batch?
        if len(file_list) == 1:
            # Single file conversion
            console.print(f"Converting: [cyan]{file_list[0].name}[/cyan]")
            result = orchestrator.convert_single(file_list[0])
            display_single_result(result)

            # Exit with error code if conversion failed
            if result.status == ConversionStatus.FAILED:
                sys.exit(1)
        else:
            # Batch conversion
            console.print(f"Converting [cyan]{len(file_list)}[/cyan] files...")
            results = display_progress_bar(file_list, orchestrator)
            display_summary(results)

            # Exit with error code if any conversions failed
            if results.failed > 0:
                sys.exit(1)

    except Exception as e:
        handle_error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
