"""CLI behavior tests for license-analyzer."""
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from license_analyzer import __version__
from license_analyzer.cli import main
from license_analyzer.constants import EXIT_ERROR, EXIT_ISSUES, EXIT_SUCCESS
from license_analyzer.exceptions import ConfigurationError, NetworkError, ScanError
from license_analyzer.models.dependency import DependencyNode, DependencyTree
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
    # Should output JSON format
    assert '"scan_metadata"' in result.output


def test_scan_format_option_markdown(cli_runner: CliRunner) -> None:
    """Test that --format markdown is recognized."""
    result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

    # Exit code 0 (no issues) or 1 (issues found) both indicate successful scan
    assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
    # Should output Markdown format
    assert "# License Scan Report" in result.output


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
    # Should output JSON format
    assert '"scan_metadata"' in result.output


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


class TestTreeCommand:
    """Tests for tree command."""

    def test_tree_command_help(self, cli_runner: CliRunner) -> None:
        """Test that tree --help outputs command description."""
        result = cli_runner.invoke(main, ["tree", "--help"])

        assert result.exit_code == 0
        assert "dependency tree" in result.output.lower()
        assert "--max-depth" in result.output

    def test_tree_command_runs(self, cli_runner: CliRunner) -> None:
        """Test that tree command runs without error."""
        # Create mock tree
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="requests", version="2.31.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["tree"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        assert "Dependencies" in result.output or "Total packages:" in result.output

    def test_tree_with_specific_packages(self, cli_runner: CliRunner) -> None:
        """Test tree command with specific package arguments."""
        root = DependencyNode(
            name="click", version="8.1.0", depth=0, license="BSD-3-Clause"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["tree", "click"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)

    def test_tree_with_max_depth(self, cli_runner: CliRunner) -> None:
        """Test tree command with --max-depth option."""
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="requests", version="2.31.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ) as mock_resolve, patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["tree", "--max-depth", "2"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        # Verify max_depth was passed
        mock_resolve.assert_called_once()
        call_args = mock_resolve.call_args
        assert call_args[1]["max_depth"] == 2

    def test_tree_shows_summary(self, cli_runner: CliRunner) -> None:
        """Test that tree output shows summary statistics."""
        child = DependencyNode(
            name="urllib3", version="2.0.0", depth=1, license="MIT"
        )
        root = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            license="Apache-2.0",
            children=[child],
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="requests", version="2.31.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["tree"])

        assert "Total packages:" in result.output
        assert "Max depth:" in result.output

    def test_tree_exit_code_1_with_problematic_license(
        self, cli_runner: CliRunner
    ) -> None:
        """Test tree returns exit code 1 when problematic license found."""
        root = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="gpl-pkg", version="1.0.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["tree"])

        assert result.exit_code == EXIT_ISSUES

    def test_tree_exit_code_0_with_permissive_licenses(
        self, cli_runner: CliRunner
    ) -> None:
        """Test tree returns exit code 0 when all licenses permissive."""
        root = DependencyNode(
            name="click", version="8.1.0", depth=0, license="BSD-3-Clause"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="click", version="8.1.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["tree"])

        assert result.exit_code == EXIT_SUCCESS

    def test_tree_empty_returns_message(self, cli_runner: CliRunner) -> None:
        """Test tree with no dependencies shows message."""
        mock_tree = DependencyTree(roots=[])

        with patch("license_analyzer.cli.discover_packages", return_value=[]):
            with patch(
                "license_analyzer.cli.resolve_dependency_tree",
                return_value=mock_tree,
            ):
                with patch(
                    "license_analyzer.cli.attach_licenses_to_tree",
                    new_callable=AsyncMock,
                    return_value=mock_tree,
                ):
                    result = cli_runner.invoke(main, ["tree"])

        assert result.exit_code == EXIT_SUCCESS
        assert "No dependencies found" in result.output

    def test_tree_exit_code_2_on_error(self, cli_runner: CliRunner) -> None:
        """Test tree returns exit code 2 when error occurs."""
        with patch(
            "license_analyzer.cli.discover_packages",
            side_effect=ScanError("Failed to discover packages"),
        ):
            result = cli_runner.invoke(main, ["tree"])

        assert result.exit_code == EXIT_ERROR
        assert "ScanError" in result.output

    def test_tree_error_on_resolve_dependency_tree(
        self, cli_runner: CliRunner
    ) -> None:
        """Test tree handles resolve_dependency_tree errors gracefully."""
        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="pkg", version="1.0.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            side_effect=ScanError("Failed to resolve dependencies"),
        ):
            result = cli_runner.invoke(main, ["tree"])

        assert result.exit_code == EXIT_ERROR
        assert "ScanError" in result.output
        assert "Failed to resolve dependencies" in result.output


class TestTreeFormatOptions:
    """Tests for tree --format option."""

    def test_tree_format_help_shows_options(self, cli_runner: CliRunner) -> None:
        """Test that tree --help shows format options."""
        result = cli_runner.invoke(main, ["tree", "--help"])

        assert result.exit_code == 0
        assert "--format" in result.output
        assert "terminal" in result.output
        assert "json" in result.output
        assert "markdown" in result.output

    def test_tree_format_json_output(self, cli_runner: CliRunner) -> None:
        """Test tree --format json outputs valid JSON."""
        import json

        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="requests", version="2.31.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["tree", "--format", "json"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        # Should be valid JSON
        data = json.loads(result.output)
        assert "dependencies" in data
        assert "summary" in data

    def test_tree_format_markdown_output(self, cli_runner: CliRunner) -> None:
        """Test tree --format markdown outputs markdown."""
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="requests", version="2.31.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["tree", "--format", "markdown"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        assert "# Dependency Tree" in result.output
        assert "## Summary" in result.output

    def test_tree_format_terminal_default(self, cli_runner: CliRunner) -> None:
        """Test tree defaults to terminal format."""
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="requests", version="2.31.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["tree"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        # Should NOT be JSON (no opening brace)
        assert not result.output.strip().startswith("{")
        # Should show tree structure from Rich
        assert "Dependencies" in result.output or "Total packages:" in result.output

    def test_tree_format_case_insensitive(self, cli_runner: CliRunner) -> None:
        """Test tree --format is case insensitive."""
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="requests", version="2.31.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["tree", "--format", "JSON"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        assert result.output.strip().startswith("{")

    def test_tree_format_invalid(self, cli_runner: CliRunner) -> None:
        """Test tree with invalid format shows error."""
        result = cli_runner.invoke(main, ["tree", "--format", "invalid"])

        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_tree_json_exit_code_1_with_problematic(
        self, cli_runner: CliRunner
    ) -> None:
        """Test tree --format json still returns exit code 1 for problematic."""
        root = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="gpl-pkg", version="1.0.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["tree", "--format", "json"])

        assert result.exit_code == EXIT_ISSUES


class TestMatrixCommand:
    """Tests for matrix command."""

    def test_matrix_command_help(self, cli_runner: CliRunner) -> None:
        """Test that matrix --help outputs command description."""
        result = cli_runner.invoke(main, ["matrix", "--help"])

        assert result.exit_code == 0
        assert "compatibility matrix" in result.output.lower()
        assert "--max-depth" in result.output
        assert "--format" in result.output

    def test_matrix_command_runs(self, cli_runner: CliRunner) -> None:
        """Test that matrix command runs without error."""
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="requests", version="2.31.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["matrix"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        # Terminal output shows matrix
        assert "Compatibility" in result.output or "Matrix" in result.output

    def test_matrix_with_specific_packages(self, cli_runner: CliRunner) -> None:
        """Test matrix command with specific package arguments."""
        root = DependencyNode(
            name="click", version="8.1.0", depth=0, license="BSD-3-Clause"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["matrix", "click"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)

    def test_matrix_with_max_depth(self, cli_runner: CliRunner) -> None:
        """Test matrix command with --max-depth option."""
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="requests", version="2.31.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ) as mock_resolve, patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["matrix", "--max-depth", "2"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        # Verify max_depth was passed
        mock_resolve.assert_called_once()
        call_args = mock_resolve.call_args
        assert call_args[1]["max_depth"] == 2

    def test_matrix_exit_code_1_with_issues(self, cli_runner: CliRunner) -> None:
        """Test matrix returns exit code 1 when compatibility issues exist."""
        # GPL-2.0 and GPL-3.0 are incompatible
        root1 = DependencyNode(
            name="gpl2-pkg", version="1.0.0", depth=0, license="GPL-2.0"
        )
        root2 = DependencyNode(
            name="gpl3-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        mock_tree = DependencyTree(roots=[root1, root2])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="gpl2-pkg", version="1.0.0", license=None),
            PackageLicense(name="gpl3-pkg", version="1.0.0", license=None),
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["matrix"])

        assert result.exit_code == EXIT_ISSUES

    def test_matrix_exit_code_0_when_compatible(self, cli_runner: CliRunner) -> None:
        """Test matrix returns exit code 0 when all licenses compatible."""
        # MIT and Apache-2.0 are compatible
        root1 = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=0, license="MIT"
        )
        root2 = DependencyNode(
            name="apache-pkg", version="1.0.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root1, root2])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="mit-pkg", version="1.0.0", license=None),
            PackageLicense(name="apache-pkg", version="1.0.0", license=None),
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["matrix"])

        assert result.exit_code == EXIT_SUCCESS

    def test_matrix_exit_code_2_on_error(self, cli_runner: CliRunner) -> None:
        """Test matrix returns exit code 2 on error."""
        with patch(
            "license_analyzer.cli.discover_packages",
            side_effect=NetworkError("Connection failed"),
        ):
            result = cli_runner.invoke(main, ["matrix"])

        assert result.exit_code == EXIT_ERROR


class TestMatrixFormatOptions:
    """Tests for matrix --format option."""

    def test_matrix_format_json_output(self, cli_runner: CliRunner) -> None:
        """Test matrix --format json outputs valid JSON."""
        import json

        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="requests", version="2.31.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["matrix", "--format", "json"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        # Should be valid JSON
        data = json.loads(result.output)
        assert "licenses" in data
        assert "matrix" in data
        assert "summary" in data

    def test_matrix_format_markdown_output(self, cli_runner: CliRunner) -> None:
        """Test matrix --format markdown outputs markdown."""
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="requests", version="2.31.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["matrix", "--format", "markdown"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        assert "# License Compatibility Matrix" in result.output
        assert "## Summary" in result.output

    def test_matrix_format_terminal_default(self, cli_runner: CliRunner) -> None:
        """Test matrix defaults to terminal format."""
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="requests", version="2.31.0", license=None)
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["matrix"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        # Should NOT be JSON (no opening brace)
        assert not result.output.strip().startswith("{")

    def test_matrix_format_invalid(self, cli_runner: CliRunner) -> None:
        """Test matrix with invalid format shows error."""
        result = cli_runner.invoke(main, ["matrix", "--format", "invalid"])

        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_matrix_json_exit_code_1_with_issues(
        self, cli_runner: CliRunner
    ) -> None:
        """Test matrix --format json still returns exit code 1 for issues."""
        # GPL-2.0 and GPL-3.0 are incompatible
        root1 = DependencyNode(
            name="gpl2-pkg", version="1.0.0", depth=0, license="GPL-2.0"
        )
        root2 = DependencyNode(
            name="gpl3-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        mock_tree = DependencyTree(roots=[root1, root2])

        with patch("license_analyzer.cli.discover_packages", return_value=[
            PackageLicense(name="gpl2-pkg", version="1.0.0", license=None),
            PackageLicense(name="gpl3-pkg", version="1.0.0", license=None),
        ]), patch(
            "license_analyzer.cli.resolve_dependency_tree",
            return_value=mock_tree,
        ), patch(
            "license_analyzer.cli.attach_licenses_to_tree",
            new_callable=AsyncMock,
            return_value=mock_tree,
        ):
            result = cli_runner.invoke(main, ["matrix", "--format", "json"])

        assert result.exit_code == EXIT_ISSUES


class TestScanMarkdownFormat:
    """Tests for scan --format markdown output."""

    def test_scan_format_markdown_runs(self, cli_runner: CliRunner) -> None:
        """Test scan --format markdown runs successfully."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        assert "# License Scan Report" in result.output

    def test_scan_format_markdown_output_structure(
        self, cli_runner: CliRunner
    ) -> None:
        """Test scan --format markdown has correct structure."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

        assert result.exit_code == EXIT_SUCCESS
        # Check for expected sections
        assert "# License Scan Report" in result.output
        assert "## Executive Summary" in result.output
        assert "## Packages" in result.output
        # Check for expected content
        assert "click" in result.output
        assert "requests" in result.output
        assert "BSD-3-Clause" in result.output
        assert "Apache-2.0" in result.output

    def test_scan_format_markdown_no_progress(self, cli_runner: CliRunner) -> None:
        """Test scan --format markdown does not show progress indicators."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        # Progress indicators should not appear
        assert "Resolving licenses" not in result.output
        assert "Fetching" not in result.output

    def test_scan_format_markdown_with_issues(self, cli_runner: CliRunner) -> None:
        """Test scan --format markdown shows issues section when issues exist."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

        assert result.exit_code == EXIT_ISSUES
        assert "## Issues" in result.output
        assert "unknown-pkg" in result.output
        assert "No license found" in result.output

    def test_scan_format_markdown_empty_environment(
        self, cli_runner: CliRunner
    ) -> None:
        """Test scan --format markdown with no packages."""
        with patch("license_analyzer.cli.discover_packages", return_value=[]):
            result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

        assert result.exit_code == EXIT_SUCCESS
        assert "# License Scan Report" in result.output
        assert "*No packages found.*" in result.output

    def test_scan_format_markdown_status_badge_passing(
        self, cli_runner: CliRunner
    ) -> None:
        """Test scan --format markdown shows passing status badge."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

        assert result.exit_code == EXIT_SUCCESS
        assert "![Status]" in result.output
        assert "passing" in result.output
        assert "green" in result.output

    def test_scan_format_markdown_status_badge_failing(
        self, cli_runner: CliRunner
    ) -> None:
        """Test scan --format markdown shows failing status badge when issues."""
        packages = [
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

        assert result.exit_code == EXIT_ISSUES
        assert "![Status]" in result.output
        assert "failing" in result.output
        assert "red" in result.output

    def test_scan_format_markdown_pipeable_output(self, cli_runner: CliRunner) -> None:
        """Test scan --format markdown output is pipeable (no ANSI codes)."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

        assert result.exit_code == EXIT_SUCCESS
        # Output should be plain text without ANSI escape codes
        assert "\x1b[" not in result.output  # No ANSI escape sequences
        assert "\033[" not in result.output  # No ANSI escape sequences (alt format)
        # Should be valid Markdown that can be written to file
        assert result.output.startswith("# License Scan Report")


class TestScanJsonFormat:
    """Tests for scan --format json output."""

    def test_scan_format_json_runs(self, cli_runner: CliRunner) -> None:
        """Test scan --format json runs successfully."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)

    def test_scan_format_json_valid_json(self, cli_runner: CliRunner) -> None:
        """Test scan --format json outputs valid JSON."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        assert result.exit_code == EXIT_SUCCESS
        # Should be valid JSON
        import json
        data = json.loads(result.output)
        assert "scan_metadata" in data
        assert "summary" in data
        assert "packages" in data
        assert "issues" in data

    def test_scan_format_json_pipeable(self, cli_runner: CliRunner) -> None:
        """Test scan --format json output is pipeable (no ANSI codes)."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        assert result.exit_code == EXIT_SUCCESS
        # Output should be plain text without ANSI escape codes
        assert "\x1b[" not in result.output
        assert "\033[" not in result.output
        # Should start with JSON object
        assert result.output.strip().startswith("{")

    def test_scan_format_json_with_issues(self, cli_runner: CliRunner) -> None:
        """Test scan --format json includes issues when present."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        assert result.exit_code == EXIT_ISSUES
        import json
        data = json.loads(result.output)
        assert data["summary"]["has_issues"] is True
        assert len(data["issues"]) == 1
        assert data["issues"][0]["package"] == "unknown-pkg"

    def test_scan_format_json_empty_environment(self, cli_runner: CliRunner) -> None:
        """Test scan --format json with no packages."""
        with patch("license_analyzer.cli.discover_packages", return_value=[]):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        assert result.exit_code == EXIT_SUCCESS
        import json
        data = json.loads(result.output)
        assert data["packages"] == []
        assert data["summary"]["total_packages"] == 0

    def test_scan_format_json_status_pass(self, cli_runner: CliRunner) -> None:
        """Test scan --format json shows pass status when no issues."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        assert result.exit_code == EXIT_SUCCESS
        import json
        data = json.loads(result.output)
        assert data["summary"]["status"] == "pass"

    def test_scan_format_json_status_issues_found(self, cli_runner: CliRunner) -> None:
        """Test scan --format json shows issues_found status when issues."""
        packages = [
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        assert result.exit_code == EXIT_ISSUES
        import json
        data = json.loads(result.output)
        assert data["summary"]["status"] == "issues_found"

    def test_scan_format_json_pipeable_to_file(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test scan --format json can be piped to file and parsed (NFR9)."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        assert result.exit_code == EXIT_SUCCESS

        # Write output to file (simulating pipe)
        output_file = tmp_path / "scan-result.json"
        output_file.write_text(result.output)

        # Read back and parse (simulating CI/CD tool)
        import json
        with open(output_file) as f:
            data = json.load(f)

        # Verify all required sections are accessible
        assert data["scan_metadata"]["generated_at"]
        assert data["summary"]["total_packages"] == 2
        assert len(data["packages"]) == 2
        assert data["issues"] == []


class TestExecutiveSummaryCLI:
    """Tests for executive summary in CLI outputs."""

    def test_scan_terminal_shows_executive_summary(
        self, cli_runner: CliRunner
    ) -> None:
        """Test scan --format terminal shows executive summary."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "terminal"])

        assert result.exit_code == EXIT_SUCCESS
        assert "EXECUTIVE SUMMARY" in result.output
        assert "PASS" in result.output

    def test_scan_markdown_includes_executive_summary(
        self, cli_runner: CliRunner
    ) -> None:
        """Test scan --format markdown includes executive summary."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

        assert result.exit_code == EXIT_SUCCESS
        assert "## Executive Summary" in result.output
        assert "PASS" in result.output
        assert "All packages compatible" in result.output

    def test_scan_json_has_executive_summary_fields(
        self, cli_runner: CliRunner
    ) -> None:
        """Test scan --format json has executive summary fields."""
        import json

        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        assert result.exit_code == EXIT_SUCCESS
        data = json.loads(result.output)

        # Check executive summary fields
        assert data["summary"]["overall_status"] == "PASS"
        assert data["summary"]["status_message"] == "All packages compatible"

    def test_executive_summary_shows_issues_found(
        self, cli_runner: CliRunner
    ) -> None:
        """Test executive summary shows ISSUES FOUND when issues exist."""
        import json

        packages = [
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        assert result.exit_code == EXIT_ISSUES
        data = json.loads(result.output)

        assert data["summary"]["overall_status"] == "ISSUES_FOUND"
        assert "require attention" in data["summary"]["status_message"]


class TestDisclaimerCLI:
    """Tests for legal disclaimer in CLI outputs."""

    def test_scan_terminal_shows_disclaimer(self, cli_runner: CliRunner) -> None:
        """Test scan --format terminal shows legal disclaimer."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "terminal"])

        assert result.exit_code == EXIT_SUCCESS
        assert "NOT LEGAL ADVICE" in result.output

    def test_scan_markdown_includes_disclaimer(self, cli_runner: CliRunner) -> None:
        """Test scan --format markdown includes legal disclaimer."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

        assert result.exit_code == EXIT_SUCCESS
        assert "NOT LEGAL ADVICE" in result.output
        assert "does not constitute legal advice" in result.output

    def test_scan_json_has_disclaimer_in_metadata(
        self, cli_runner: CliRunner
    ) -> None:
        """Test scan --format json has disclaimer in metadata."""
        import json

        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        assert result.exit_code == EXIT_SUCCESS
        data = json.loads(result.output)

        # Check disclaimer in metadata
        assert "disclaimer" in data["scan_metadata"]
        assert "disclaimer_type" in data["scan_metadata"]
        assert "informational" in data["scan_metadata"]["disclaimer_type"]


class TestFileOutputUtility:
    """Unit tests for _write_output_to_file() function."""

    def test_write_output_creates_file(self, tmp_path: Path) -> None:
        """Test _write_output_to_file creates file with correct content."""
        from license_analyzer.cli import _write_output_to_file

        output_file = tmp_path / "test.txt"
        content = "Test content here"

        _write_output_to_file(content, str(output_file))

        assert output_file.exists()
        assert output_file.read_text() == content

    def test_write_output_sets_permissions(self, tmp_path: Path) -> None:
        """Test _write_output_to_file sets 0644 permissions."""
        from license_analyzer.cli import _write_output_to_file

        output_file = tmp_path / "test.txt"

        _write_output_to_file("content", str(output_file))

        # Verify permissions are 0644 (rw-r--r--)
        assert (output_file.stat().st_mode & 0o777) == 0o644

    def test_write_output_overwrites_existing(self, tmp_path: Path) -> None:
        """Test _write_output_to_file overwrites existing file."""
        from license_analyzer.cli import _write_output_to_file

        output_file = tmp_path / "test.txt"
        output_file.write_text("old content")

        _write_output_to_file("new content", str(output_file))

        assert output_file.read_text() == "new content"

    def test_write_output_invalid_path_raises_error(self) -> None:
        """Test _write_output_to_file raises ConfigurationError for invalid path."""
        import pytest

        from license_analyzer.cli import _write_output_to_file
        from license_analyzer.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError) as exc_info:
            _write_output_to_file("content", "/nonexistent/dir/file.txt")

        assert "Cannot write to file" in str(exc_info.value)

    def test_write_output_permission_denied_raises_error(self, tmp_path: Path) -> None:
        """Test _write_output_to_file raises error on permission denied."""
        import os

        import pytest

        from license_analyzer.cli import _write_output_to_file
        from license_analyzer.exceptions import ConfigurationError

        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                _write_output_to_file("content", str(readonly_dir / "file.txt"))

            assert "Cannot write to file" in str(exc_info.value)
        finally:
            # Restore permissions for cleanup
            os.chmod(readonly_dir, 0o755)


class TestScanOutputOption:
    """Tests for scan --output option."""

    def test_scan_output_creates_file(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test scan --output creates file with report content."""
        output_file = tmp_path / "report.md"
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(
                main, ["scan", "--format", "markdown", "--output", str(output_file)]
            )

        assert result.exit_code == EXIT_SUCCESS
        assert output_file.exists()
        content = output_file.read_text()
        assert "# License Scan Report" in content
        assert "click" in content

    def test_scan_output_json_format(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test scan --output with JSON format."""
        import json

        output_file = tmp_path / "report.json"
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(
                main, ["scan", "--format", "json", "--output", str(output_file)]
            )

        assert result.exit_code == EXIT_SUCCESS
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert "scan_metadata" in data
        assert "packages" in data

    def test_scan_output_shows_success_message(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test scan --output shows success message."""
        output_file = tmp_path / "report.md"
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(
                main, ["scan", "--format", "markdown", "--output", str(output_file)]
            )

        assert result.exit_code == EXIT_SUCCESS
        assert "Report written to" in result.output

    def test_scan_output_overwrites_with_warning(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test scan --output shows warning when overwriting."""
        output_file = tmp_path / "report.md"
        output_file.write_text("existing content")

        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(
                main, ["scan", "--format", "markdown", "--output", str(output_file)]
            )

        assert result.exit_code == EXIT_SUCCESS
        assert "Warning: Overwriting" in result.output
        # Verify content was overwritten
        assert "# License Scan Report" in output_file.read_text()

    def test_scan_output_invalid_path_exit_code_2(
        self, cli_runner: CliRunner
    ) -> None:
        """Test scan --output with invalid path returns exit code 2."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(
                main,
                ["scan", "--format", "markdown", "--output", "/nonexistent/dir/file.md"],
            )

        assert result.exit_code == EXIT_ERROR
        assert "Cannot write to file" in result.output

    def test_scan_output_terminal_format_uses_markdown(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test scan --output with terminal format uses markdown in file."""
        output_file = tmp_path / "report.txt"
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(
                main, ["scan", "--format", "terminal", "--output", str(output_file)]
            )

        assert result.exit_code == EXIT_SUCCESS
        content = output_file.read_text()
        # Should be markdown format, not Rich terminal codes
        assert "# License Scan Report" in content
        assert "\x1b[" not in content  # No ANSI codes


class TestTreeOutputOption:
    """Tests for tree --output option."""

    def test_tree_output_creates_file(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test tree --output creates file with report content."""
        output_file = tmp_path / "tree.md"

        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with (
            patch("license_analyzer.cli.discover_packages", return_value=[
                PackageLicense(name="requests", version="2.31.0", license=None)
            ]),
            patch("license_analyzer.cli.resolve_dependency_tree", return_value=mock_tree),
            patch(
                "license_analyzer.cli.attach_licenses_to_tree",
                new_callable=AsyncMock,
                return_value=mock_tree,
            ),
        ):
            result = cli_runner.invoke(
                main, ["tree", "--format", "markdown", "--output", str(output_file)]
            )

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        assert output_file.exists()
        content = output_file.read_text()
        assert "# Dependency Tree" in content

    def test_tree_output_json_format(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test tree --output with JSON format."""
        import json

        output_file = tmp_path / "tree.json"

        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with (
            patch("license_analyzer.cli.discover_packages", return_value=[
                PackageLicense(name="requests", version="2.31.0", license=None)
            ]),
            patch("license_analyzer.cli.resolve_dependency_tree", return_value=mock_tree),
            patch(
                "license_analyzer.cli.attach_licenses_to_tree",
                new_callable=AsyncMock,
                return_value=mock_tree,
            ),
        ):
            result = cli_runner.invoke(
                main, ["tree", "--format", "json", "--output", str(output_file)]
            )

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert "dependencies" in data


class TestMatrixOutputOption:
    """Tests for matrix --output option."""

    def test_matrix_output_creates_file(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test matrix --output creates file with report content."""
        output_file = tmp_path / "matrix.md"

        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with (
            patch("license_analyzer.cli.discover_packages", return_value=[
                PackageLicense(name="requests", version="2.31.0", license=None)
            ]),
            patch("license_analyzer.cli.resolve_dependency_tree", return_value=mock_tree),
            patch(
                "license_analyzer.cli.attach_licenses_to_tree",
                new_callable=AsyncMock,
                return_value=mock_tree,
            ),
        ):
            result = cli_runner.invoke(
                main, ["matrix", "--format", "markdown", "--output", str(output_file)]
            )

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        assert output_file.exists()
        content = output_file.read_text()
        assert "# License Compatibility Matrix" in content

    def test_matrix_output_json_format(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test matrix --output with JSON format."""
        import json

        output_file = tmp_path / "matrix.json"

        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with (
            patch("license_analyzer.cli.discover_packages", return_value=[
                PackageLicense(name="requests", version="2.31.0", license=None)
            ]),
            patch("license_analyzer.cli.resolve_dependency_tree", return_value=mock_tree),
            patch(
                "license_analyzer.cli.attach_licenses_to_tree",
                new_callable=AsyncMock,
                return_value=mock_tree,
            ),
        ):
            result = cli_runner.invoke(
                main, ["matrix", "--format", "json", "--output", str(output_file)]
            )

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert "licenses" in data
        assert "matrix" in data


class TestVerbosityOptions:
    """Tests for --verbose and --quiet options."""

    def test_scan_verbose_and_quiet_mutually_exclusive(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --verbose and --quiet together returns error."""
        result = cli_runner.invoke(main, ["scan", "--verbose", "--quiet"])

        assert result.exit_code == EXIT_ERROR
        assert "mutually exclusive" in result.output.lower()

    def test_tree_verbose_and_quiet_mutually_exclusive(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that tree --verbose and --quiet together returns error."""
        result = cli_runner.invoke(main, ["tree", "--verbose", "--quiet"])

        assert result.exit_code == EXIT_ERROR
        assert "mutually exclusive" in result.output.lower()

    def test_matrix_verbose_and_quiet_mutually_exclusive(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that matrix --verbose and --quiet together returns error."""
        result = cli_runner.invoke(main, ["matrix", "--verbose", "--quiet"])

        assert result.exit_code == EXIT_ERROR
        assert "mutually exclusive" in result.output.lower()

    def test_scan_quiet_suppresses_progress(self, cli_runner: CliRunner) -> None:
        """Test that scan --quiet suppresses progress indicators."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause")
        ]
        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--quiet"])

        assert result.exit_code == EXIT_SUCCESS
        # Quiet mode should show minimal output - no progress bar
        assert "Resolving" not in result.output

    def test_scan_quiet_shows_minimal_output(self, cli_runner: CliRunner) -> None:
        """Test that scan --quiet shows only status and issues."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="requests", version="2.31.0", license="Apache-2.0"),
        ]
        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--quiet"])

        assert result.exit_code == EXIT_SUCCESS
        # Should not show full table or executive summary panel
        assert "EXECUTIVE SUMMARY" not in result.output

    def test_scan_verbose_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that scan --verbose flag is accepted."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause")
        ]
        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--verbose"])

        # Should succeed (verbose is accepted)
        assert result.exit_code == EXIT_SUCCESS

    def test_tree_quiet_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that tree --quiet flag is accepted."""
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with (
            patch("license_analyzer.cli.discover_packages", return_value=[
                PackageLicense(name="requests", version="2.31.0", license=None)
            ]),
            patch(
                "license_analyzer.cli.resolve_dependency_tree", return_value=mock_tree
            ),
            patch(
                "license_analyzer.cli.attach_licenses_to_tree",
                new_callable=AsyncMock,
                return_value=mock_tree,
            ),
        ):
            result = cli_runner.invoke(main, ["tree", "--quiet"])

        # Should succeed (quiet is accepted)
        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)

    def test_matrix_quiet_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that matrix --quiet flag is accepted."""
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with (
            patch("license_analyzer.cli.discover_packages", return_value=[
                PackageLicense(name="requests", version="2.31.0", license=None)
            ]),
            patch(
                "license_analyzer.cli.resolve_dependency_tree", return_value=mock_tree
            ),
            patch(
                "license_analyzer.cli.attach_licenses_to_tree",
                new_callable=AsyncMock,
                return_value=mock_tree,
            ),
        ):
            result = cli_runner.invoke(main, ["matrix", "--quiet"])

        # Should succeed (quiet is accepted)
        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)

    def test_scan_short_flags_work(self, cli_runner: CliRunner) -> None:
        """Test that -v and -q short flags work."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause")
        ]
        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            # Test -v
            result_v = cli_runner.invoke(main, ["scan", "-v"])
            assert result_v.exit_code == EXIT_SUCCESS

            # Test -q
            result_q = cli_runner.invoke(main, ["scan", "-q"])
            assert result_q.exit_code == EXIT_SUCCESS

    def test_scan_quiet_with_issues_shows_issue_list(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that scan --quiet with issues shows status and issue list (AC2)."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ]
        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "--quiet"])

        assert result.exit_code == EXIT_ISSUES
        # Should show ISSUES FOUND status
        assert "ISSUES FOUND" in result.output
        # Should list the package with no license
        assert "unknown-pkg" in result.output
        # Should NOT show executive summary or full table
        assert "EXECUTIVE SUMMARY" not in result.output
        assert "License Scan Results" not in result.output

    def test_tree_verbose_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that tree --verbose flag is accepted."""
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with (
            patch("license_analyzer.cli.discover_packages", return_value=[
                PackageLicense(name="requests", version="2.31.0", license=None)
            ]),
            patch(
                "license_analyzer.cli.resolve_dependency_tree", return_value=mock_tree
            ),
            patch(
                "license_analyzer.cli.attach_licenses_to_tree",
                new_callable=AsyncMock,
                return_value=mock_tree,
            ),
        ):
            result = cli_runner.invoke(main, ["tree", "--verbose"])

        # Should succeed (verbose is accepted)
        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)

    def test_matrix_verbose_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that matrix --verbose flag is accepted."""
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with (
            patch("license_analyzer.cli.discover_packages", return_value=[
                PackageLicense(name="requests", version="2.31.0", license=None)
            ]),
            patch(
                "license_analyzer.cli.resolve_dependency_tree", return_value=mock_tree
            ),
            patch(
                "license_analyzer.cli.attach_licenses_to_tree",
                new_callable=AsyncMock,
                return_value=mock_tree,
            ),
        ):
            result = cli_runner.invoke(main, ["matrix", "--verbose"])

        # Should succeed (verbose is accepted)
        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)

    def test_tree_quiet_shows_summary_only(self, cli_runner: CliRunner) -> None:
        """Test that tree --quiet shows only summary and problematic licenses (AC5)."""
        child = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=1, license="GPL-3.0"
        )
        root = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            license="Apache-2.0",
            children=[child],
        )
        mock_tree = DependencyTree(roots=[root])

        with (
            patch("license_analyzer.cli.discover_packages", return_value=[
                PackageLicense(name="requests", version="2.31.0", license=None)
            ]),
            patch(
                "license_analyzer.cli.resolve_dependency_tree", return_value=mock_tree
            ),
            patch(
                "license_analyzer.cli.attach_licenses_to_tree",
                new_callable=AsyncMock,
                return_value=mock_tree,
            ),
        ):
            result = cli_runner.invoke(main, ["tree", "--quiet"])

        assert result.exit_code == EXIT_ISSUES
        # Should show ISSUES FOUND status with count
        assert "ISSUES FOUND" in result.output
        # Should list problematic license
        assert "GPL-3.0" in result.output
        # Should NOT show full tree structure (Dependencies header)
        assert "Dependencies" not in result.output
        # Should NOT show detailed stats sections
        assert "License Categories:" not in result.output

    def test_matrix_quiet_shows_incompatibility_only(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that matrix --quiet shows only incompatibility summary (AC6)."""
        # GPL-2.0 and GPL-3.0 are incompatible
        root1 = DependencyNode(
            name="gpl2-pkg", version="1.0.0", depth=0, license="GPL-2.0"
        )
        root2 = DependencyNode(
            name="gpl3-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        mock_tree = DependencyTree(roots=[root1, root2])

        with (
            patch("license_analyzer.cli.discover_packages", return_value=[
                PackageLicense(name="gpl2-pkg", version="1.0.0", license=None),
                PackageLicense(name="gpl3-pkg", version="1.0.0", license=None),
            ]),
            patch(
                "license_analyzer.cli.resolve_dependency_tree", return_value=mock_tree
            ),
            patch(
                "license_analyzer.cli.attach_licenses_to_tree",
                new_callable=AsyncMock,
                return_value=mock_tree,
            ),
        ):
            result = cli_runner.invoke(main, ["matrix", "--quiet"])

        assert result.exit_code == EXIT_ISSUES
        # Should show INCOMPATIBLE status
        assert "INCOMPATIBLE" in result.output
        # Should list incompatible pair
        assert "GPL-2.0" in result.output
        assert "GPL-3.0" in result.output
        # Should NOT show full matrix table
        assert "License Compatibility Matrix" not in result.output
        # Should NOT show legend
        assert "Legend:" not in result.output


class TestConfigOption:
    """Tests for --config option on CLI commands."""

    def test_scan_with_config_file(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that scan command accepts --config option with valid file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")

        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause")
        ]
        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(
                main, ["scan", "--config", str(config_file)]
            )

        # Should succeed - config was loaded
        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)

    def test_scan_with_custom_config_path(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test scan with -c short option for custom config path."""
        config_file = tmp_path / "my-config.yaml"
        config_file.write_text("ignored_packages:\n  - test-pkg\n")

        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause")
        ]
        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan", "-c", str(config_file)])

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)

    def test_scan_invalid_config_exit_code_2(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that invalid config file causes exit code 2."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("unknown_field: value\n")

        result = cli_runner.invoke(main, ["scan", "--config", str(config_file)])

        assert result.exit_code == EXIT_ERROR
        assert "ConfigurationError" in result.output
        assert "unknown_field" in result.output

    def test_scan_invalid_yaml_syntax_exit_code_2(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that invalid YAML syntax causes exit code 2."""
        config_file = tmp_path / "bad-syntax.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n  bad yaml here")

        result = cli_runner.invoke(main, ["scan", "--config", str(config_file)])

        assert result.exit_code == EXIT_ERROR
        assert "ConfigurationError" in result.output
        assert "Invalid YAML syntax" in result.output

    def test_scan_nonexistent_config_error(self, cli_runner: CliRunner) -> None:
        """Test that nonexistent config file path causes error."""
        result = cli_runner.invoke(
            main, ["scan", "--config", "/nonexistent/config.yaml"]
        )

        # Click validates exists=True, so this should fail
        assert result.exit_code == EXIT_ERROR

    def test_scan_without_config_uses_defaults(
        self, cli_runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that scan without --config uses defaults (no error)."""
        # Change to empty directory (no config file)
        monkeypatch.chdir(tmp_path)

        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause")
        ]
        mock_resolve = AsyncMock(return_value=packages)

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch("license_analyzer.cli.resolve_licenses", mock_resolve),
        ):
            result = cli_runner.invoke(main, ["scan"])

        # Should succeed with defaults
        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)

    def test_tree_with_config_option(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that tree command accepts --config option."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")

        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with (
            patch("license_analyzer.cli.discover_packages", return_value=[
                PackageLicense(name="requests", version="2.31.0", license=None)
            ]),
            patch(
                "license_analyzer.cli.resolve_dependency_tree", return_value=mock_tree
            ),
            patch(
                "license_analyzer.cli.attach_licenses_to_tree",
                new_callable=AsyncMock,
                return_value=mock_tree,
            ),
        ):
            result = cli_runner.invoke(
                main, ["tree", "--config", str(config_file)]
            )

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)

    def test_matrix_with_config_option(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that matrix command accepts --config option."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")

        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        mock_tree = DependencyTree(roots=[root])

        with (
            patch("license_analyzer.cli.discover_packages", return_value=[
                PackageLicense(name="requests", version="2.31.0", license=None)
            ]),
            patch(
                "license_analyzer.cli.resolve_dependency_tree", return_value=mock_tree
            ),
            patch(
                "license_analyzer.cli.attach_licenses_to_tree",
                new_callable=AsyncMock,
                return_value=mock_tree,
            ),
        ):
            result = cli_runner.invoke(
                main, ["matrix", "--config", str(config_file)]
            )

        assert result.exit_code in (EXIT_SUCCESS, EXIT_ISSUES)

    def test_scan_help_shows_config_option(self, cli_runner: CliRunner) -> None:
        """Test that scan --help shows --config option."""
        result = cli_runner.invoke(main, ["scan", "--help"])

        assert result.exit_code == 0
        assert "--config" in result.output
        assert "-c" in result.output

    def test_tree_help_shows_config_option(self, cli_runner: CliRunner) -> None:
        """Test that tree --help shows --config option."""
        result = cli_runner.invoke(main, ["tree", "--help"])

        assert result.exit_code == 0
        assert "--config" in result.output

    def test_matrix_help_shows_config_option(self, cli_runner: CliRunner) -> None:
        """Test that matrix --help shows --config option."""
        result = cli_runner.invoke(main, ["matrix", "--help"])

        assert result.exit_code == 0
        assert "--config" in result.output


class TestAllowedLicensesPolicy:
    """Tests for allowed_licenses configuration (FR23)."""

    def test_scan_all_allowed_exit_0(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test exit code 0 when all packages use allowed licenses."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n  - Apache-2.0\n")

        mock_packages = [
            PackageLicense(name="click", version="8.1.0", license="MIT"),
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=mock_packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=mock_packages,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan"])

        assert result.exit_code == EXIT_SUCCESS

    def test_scan_violation_exit_1(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test exit code 1 when policy violations found."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")

        mock_packages = [
            PackageLicense(name="click", version="8.1.0", license="MIT"),
            PackageLicense(name="gpl-pkg", version="1.0.0", license="GPL-3.0"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=mock_packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=mock_packages,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan"])

        assert result.exit_code == EXIT_ISSUES

    def test_violation_message_in_terminal_output(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that violation message appears in terminal output."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")

        mock_packages = [
            PackageLicense(name="gpl-pkg", version="1.0.0", license="GPL-3.0"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=mock_packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=mock_packages,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan"])

        assert "GPL-3.0" in result.output
        assert "not in allowed list" in result.output

    def test_violation_message_in_json_output(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that policy violations appear in JSON output."""
        import json

        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")

        mock_packages = [
            PackageLicense(name="gpl-pkg", version="1.0.0", license="GPL-3.0"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=mock_packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=mock_packages,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        data = json.loads(result.output)
        assert "policy_violations" in data
        assert len(data["policy_violations"]) == 1
        assert data["policy_violations"][0]["package_name"] == "gpl-pkg"
        assert data["policy_violations"][0]["detected_license"] == "GPL-3.0"

    def test_violation_message_in_markdown_output(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that policy violations appear in Markdown output."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")

        mock_packages = [
            PackageLicense(name="gpl-pkg", version="1.0.0", license="GPL-3.0"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=mock_packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=mock_packages,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

        assert "## Policy Violations" in result.output
        assert "gpl-pkg" in result.output
        assert "GPL-3.0" in result.output

    def test_no_policy_checking_without_config(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test no policy violations when allowed_licenses not configured."""
        # No config file - default config has allowed_licenses=None
        mock_packages = [
            PackageLicense(name="gpl-pkg", version="1.0.0", license="GPL-3.0"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=mock_packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=mock_packages,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan"])

        # No policy violations, so should pass
        assert result.exit_code == EXIT_SUCCESS
        assert "Policy Violations" not in result.output

    def test_unknown_license_flagged_when_policy_configured(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test unknown license is flagged when allowed_licenses configured."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")

        mock_packages = [
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=mock_packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=mock_packages,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan"])

        assert result.exit_code == EXIT_ISSUES
        assert "Unknown license" in result.output

    def test_custom_config_path_with_allowed_licenses(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test --config option with allowed_licenses."""
        config_file = tmp_path / "custom-config.yaml"
        config_file.write_text("allowed_licenses:\n  - Apache-2.0\n")

        mock_packages = [
            PackageLicense(name="mit-pkg", version="1.0.0", license="MIT"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=mock_packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=mock_packages,
            ),
        ):
            result = cli_runner.invoke(
                main, ["scan", "--config", str(config_file)]
            )

        # MIT not in allowed list (only Apache-2.0), so should fail
        assert result.exit_code == EXIT_ISSUES
        assert "MIT" in result.output
        assert "not in allowed list" in result.output

    def test_empty_allowed_list_flags_all_packages(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test empty allowed_licenses list flags all packages."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("allowed_licenses: []\n")

        mock_packages = [
            PackageLicense(name="pkg1", version="1.0.0", license="MIT"),
            PackageLicense(name="pkg2", version="1.0.0", license="Apache-2.0"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=mock_packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=mock_packages,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        import json
        data = json.loads(result.output)
        assert len(data["policy_violations"]) == 2

    def test_policy_violations_count_in_summary(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that policy violations count appears in JSON summary."""
        import json

        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("allowed_licenses:\n  - MIT\n")

        mock_packages = [
            PackageLicense(name="gpl-pkg", version="1.0.0", license="GPL-3.0"),
            PackageLicense(name="lgpl-pkg", version="1.0.0", license="LGPL-2.1"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=mock_packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=mock_packages,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        data = json.loads(result.output)
        assert data["summary"]["policy_violations_count"] == 2


class TestIgnoredPackagesCLI:
    """CLI integration tests for ignored packages feature (FR24)."""

    def test_ignored_packages_filtered_from_scan(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that packages in ignored_packages are filtered from scan."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("ignored_packages:\n  - ignored-pkg\n")

        all_packages = [
            PackageLicense(name="click", version="8.1.0", license=None),
            PackageLicense(name="ignored-pkg", version="1.0.0", license=None),
        ]
        resolved_packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=all_packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=resolved_packages,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        import json
        data = json.loads(result.output)
        # Should only have 1 package (click), not 2
        assert data["summary"]["total_packages"] == 1
        assert len(data["packages"]) == 1
        assert data["packages"][0]["name"] == "click"

    def test_ignored_packages_summary_in_json(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that ignored_packages summary appears in JSON output."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("ignored_packages:\n  - pkg1\n  - pkg2\n")

        all_packages = [
            PackageLicense(name="click", version="8.1.0", license=None),
            PackageLicense(name="pkg1", version="1.0.0", license=None),
            PackageLicense(name="pkg2", version="1.0.0", license=None),
        ]
        resolved_packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=all_packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=resolved_packages,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        import json
        data = json.loads(result.output)
        assert data["summary"]["ignored_packages"] is not None
        assert data["summary"]["ignored_packages"]["count"] == 2
        assert set(data["summary"]["ignored_packages"]["names"]) == {"pkg1", "pkg2"}

    def test_ignored_packages_summary_in_markdown(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that ignored_packages summary appears in Markdown output."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("ignored_packages:\n  - ignored-pkg\n")

        all_packages = [
            PackageLicense(name="click", version="8.1.0", license=None),
            PackageLicense(name="ignored-pkg", version="1.0.0", license=None),
        ]
        resolved_packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=all_packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=resolved_packages,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

        assert "Packages Ignored | 1" in result.output

    def test_ignored_packages_null_when_none_ignored(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that ignored_packages is null when no packages ignored."""
        # No config file, so no ignored packages
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=packages,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        import json
        data = json.loads(result.output)
        assert data["summary"]["ignored_packages"] is None

    def test_ignored_packages_nonexistent_not_counted(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that nonexistent packages in ignore list don't count."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text("ignored_packages:\n  - nonexistent-pkg\n")

        packages = [
            PackageLicense(name="click", version="8.1.0", license=None),
        ]
        resolved = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=resolved,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        import json
        data = json.loads(result.output)
        # No packages were actually ignored
        assert data["summary"]["ignored_packages"] is None
        assert data["summary"]["total_packages"] == 1


class TestLicenseOverridesCLI:
    """CLI integration tests for license override feature (FR25)."""

    def test_scan_applies_overrides(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that overrides are applied during scan."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text(
            "overrides:\n"
            "  requests:\n"
            "    license: Apache-2.0\n"
            "    reason: Verified from LICENSE file\n"
        )

        packages = [
            PackageLicense(name="requests", version="2.28.0", license=None),
        ]
        resolved = [
            PackageLicense(name="requests", version="2.28.0", license="Unknown"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=resolved,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        import json
        data = json.loads(result.output)
        assert data["packages"][0]["license"] == "Apache-2.0"
        assert data["packages"][0]["is_overridden"] is True

    def test_override_preserves_original_license_in_json(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that original license is preserved in JSON output."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text(
            "overrides:\n"
            "  requests:\n"
            "    license: MIT\n"
            "    reason: Corrected\n"
        )

        packages = [
            PackageLicense(name="requests", version="2.28.0", license=None),
        ]
        resolved = [
            PackageLicense(name="requests", version="2.28.0", license="Unknown-License"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=resolved,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        import json
        data = json.loads(result.output)
        assert data["packages"][0]["original_license"] == "Unknown-License"
        assert data["packages"][0]["override_reason"] == "Corrected"

    def test_override_count_in_json_summary(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that overrides_applied count appears in JSON summary."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text(
            "overrides:\n"
            "  requests:\n"
            "    license: MIT\n"
            "    reason: Verified\n"
            "  click:\n"
            "    license: BSD-3-Clause\n"
            "    reason: Verified\n"
        )

        packages = [
            PackageLicense(name="requests", version="2.28.0", license=None),
            PackageLicense(name="click", version="8.1.0", license=None),
        ]
        resolved = [
            PackageLicense(name="requests", version="2.28.0", license="Unknown"),
            PackageLicense(name="click", version="8.1.0", license="Unknown"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=resolved,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        import json
        data = json.loads(result.output)
        assert data["summary"]["overrides_applied"] == 2

    def test_override_marker_in_terminal_output(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that override info appears in terminal output."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text(
            "overrides:\n"
            "  requests:\n"
            "    license: MIT\n"
            "    reason: Verified\n"
        )

        packages = [
            PackageLicense(name="requests", version="2.28.0", license=None),
        ]
        resolved = [
            PackageLicense(name="requests", version="2.28.0", license="Unknown"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=resolved,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "terminal"])

        # Check that overrides count is shown in executive summary
        assert "Overrides Applied: 1" in result.output

    def test_override_section_in_markdown(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that Overrides Applied section appears in markdown."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text(
            "overrides:\n"
            "  requests:\n"
            "    license: MIT\n"
            "    reason: Verified from LICENSE\n"
        )

        packages = [
            PackageLicense(name="requests", version="2.28.0", license=None),
        ]
        resolved = [
            PackageLicense(name="requests", version="2.28.0", license="Unknown"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=resolved,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "markdown"])

        assert "## Overrides Applied" in result.output
        assert "Verified from LICENSE" in result.output

    def test_override_subject_to_allowed_licenses_policy(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that overridden license is still checked against allowed_licenses."""
        config_file = tmp_path / ".license-analyzer.yaml"
        config_file.write_text(
            "allowed_licenses:\n"
            "  - MIT\n"
            "overrides:\n"
            "  requests:\n"
            "    license: GPL-3.0\n"  # Not in allowed list
            "    reason: Verified\n"
        )

        packages = [
            PackageLicense(name="requests", version="2.28.0", license=None),
        ]
        resolved = [
            PackageLicense(name="requests", version="2.28.0", license="Unknown"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=resolved,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        import json
        data = json.loads(result.output)
        # GPL-3.0 should be flagged as policy violation
        assert data["summary"]["policy_violations_count"] == 1
        assert result.exit_code == 1  # Issues found

    def test_no_overrides_json_fields_default(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that override fields have correct defaults when no overrides."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license=None),
        ]
        resolved = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        with (
            patch("license_analyzer.cli.discover_packages", return_value=packages),
            patch(
                "license_analyzer.cli.resolve_licenses",
                new_callable=AsyncMock,
                return_value=resolved,
            ),
            patch("license_analyzer.config.loader.Path.cwd", return_value=tmp_path),
        ):
            result = cli_runner.invoke(main, ["scan", "--format", "json"])

        import json
        data = json.loads(result.output)
        assert data["packages"][0]["original_license"] is None
        assert data["packages"][0]["override_reason"] is None
        assert data["packages"][0]["is_overridden"] is False
        assert data["summary"]["overrides_applied"] == 0
