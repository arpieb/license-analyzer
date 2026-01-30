"""Tests for terminal formatter."""

from io import StringIO

from rich.console import Console

from license_analyzer.models.scan import (
    IgnoredPackagesSummary,
    PackageLicense,
    ScanResult,
)
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


class TestTerminalFormatterExecutiveSummary:
    """Tests for executive summary in terminal output."""

    def test_executive_summary_displayed(self) -> None:
        """Test executive summary panel is displayed."""
        result = ScanResult.from_packages(
            [
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            ]
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "EXECUTIVE SUMMARY" in output

    def test_executive_summary_before_table(self) -> None:
        """Test executive summary appears before the packages table."""
        result = ScanResult.from_packages(
            [
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            ]
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        summary_pos = output.find("EXECUTIVE SUMMARY")
        table_pos = output.find("License Scan Results")

        assert summary_pos < table_pos

    def test_executive_summary_metrics(self) -> None:
        """Test executive summary includes all metrics."""
        result = ScanResult.from_packages(
            [
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
                PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
                PackageLicense(name="unknown", version="1.0.0", license=None),
            ]
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()

        # Check metrics are present
        assert "Total Packages" in output
        assert "3" in output
        assert "Licenses Found" in output
        assert "2" in output
        assert "Issues" in output

    def test_executive_summary_status_pass(self) -> None:
        """Test executive summary shows PASS status with green color."""
        result = ScanResult.from_packages(
            [
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            ]
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "PASS" in output
        assert "All packages compatible" in output

    def test_executive_summary_status_issues(self) -> None:
        """Test executive summary shows ISSUES FOUND status."""
        result = ScanResult.from_packages(
            [
                PackageLicense(name="unknown1", version="1.0.0", license=None),
                PackageLicense(name="unknown2", version="2.0.0", license=None),
            ]
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "ISSUES FOUND" in output
        assert "2 issue(s) require attention" in output

    def test_empty_result_no_executive_summary(self) -> None:
        """Test empty result doesn't show executive summary."""
        result = ScanResult(packages=[], total_packages=0, issues_found=0)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "EXECUTIVE SUMMARY" not in output


class TestTerminalFormatterSorting:
    """Tests for package sorting in terminal output."""

    def test_packages_sorted_alphabetically(self) -> None:
        """Test packages are sorted alphabetically by name."""
        result = ScanResult.from_packages(
            [
                PackageLicense(name="zlib", version="1.0.0", license="MIT"),
                PackageLicense(name="aiohttp", version="3.0.0", license="Apache-2.0"),
                PackageLicense(name="requests", version="2.28.0", license="MIT"),
            ]
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()

        # Find positions of package names in output
        aiohttp_pos = output.find("aiohttp")
        requests_pos = output.find("requests")
        zlib_pos = output.find("zlib")

        # Should be sorted: aiohttp < requests < zlib
        assert aiohttp_pos < requests_pos < zlib_pos


class TestTerminalFormatterDisclaimer:
    """Tests for legal disclaimer in terminal output."""

    def test_disclaimer_displayed(self) -> None:
        """Test disclaimer panel is displayed."""
        result = ScanResult.from_packages(
            [
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            ]
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "NOT LEGAL ADVICE" in output

    def test_disclaimer_after_executive_summary(self) -> None:
        """Test disclaimer appears after executive summary."""
        result = ScanResult.from_packages(
            [
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            ]
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        summary_pos = output.find("EXECUTIVE SUMMARY")
        disclaimer_pos = output.find("NOT LEGAL ADVICE")
        table_pos = output.find("License Scan Results")

        # Order should be: Executive Summary → Disclaimer → Table
        assert summary_pos < disclaimer_pos < table_pos

    def test_disclaimer_contains_key_text(self) -> None:
        """Test disclaimer contains informational purpose text."""
        result = ScanResult.from_packages(
            [
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            ]
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "informational purposes" in output

    def test_empty_result_shows_disclaimer(self) -> None:
        """Test disclaimer is shown even when no packages found."""
        result = ScanResult(packages=[], total_packages=0, issues_found=0)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "NOT LEGAL ADVICE" in output
        assert "No packages found" in output


class TestTerminalFormatterIgnoredPackages:
    """Tests for ignored packages display in terminal output (FR24)."""

    def test_ignored_packages_shown_in_summary(self) -> None:
        """Test that ignored packages count and names appear in executive summary."""
        result = ScanResult(
            packages=[
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            ],
            total_packages=1,
            issues_found=0,
            ignored_packages_summary=IgnoredPackagesSummary(
                ignored_count=2,
                ignored_names=["pkg1", "pkg2"],
            ),
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "Packages Ignored: 2" in output
        assert "pkg1" in output
        assert "pkg2" in output

    def test_ignored_packages_truncated_when_many(self) -> None:
        """Test that only first 3 package names shown when many ignored."""
        result = ScanResult(
            packages=[
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            ],
            total_packages=1,
            issues_found=0,
            ignored_packages_summary=IgnoredPackagesSummary(
                ignored_count=5,
                ignored_names=["pkg1", "pkg2", "pkg3", "pkg4", "pkg5"],
            ),
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "Packages Ignored: 5" in output
        assert "pkg1" in output
        assert "pkg2" in output
        assert "pkg3" in output
        assert "+2 more" in output

    def test_no_ignored_packages_line_when_none_ignored(self) -> None:
        """Test that no ignored line appears when ignored_packages_summary is None."""
        result = ScanResult(
            packages=[
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            ],
            total_packages=1,
            issues_found=0,
            ignored_packages_summary=None,
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "Packages Ignored" not in output

    def test_no_ignored_packages_line_when_zero_count(self) -> None:
        """Test that no ignored line appears when count is 0."""
        result = ScanResult(
            packages=[
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            ],
            total_packages=1,
            issues_found=0,
            ignored_packages_summary=IgnoredPackagesSummary(
                ignored_count=0,
                ignored_names=[],
            ),
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)

        formatter = TerminalFormatter(console=console)
        formatter.format_scan_result(result)

        output = string_io.getvalue()
        assert "Packages Ignored" not in output
