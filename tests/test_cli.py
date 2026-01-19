"""CLI behavior tests for license-analyzer."""
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from license_analyzer import __version__
from license_analyzer.cli import main
from license_analyzer.constants import EXIT_ERROR, EXIT_ISSUES, EXIT_SUCCESS
from license_analyzer.exceptions import ConfigurationError, NetworkError, ScanError
from license_analyzer.models.scan import PackageLicense


def test_cli_help(cli_runner: CliRunner) -> None:
    """Test that --help outputs usage information."""
    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Python License Analyzer" in result.output
    assert "scan" in result.output
    assert "--version" in result.output


def test_cli_version(cli_runner: CliRunner) -> None:
    """Test that --version outputs correct version."""
    result = cli_runner.invoke(main, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output


def test_scan_command_runs(cli_runner: CliRunner) -> None:
    """Test that scan command runs without error."""
    result = cli_runner.invoke(main, ["scan"])

    # Exit code 0 (no issues) or 1 (issues found) both indicate successful scan
    assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
    # Terminal output shows Rich table with results
    assert "License Scan Results" in result.output


def test_scan_command_default_format(cli_runner: CliRunner) -> None:
    """Test that scan command uses terminal format by default."""
    result = cli_runner.invoke(main, ["scan"])

    # Exit code 0 (no issues) or 1 (issues found) both indicate successful scan
    assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
    # Terminal format displays a Rich table
    assert "License Scan Results" in result.output
    assert "Package" in result.output  # Table header


def test_scan_command_help(cli_runner: CliRunner) -> None:
    """Test that scan --help outputs command description."""
    result = cli_runner.invoke(main, ["scan", "--help"])

    assert result.exit_code == 0
    assert "Scan Python project" in result.output
    assert "--format" in result.output


def test_scan_help_shows_format_option(cli_runner: CliRunner) -> None:
    """Test that scan --help shows all format options."""
    result = cli_runner.invoke(main, ["scan", "--help"])

    assert result.exit_code == 0
    assert "--format" in result.output
    assert "terminal" in result.output
    assert "markdown" in result.output
    assert "json" in result.output


def test_scan_format_option_json(cli_runner: CliRunner) -> None:
    """Test that --format json is recognized."""
    result = cli_runner.invoke(main, ["scan", "--format", "json"])

    # Exit code 0 (no issues) or 1 (issues found) both indicate successful scan
    assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
    assert "JSON output not yet implemented" in result.output


def test_scan_format_option_markdown(cli_runner: CliRunner) -> None:
    """Test that --format markdown is recognized."""
    result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

    # Exit code 0 (no issues) or 1 (issues found) both indicate successful scan
    assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
    assert "Markdown output not yet implemented" in result.output


def test_scan_format_option_terminal(cli_runner: CliRunner) -> None:
    """Test that --format terminal is recognized."""
    result = cli_runner.invoke(main, ["scan", "--format", "terminal"])

    # Exit code 0 (no issues) or 1 (issues found) both indicate successful scan
    assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
    # Terminal format displays a Rich table
    assert "License Scan Results" in result.output


def test_scan_format_option_case_insensitive(cli_runner: CliRunner) -> None:
    """Test that --format is case insensitive."""
    result = cli_runner.invoke(main, ["scan", "--format", "JSON"])

    # Exit code 0 (no issues) or 1 (issues found) both indicate successful scan
    assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
    assert "JSON output not yet implemented" in result.output


def test_scan_format_option_invalid(cli_runner: CliRunner) -> None:
    """Test that invalid format shows error."""
    result = cli_runner.invoke(main, ["scan", "--format", "invalid"])

    assert result.exit_code != 0
    assert "Invalid value" in result.output


def test_scan_shows_package_count(cli_runner: CliRunner) -> None:
    """Test that scan output shows package count."""
    result = cli_runner.invoke(main, ["scan"])

    # Exit code 0 (no issues) or 1 (issues found) both indicate successful scan
    assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
    assert "Total packages:" in result.output


def test_scan_shows_issues_count(cli_runner: CliRunner) -> None:
    """Test that scan output shows issues count."""
    result = cli_runner.invoke(main, ["scan"])

    # Exit code 0 (no issues) or 1 (issues found) both indicate successful scan
    assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
    assert "Issues found:" in result.output


def test_scan_discovers_actual_packages(cli_runner: CliRunner) -> None:
    """Test that scan discovers actual installed packages."""
    result = cli_runner.invoke(main, ["scan"])

    # Exit code 0 (no issues) or 1 (issues found) both indicate successful scan
    assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
    # In a real environment with packages installed, the table should have rows
    assert "License Scan Results" in result.output
    # Should show total packages count
    assert "Total packages:" in result.output


def test_scan_empty_environment_shows_message(cli_runner: CliRunner) -> None:
    """Test that empty environment shows 'No packages found' message."""
    with patch("license_analyzer.cli.discover_packages", return_value=[]):
        result = cli_runner.invoke(main, ["scan"])

    assert result.exit_code == 0
    assert "No packages found" in result.output


def test_scan_empty_environment_exit_code_zero(cli_runner: CliRunner) -> None:
    """Test that empty environment returns exit code 0 (not an error)."""
    with patch("license_analyzer.cli.discover_packages", return_value=[]):
        result = cli_runner.invoke(main, ["scan"])

    assert result.exit_code == EXIT_SUCCESS


class TestExitCodes:
    """Tests for CLI exit codes."""

    def test_exit_code_0_when_all_licenses_resolved(
        self, cli_runner: CliRunner
    ) -> None:
        """Test exit code 0 when all packages have licenses (AC #1)."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="pydantic", version="2.0.0", license="MIT"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with patch("license_analyzer.cli.discover_packages", return_value=packages):
            with patch("license_analyzer.cli.resolve_licenses", mock_resolve):
                result = cli_runner.invoke(main, ["scan"])

        assert result.exit_code == EXIT_SUCCESS

    def test_exit_code_1_when_issues_found(self, cli_runner: CliRunner) -> None:
        """Test exit code 1 when packages have no license (AC #2)."""
        packages = [
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with patch("license_analyzer.cli.discover_packages", return_value=packages):
            with patch("license_analyzer.cli.resolve_licenses", mock_resolve):
                result = cli_runner.invoke(main, ["scan"])

        assert result.exit_code == EXIT_ISSUES

    def test_exit_code_2_on_network_error(self, cli_runner: CliRunner) -> None:
        """Test exit code 2 when network error occurs (AC #3)."""
        with patch(
            "license_analyzer.cli.discover_packages",
            side_effect=NetworkError("Connection failed"),
        ):
            result = cli_runner.invoke(main, ["scan"])

        assert result.exit_code == EXIT_ERROR

    def test_exit_code_2_on_configuration_error(self, cli_runner: CliRunner) -> None:
        """Test exit code 2 when configuration error occurs (AC #3)."""
        with patch(
            "license_analyzer.cli.discover_packages",
            side_effect=ConfigurationError("Invalid config"),
        ):
            result = cli_runner.invoke(main, ["scan"])

        assert result.exit_code == EXIT_ERROR

    def test_exit_code_2_on_scan_error(self, cli_runner: CliRunner) -> None:
        """Test exit code 2 when scan error occurs (AC #3)."""
        with patch(
            "license_analyzer.cli.discover_packages",
            side_effect=ScanError("Scan failed"),
        ):
            result = cli_runner.invoke(main, ["scan"])

        assert result.exit_code == EXIT_ERROR

    def test_error_message_displayed_on_error(self, cli_runner: CliRunner) -> None:
        """Test that clear error message is shown on error (AC #3, NFR14)."""
        with patch(
            "license_analyzer.cli.discover_packages",
            side_effect=NetworkError("Connection failed"),
        ):
            result = cli_runner.invoke(main, ["scan"])

        assert "NetworkError" in result.output or "Connection failed" in result.output

    def test_mixed_licenses_counts_issues_correctly(
        self, cli_runner: CliRunner
    ) -> None:
        """Test exit code 1 when some packages have licenses and some don't."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with patch("license_analyzer.cli.discover_packages", return_value=packages):
            with patch("license_analyzer.cli.resolve_licenses", mock_resolve):
                result = cli_runner.invoke(main, ["scan"])

        assert result.exit_code == EXIT_ISSUES

    def test_exit_code_2_on_resolve_licenses_error(
        self, cli_runner: CliRunner
    ) -> None:
        """Test exit code 2 when resolve_licenses raises an error (AC #3)."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license=None),
        ]

        mock_resolve = AsyncMock(side_effect=NetworkError("API rate limited"))

        with patch("license_analyzer.cli.discover_packages", return_value=packages):
            with patch("license_analyzer.cli.resolve_licenses", mock_resolve):
                result = cli_runner.invoke(main, ["scan"])

        assert result.exit_code == EXIT_ERROR

    def test_configuration_error_message_displayed(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that ConfigurationError shows clear error message (NFR14)."""
        with patch(
            "license_analyzer.cli.discover_packages",
            side_effect=ConfigurationError("Invalid YAML syntax"),
        ):
            result = cli_runner.invoke(main, ["scan"])

        assert "ConfigurationError" in result.output
        assert "Invalid YAML syntax" in result.output

    def test_scan_error_message_displayed(self, cli_runner: CliRunner) -> None:
        """Test that ScanError shows clear error message (NFR14)."""
        with patch(
            "license_analyzer.cli.discover_packages",
            side_effect=ScanError("Cannot access environment"),
        ):
            result = cli_runner.invoke(main, ["scan"])

        assert "ScanError" in result.output
        assert "Cannot access environment" in result.output
