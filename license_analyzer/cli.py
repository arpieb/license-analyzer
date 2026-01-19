"""CLI entry point for license-analyzer."""
import asyncio
import sys
from typing import Literal, cast

import click
from rich.console import Console

from license_analyzer import __version__
from license_analyzer.constants import EXIT_ERROR, EXIT_ISSUES, EXIT_SUCCESS
from license_analyzer.exceptions import LicenseAnalyzerError
from license_analyzer.models.scan import ScanOptions, ScanResult
from license_analyzer.output.terminal import TerminalFormatter
from license_analyzer.scanner import discover_packages, resolve_licenses

# Module-level console for consistent output
_console = Console()
# Separate console for error output (writes to stderr)
_error_console = Console(stderr=True)


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Python License Analyzer - Scan dependencies for license information.

    Analyze your Python project's dependencies for license compliance.
    Supports multiple output formats and provides confidence levels
    for each license detection.

    \b
    Examples:
        license-analyzer scan
        license-analyzer scan --format json
        license-analyzer scan --format markdown
    """
    pass


@main.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["terminal", "markdown", "json"], case_sensitive=False),
    default="terminal",
    help="Output format for scan results (default: terminal).",
)
def scan(output_format: str) -> None:
    """Scan Python project for license information.

    Discovers all installed packages in the current environment
    and retrieves their license information from multiple sources.

    \b
    Examples:
        license-analyzer scan
        license-analyzer scan --format json
        license-analyzer scan --format markdown > report.md
    """
    format_value = cast(Literal["terminal", "markdown", "json"], output_format.lower())
    options = ScanOptions(format=format_value)

    try:
        result = _run_scan(options)
        _display_result(result, options)

        # Exit with appropriate code based on issues found (FR35, FR36)
        if result.has_issues:
            sys.exit(EXIT_ISSUES)
        sys.exit(EXIT_SUCCESS)

    except LicenseAnalyzerError as e:
        # Display error and exit with error code (FR37, FR38, NFR14)
        _display_error(e, options.format)
        sys.exit(EXIT_ERROR)


def _run_scan(options: ScanOptions) -> ScanResult:
    """Execute the license scan.

    Args:
        options: Scan options for the scan.

    Returns:
        ScanResult with packages and calculated issues.
    """
    packages = discover_packages()

    # Show progress for terminal format (not for json/markdown)
    show_progress = options.format == "terminal"

    # Resolve licenses asynchronously with optional progress
    resolved = asyncio.run(
        resolve_licenses(
            packages,
            console=_console if show_progress else None,
            show_progress=show_progress,
        )
    )

    # Use factory method to calculate issues (packages with license=None)
    return ScanResult.from_packages(resolved)


def _display_result(result: ScanResult, options: ScanOptions) -> None:
    """Display scan results in the specified format."""
    if options.format == "terminal":
        formatter = TerminalFormatter(console=_console)
        formatter.format_scan_result(result)
    elif options.format == "json":
        # Placeholder for Story 5.2
        click.echo("JSON output not yet implemented")
    elif options.format == "markdown":
        # Placeholder for Story 5.1
        click.echo("Markdown output not yet implemented")


def _display_error(error: LicenseAnalyzerError, format_type: str) -> None:
    """Display error message to user.

    All errors are written to stderr for consistent CI/CD behavior.

    Args:
        error: The exception that occurred.
        format_type: Output format type for styling.
    """
    error_type = type(error).__name__
    message = f"Error: {error_type}: {error}"

    if format_type == "terminal":
        # Use stderr console for terminal errors (consistent with other formats)
        _error_console.print(f"[red bold]{message}[/red bold]")
    else:
        click.echo(message, err=True)


if __name__ == "__main__":
    main()
