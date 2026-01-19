"""Tests for terminal formatter."""
from io import StringIO

from rich.console import Console

from license_analyzer.models.scan import PackageLicense, ScanResult
from license_analyzer.output.terminal import TerminalFormatter


class TestTerminalFormatter:
    """Tests for TerminalFormatter."""

    def test_formats_packages_as_table(self) -> None:
        """Test that packages are displayed in a table."""
        result = ScanResult(
            packages=[
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
                PackageLicense(name="pydantic", version="2.0.0", license="MIT"),
            ],
            total_packages=2,
            issues_found=0,
        )

        # Capture Rich output
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "click" in output
        assert "8.1.0" in output
        assert "BSD-3-Clause" in output
        assert "pydantic" in output
        assert "MIT" in output

    def test_handles_none_license(self) -> None:
        """Test that None license shows as Unknown."""
        result = ScanResult(
            packages=[
                PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
            ],
            total_packages=1,
            issues_found=0,
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "unknown-pkg" in output
        assert "Unknown" in output

    def test_empty_packages_shows_message(self) -> None:
        """Test that empty package list shows appropriate message."""
        result = ScanResult(packages=[], total_packages=0, issues_found=0)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "No packages found" in output

    def test_displays_summary_with_totals(self) -> None:
        """Test that summary displays total packages and issues."""
        result = ScanResult(
            packages=[
                PackageLicense(name="click", version="8.1.0", license="MIT"),
            ],
            total_packages=1,
            issues_found=3,
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "Total packages:" in output
        assert "1" in output
        assert "Issues found:" in output
        assert "3" in output

    def test_table_has_correct_headers(self) -> None:
        """Test that table has Package, Version, License headers."""
        result = ScanResult(
            packages=[
                PackageLicense(name="click", version="8.1.0", license="MIT"),
            ],
            total_packages=1,
            issues_found=0,
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "Package" in output
        assert "Version" in output
        assert "License" in output

    def test_table_title(self) -> None:
        """Test that table has correct title."""
        result = ScanResult(
            packages=[
                PackageLicense(name="click", version="8.1.0", license="MIT"),
            ],
            total_packages=1,
            issues_found=0,
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "License Scan Results" in output

    def test_multiple_packages_all_displayed(self) -> None:
        """Test that all packages are displayed in the table."""
        result = ScanResult(
            packages=[
                PackageLicense(name="package-a", version="1.0.0", license="MIT"),
                PackageLicense(name="package-b", version="2.0.0", license="Apache-2.0"),
                PackageLicense(name="package-c", version="3.0.0", license=None),
            ],
            total_packages=3,
            issues_found=0,
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "package-a" in output
        assert "package-b" in output
        assert "package-c" in output
        assert "MIT" in output
        assert "Apache-2.0" in output
        assert "Unknown" in output  # For None license

    def test_default_console_created(self) -> None:
        """Test that TerminalFormatter creates a console if not provided."""
        formatter = TerminalFormatter()
        assert formatter._console is not None

    def test_custom_console_used(self) -> None:
        """Test that custom console is used when provided."""
        string_io = StringIO()
        custom_console = Console(file=string_io, force_terminal=True)

        formatter = TerminalFormatter(console=custom_console)
        assert formatter._console is custom_console
