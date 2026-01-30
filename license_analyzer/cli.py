"""CLI entry point for license-analyzer."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Literal, Optional, cast

import click
from rich.console import Console

from license_analyzer import __version__
from license_analyzer.analysis.filtering import filter_ignored_packages
from license_analyzer.analysis.overrides import (
    apply_license_overrides,
    apply_overrides_to_tree,
)
from license_analyzer.config import AnalyzerConfig, load_config
from license_analyzer.constants import EXIT_ERROR, EXIT_ISSUES, EXIT_SUCCESS
from license_analyzer.exceptions import ConfigurationError, LicenseAnalyzerError
from license_analyzer.models.dependency import CompatibilityMatrix, DependencyTree
from license_analyzer.models.scan import (
    IgnoredPackagesSummary,
    PackageLicense,
    ScanOptions,
    ScanResult,
    Verbosity,
)
from license_analyzer.output.matrix import MatrixFormatter
from license_analyzer.output.matrix_json import MatrixJsonFormatter
from license_analyzer.output.matrix_markdown import MatrixMarkdownFormatter
from license_analyzer.output.scan_json import ScanJsonFormatter
from license_analyzer.output.scan_markdown import ScanMarkdownFormatter
from license_analyzer.output.terminal import TerminalFormatter
from license_analyzer.output.tree import TreeFormatter
from license_analyzer.output.tree_json import TreeJsonFormatter
from license_analyzer.output.tree_markdown import TreeMarkdownFormatter
from license_analyzer.scanner import (
    attach_licenses_to_tree,
    discover_packages,
    resolve_dependency_tree,
    resolve_licenses,
)

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
        license-analyzer tree
        license-analyzer tree --format json
        license-analyzer tree --max-depth 2
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
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write report to file instead of stdout.",
)
@click.option(
    "--verbose",
    "-v",
    "verbose_flag",
    is_flag=True,
    default=False,
    help="Show detailed detection information.",
)
@click.option(
    "--quiet",
    "-q",
    "quiet_flag",
    is_flag=True,
    default=False,
    help="Suppress non-essential output.",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to configuration file.",
)
def scan(
    output_format: str,
    output_path: str | None,
    verbose_flag: bool,
    quiet_flag: bool,
    config_path: str | None,
) -> None:
    """Scan Python project for license information.

    Discovers all installed packages in the current environment
    and retrieves their license information from multiple sources.

    \b
    Examples:
        license-analyzer scan
        license-analyzer scan --format json
        license-analyzer scan --format markdown > report.md
        license-analyzer scan --output report.md --format markdown
        license-analyzer scan --verbose
        license-analyzer scan --quiet
        license-analyzer scan --config custom-config.yaml
    """
    # Validate mutual exclusivity
    if verbose_flag and quiet_flag:
        raise click.UsageError("--verbose and --quiet are mutually exclusive.")

    # Determine verbosity
    if quiet_flag:
        verbosity = Verbosity.QUIET
    elif verbose_flag:
        verbosity = Verbosity.VERBOSE
    else:
        verbosity = Verbosity.NORMAL

    format_value = cast(Literal["terminal", "markdown", "json"], output_format.lower())
    options = ScanOptions(format=format_value, verbosity=verbosity)

    try:
        # Load configuration (FR26, FR27)
        config = load_config(config_path)

        result = _run_scan(options, config)
        _display_result(result, options, output_path)

        # Exit with appropriate code based on issues found (FR35, FR36)
        if result.has_issues:
            sys.exit(EXIT_ISSUES)
        sys.exit(EXIT_SUCCESS)

    except LicenseAnalyzerError as e:
        # Display error and exit with error code (FR37, FR38, NFR14)
        _display_error(e, options.format)
        sys.exit(EXIT_ERROR)


@main.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["terminal", "markdown", "json"], case_sensitive=False),
    default="terminal",
    help="Output format for tree results (default: terminal).",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write report to file instead of stdout.",
)
@click.option(
    "--max-depth",
    type=int,
    default=None,
    help="Maximum depth to traverse (default: unlimited).",
)
@click.option(
    "--verbose",
    "-v",
    "verbose_flag",
    is_flag=True,
    default=False,
    help="Show detailed license source information.",
)
@click.option(
    "--quiet",
    "-q",
    "quiet_flag",
    is_flag=True,
    default=False,
    help="Show only summary and problematic licenses.",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to configuration file.",
)
@click.argument("packages", nargs=-1)
def tree(
    output_format: str,
    output_path: str | None,
    max_depth: Optional[int],
    verbose_flag: bool,
    quiet_flag: bool,
    config_path: str | None,
    packages: tuple[str, ...],
) -> None:
    """Display dependency tree with license information.

    Shows a hierarchical view of dependencies with color-coded licenses,
    problematic license warnings, and circular dependency indicators.

    If no packages are specified, shows tree for all direct dependencies
    discovered in the current environment.

    \b
    Examples:
        license-analyzer tree
        license-analyzer tree requests click
        license-analyzer tree --max-depth 2
        license-analyzer tree --format json
        license-analyzer tree --output tree.md --format markdown
        license-analyzer tree --verbose
        license-analyzer tree --quiet
        license-analyzer tree --config custom-config.yaml
    """
    # Validate mutual exclusivity
    if verbose_flag and quiet_flag:
        raise click.UsageError("--verbose and --quiet are mutually exclusive.")

    # Determine verbosity
    if quiet_flag:
        verbosity = Verbosity.QUIET
    elif verbose_flag:
        verbosity = Verbosity.VERBOSE
    else:
        verbosity = Verbosity.NORMAL

    format_value = output_format.lower()

    try:
        # Load configuration (FR26, FR27)
        config = load_config(config_path)

        # Determine which packages to analyze
        if packages:
            package_list = list(packages)
        else:
            # Get all installed packages as roots
            discovered = discover_packages()
            # Filter ignored packages (FR24)
            packages_as_license = [
                PackageLicense(name=pkg.name, version=pkg.version, license=None)
                for pkg in discovered
            ]
            filter_result = filter_ignored_packages(packages_as_license, config)
            package_list = [pkg.name for pkg in filter_result.packages]

        # Build dependency tree
        dep_tree = resolve_dependency_tree(package_list, max_depth=max_depth)

        # Show progress only for terminal format (not in quiet mode)
        show_progress = format_value == "terminal" and verbosity != Verbosity.QUIET

        # Attach licenses to tree nodes
        dep_tree_with_licenses = asyncio.run(
            attach_licenses_to_tree(
                dep_tree,
                console=_console if show_progress else None,
                show_progress=show_progress,
            )
        )

        # Apply manual license overrides (FR25)
        dep_tree_with_licenses = apply_overrides_to_tree(dep_tree_with_licenses, config)

        # Display the tree in requested format
        _display_tree(dep_tree_with_licenses, format_value, output_path, verbosity)

        # Exit with appropriate code based on problematic licenses
        problematic = dep_tree_with_licenses.get_nodes_with_problematic_licenses()
        if problematic:
            sys.exit(EXIT_ISSUES)
        sys.exit(EXIT_SUCCESS)

    except LicenseAnalyzerError as e:
        _display_error(e, format_value)
        sys.exit(EXIT_ERROR)


@main.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["terminal", "markdown", "json"], case_sensitive=False),
    default="terminal",
    help="Output format for matrix results (default: terminal).",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write report to file instead of stdout.",
)
@click.option(
    "--max-depth",
    type=int,
    default=None,
    help="Maximum depth to traverse for dependencies (default: unlimited).",
)
@click.option(
    "--verbose",
    "-v",
    "verbose_flag",
    is_flag=True,
    default=False,
    help="Show detailed compatibility reasoning.",
)
@click.option(
    "--quiet",
    "-q",
    "quiet_flag",
    is_flag=True,
    default=False,
    help="Show only incompatibility summary.",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to configuration file.",
)
@click.argument("packages", nargs=-1)
def matrix(
    output_format: str,
    output_path: str | None,
    max_depth: Optional[int],
    verbose_flag: bool,
    quiet_flag: bool,
    config_path: str | None,
    packages: tuple[str, ...],
) -> None:
    """Display license compatibility matrix.

    Shows a visual matrix of license compatibility relationships
    between all licenses found in your dependencies.

    If no packages are specified, analyzes all direct dependencies
    discovered in the current environment.

    \b
    Examples:
        license-analyzer matrix
        license-analyzer matrix requests click
        license-analyzer matrix --max-depth 2
        license-analyzer matrix --format json
        license-analyzer matrix --output matrix.md --format markdown
        license-analyzer matrix --verbose
        license-analyzer matrix --quiet
        license-analyzer matrix --config custom-config.yaml
    """
    # Validate mutual exclusivity
    if verbose_flag and quiet_flag:
        raise click.UsageError("--verbose and --quiet are mutually exclusive.")

    # Determine verbosity
    if quiet_flag:
        verbosity = Verbosity.QUIET
    elif verbose_flag:
        verbosity = Verbosity.VERBOSE
    else:
        verbosity = Verbosity.NORMAL

    format_value = output_format.lower()

    try:
        # Load configuration (FR26, FR27)
        config = load_config(config_path)

        # Determine which packages to analyze
        if packages:
            package_list = list(packages)
        else:
            # Get all installed packages as roots
            discovered = discover_packages()
            # Filter ignored packages (FR24)
            packages_as_license = [
                PackageLicense(name=pkg.name, version=pkg.version, license=None)
                for pkg in discovered
            ]
            filter_result = filter_ignored_packages(packages_as_license, config)
            package_list = [pkg.name for pkg in filter_result.packages]

        # Build dependency tree
        dep_tree = resolve_dependency_tree(package_list, max_depth=max_depth)

        # Show progress only for terminal format (not in quiet mode)
        show_progress = format_value == "terminal" and verbosity != Verbosity.QUIET

        # Attach licenses to tree nodes
        dep_tree_with_licenses = asyncio.run(
            attach_licenses_to_tree(
                dep_tree,
                console=_console if show_progress else None,
                show_progress=show_progress,
            )
        )

        # Apply manual license overrides (FR25)
        dep_tree_with_licenses = apply_overrides_to_tree(dep_tree_with_licenses, config)

        # Build compatibility matrix from tree
        compat_matrix = CompatibilityMatrix.from_dependency_tree(dep_tree_with_licenses)

        # Display the matrix in requested format
        _display_matrix(compat_matrix, format_value, output_path, verbosity)

        # Exit with appropriate code based on compatibility issues
        if compat_matrix.has_issues:
            sys.exit(EXIT_ISSUES)
        sys.exit(EXIT_SUCCESS)

    except LicenseAnalyzerError as e:
        _display_error(e, format_value)
        sys.exit(EXIT_ERROR)


def _write_output_to_file(content: str, path: str) -> None:
    """Write report content to file.

    Args:
        content: The report content to write.
        path: The file path to write to.

    Raises:
        ConfigurationError: If file cannot be written.
    """
    file_path = Path(path)

    try:
        if file_path.exists():
            _console.print(
                f"[yellow]Warning: Overwriting existing file: {path}[/yellow]"
            )

        file_path.write_text(content, encoding="utf-8")
        # Set appropriate permissions (user read/write, group/other read)
        file_path.chmod(0o644)
    except (OSError, PermissionError) as e:
        raise ConfigurationError(f"Cannot write to file '{path}': {e}") from e

    _console.print(f"[green]Report written to {path}[/green]")


def _display_matrix(
    matrix: CompatibilityMatrix,
    format_type: str,
    output_path: str | None = None,
    verbosity: Verbosity = Verbosity.NORMAL,
) -> None:
    """Display compatibility matrix in the specified format.

    Args:
        matrix: The compatibility matrix to display.
        format_type: Output format (terminal, json, markdown).
        output_path: Optional file path to write output to.
        verbosity: Output verbosity level.
    """
    # Get formatted content based on format type
    if format_type == "json":
        content = MatrixJsonFormatter().format_matrix(matrix)
    elif format_type == "markdown":
        content = MatrixMarkdownFormatter().format_matrix(matrix)
    else:  # terminal
        if output_path:
            # Terminal format to file uses markdown instead
            content = MatrixMarkdownFormatter().format_matrix(matrix)
        else:
            # Display directly to terminal with verbosity support
            MatrixFormatter(console=_console, verbosity=verbosity).format_matrix(matrix)
            return

    if output_path:
        _write_output_to_file(content, output_path)
    else:
        click.echo(content)


def _display_tree(
    tree: DependencyTree,
    format_type: str,
    output_path: str | None = None,
    verbosity: Verbosity = Verbosity.NORMAL,
) -> None:
    """Display dependency tree in the specified format.

    Args:
        tree: The dependency tree to display.
        format_type: Output format (terminal, json, markdown).
        output_path: Optional file path to write output to.
        verbosity: Output verbosity level.
    """
    # Get formatted content based on format type
    if format_type == "json":
        content = TreeJsonFormatter().format_dependency_tree(tree)
    elif format_type == "markdown":
        content = TreeMarkdownFormatter().format_dependency_tree(tree)
    else:  # terminal
        if output_path:
            # Terminal format to file uses markdown instead
            content = TreeMarkdownFormatter().format_dependency_tree(tree)
        else:
            # Display directly to terminal with verbosity support
            TreeFormatter(console=_console, verbosity=verbosity).format_dependency_tree(
                tree
            )
            return

    if output_path:
        _write_output_to_file(content, output_path)
    else:
        click.echo(content)


def _run_scan(options: ScanOptions, config: AnalyzerConfig) -> ScanResult:
    """Execute the license scan.

    Args:
        options: Scan options for the scan.
        config: Configuration for policy checking.

    Returns:
        ScanResult with packages, calculated issues, and policy violations.
    """
    packages = discover_packages()

    # Filter ignored packages BEFORE license resolution (FR24)
    # This avoids unnecessary API calls for ignored packages
    packages_as_license = [
        PackageLicense(name=pkg.name, version=pkg.version, license=None)
        for pkg in packages
    ]
    filter_result = filter_ignored_packages(packages_as_license, config)

    # Create ignored summary if any packages were ignored
    ignored_summary = None
    if filter_result.ignored_count > 0:
        ignored_summary = IgnoredPackagesSummary(
            ignored_count=filter_result.ignored_count,
            ignored_names=filter_result.ignored_names,
        )

    # Get the filtered package names for license resolution
    filtered_package_names = {pkg.name for pkg in filter_result.packages}
    filtered_packages = [pkg for pkg in packages if pkg.name in filtered_package_names]

    # Show progress for terminal format (not for json/markdown or quiet mode)
    show_progress = (
        options.format == "terminal" and options.verbosity != Verbosity.QUIET
    )

    # Resolve licenses asynchronously with optional progress
    resolved = asyncio.run(
        resolve_licenses(
            filtered_packages,
            console=_console if show_progress else None,
            show_progress=show_progress,
        )
    )

    # Apply manual license overrides AFTER resolution, BEFORE policy check (FR25)
    resolved_with_overrides = apply_license_overrides(resolved, config)

    # Use factory method to calculate issues and policy violations (FR23, FR24, FR25)
    return ScanResult.from_packages_with_config(
        resolved_with_overrides, config, ignored_summary
    )


def _display_result(
    result: ScanResult, options: ScanOptions, output_path: str | None = None
) -> None:
    """Display scan results in the specified format.

    Args:
        result: The scan result to display.
        options: Scan options including format.
        output_path: Optional file path to write output to.
    """
    # Get formatted content based on format type
    if options.format == "json":
        content = ScanJsonFormatter().format_scan_result(result)
    elif options.format == "markdown":
        content = ScanMarkdownFormatter().format_scan_result(result)
    else:  # terminal
        if output_path:
            # Terminal format to file uses markdown instead
            content = ScanMarkdownFormatter().format_scan_result(result)
        else:
            # Display directly to terminal with verbosity support
            TerminalFormatter(
                console=_console, verbosity=options.verbosity
            ).format_scan_result(result)
            return

    if output_path:
        _write_output_to_file(content, output_path)
    else:
        click.echo(content)


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
