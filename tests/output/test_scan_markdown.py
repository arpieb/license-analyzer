"""Tests for Markdown scan result formatter."""
from license_analyzer.constants import LEGAL_DISCLAIMER
from license_analyzer.models.scan import (
    IgnoredPackagesSummary,
    PackageLicense,
    ScanResult,
)
from license_analyzer.output.scan_markdown import ScanMarkdownFormatter


class TestScanMarkdownFormatter:
    """Tests for ScanMarkdownFormatter class."""

    def test_format_empty_result(self) -> None:
        """Test formatting empty result shows message."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult(packages=[], total_packages=0, issues_found=0)

        output = formatter.format_scan_result(result)

        assert "# License Scan Report" in output
        assert "*No packages found.*" in output

    def test_format_single_package(self) -> None:
        """Test formatting result with single package."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
        ])

        output = formatter.format_scan_result(result)

        assert "requests" in output
        assert "2.28.0" in output
        assert "Apache-2.0" in output

    def test_format_multiple_packages(self) -> None:
        """Test formatting result with multiple packages."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
        ])

        output = formatter.format_scan_result(result)

        assert "click" in output
        assert "requests" in output
        assert "BSD-3-Clause" in output
        assert "Apache-2.0" in output


class TestScanMarkdownFormatterTitle:
    """Tests for title and header."""

    def test_title_present(self) -> None:
        """Test report has title."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        assert "# License Scan Report" in output

    def test_timestamp_present(self) -> None:
        """Test report has timestamp."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        assert "*Generated:" in output
        assert "Z*" in output  # UTC timestamp ends with Z


class TestScanMarkdownFormatterSummary:
    """Tests for summary metrics (now in Executive Summary section)."""

    def test_summary_shows_total_packages(self) -> None:
        """Test summary shows total package count."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
            PackageLicense(name="httpx", version="0.24.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)

        assert "Total Packages" in output
        assert "| 3 |" in output

    def test_summary_shows_licenses_found(self) -> None:
        """Test summary shows licenses found count."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)

        assert "Licenses Found" in output
        assert "| 1 |" in output

    def test_summary_shows_issues_count(self) -> None:
        """Test summary shows issues count."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)

        assert "Issues" in output
        # Should show 1 issue
        lines = output.split("\n")
        issues_line = [line for line in lines if "Issues" in line and "1" in line]
        assert len(issues_line) > 0

    def test_status_badge_passing_when_no_issues(self) -> None:
        """Test status badge shows passing when no issues."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        assert "![Status]" in output
        assert "passing" in output
        assert "green" in output

    def test_status_badge_failing_when_issues(self) -> None:
        """Test status badge shows failing when issues exist."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)

        assert "![Status]" in output
        assert "failing" in output
        assert "red" in output


class TestScanMarkdownFormatterPackages:
    """Tests for packages table."""

    def test_packages_table_has_headers(self) -> None:
        """Test packages table has proper headers."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        assert "## Packages" in output
        assert "| Package | Version | License |" in output
        assert "|---------|---------|---------|" in output

    def test_packages_sorted_alphabetically(self) -> None:
        """Test packages are sorted alphabetically."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="zlib", version="1.0.0", license="MIT"),
            PackageLicense(name="aiohttp", version="3.0.0", license="Apache-2.0"),
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        # Find positions of package names in output
        aiohttp_pos = output.find("aiohttp")
        requests_pos = output.find("requests")
        zlib_pos = output.find("zlib")

        assert aiohttp_pos < requests_pos < zlib_pos

    def test_unknown_license_shows_warning_indicator(self) -> None:
        """Test packages with no license show warning indicator."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)

        assert "⚠️ Unknown" in output

    def test_empty_string_license_shows_warning(self) -> None:
        """Test packages with empty string license show warning indicator."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="empty-license-pkg", version="1.0.0", license=""),
        ])

        output = formatter.format_scan_result(result)

        assert "⚠️ Unknown" in output

    def test_packages_sorted_case_insensitive(self) -> None:
        """Test packages are sorted case-insensitively."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="Zlib", version="1.0.0", license="MIT"),
            PackageLicense(name="aiohttp", version="3.0.0", license="Apache-2.0"),
            PackageLicense(name="Requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        # Find positions - should be aiohttp < Requests < Zlib (case-insensitive)
        aiohttp_pos = output.find("aiohttp")
        requests_pos = output.find("Requests")
        zlib_pos = output.find("Zlib")

        assert aiohttp_pos < requests_pos < zlib_pos


class TestScanMarkdownFormatterIssues:
    """Tests for issues section."""

    def test_issues_section_absent_when_no_issues(self) -> None:
        """Test issues section is absent when all packages have licenses."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)

        assert "## Issues" not in output

    def test_issues_section_present_when_issues(self) -> None:
        """Test issues section is present when packages have no license."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)

        assert "## Issues" in output

    def test_issues_include_package_details(self) -> None:
        """Test issues include package name and version."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)

        assert "unknown-pkg" in output
        assert "1.0.0" in output
        assert "No license found" in output

    def test_issues_include_remediation(self) -> None:
        """Test issues include remediation suggestions."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)

        assert "Check package documentation" in output or "PyPI" in output

    def test_issues_show_count(self) -> None:
        """Test issues section shows count of issues."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="pkg1", version="1.0.0", license=None),
            PackageLicense(name="pkg2", version="2.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)

        assert "2 issue(s) require attention" in output

    def test_issues_positioned_after_summary(self) -> None:
        """Test issues section comes after summary but before packages."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)

        summary_pos = output.find("## Summary")
        issues_pos = output.find("## Issues")
        packages_pos = output.find("## Packages")

        assert summary_pos < issues_pos < packages_pos


class TestScanMarkdownFormatterExecutiveSummary:
    """Tests for executive summary section."""

    def test_executive_summary_present(self) -> None:
        """Test executive summary section is present."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        assert "## Executive Summary" in output

    def test_executive_summary_after_title(self) -> None:
        """Test executive summary appears after title but before status badge."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        title_pos = output.find("# License Scan Report")
        exec_summary_pos = output.find("## Executive Summary")
        status_pos = output.find("![Status]")

        assert title_pos < exec_summary_pos < status_pos

    def test_executive_summary_includes_total_packages(self) -> None:
        """Test executive summary shows total packages."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
            PackageLicense(name="httpx", version="0.24.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        # Executive summary should show total packages = 3
        exec_summary_start = output.find("## Executive Summary")
        exec_summary_end = output.find("![Status]")
        exec_summary = output[exec_summary_start:exec_summary_end]

        assert "Total Packages" in exec_summary
        assert "3" in exec_summary

    def test_executive_summary_includes_licenses_found(self) -> None:
        """Test executive summary shows licenses found."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)

        exec_summary_start = output.find("## Executive Summary")
        exec_summary_end = output.find("![Status]")
        exec_summary = output[exec_summary_start:exec_summary_end]

        assert "Licenses Found" in exec_summary
        assert "1" in exec_summary

    def test_executive_summary_includes_issues_count(self) -> None:
        """Test executive summary shows issues count."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)

        exec_summary_start = output.find("## Executive Summary")
        exec_summary_end = output.find("![Status]")
        exec_summary = output[exec_summary_start:exec_summary_end]

        assert "Issues" in exec_summary

    def test_executive_summary_status_pass(self) -> None:
        """Test executive summary shows PASS when no issues."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        exec_summary_start = output.find("## Executive Summary")
        exec_summary_end = output.find("![Status]")
        exec_summary = output[exec_summary_start:exec_summary_end]

        assert "PASS" in exec_summary
        assert "All packages compatible" in exec_summary

    def test_executive_summary_status_issues_found(self) -> None:
        """Test executive summary shows ISSUES FOUND when issues exist."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown", version="1.0.0", license=None),
            PackageLicense(name="another", version="2.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)

        exec_summary_start = output.find("## Executive Summary")
        exec_summary_end = output.find("![Status]")
        exec_summary = output[exec_summary_start:exec_summary_end]

        assert "ISSUES FOUND" in exec_summary
        assert "2 issue(s) require attention" in exec_summary

    def test_executive_summary_empty_result(self) -> None:
        """Test executive summary handling when no packages."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult(packages=[], total_packages=0, issues_found=0)

        output = formatter.format_scan_result(result)

        # Empty result should not have executive summary
        assert "## Executive Summary" not in output


class TestScanMarkdownFormatterStructure:
    """Tests for overall report structure."""

    def test_report_structure_order(self) -> None:
        """Test report sections are in correct order."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        title_pos = output.find("# License Scan Report")
        generated_pos = output.find("*Generated:")
        exec_summary_pos = output.find("## Executive Summary")
        status_pos = output.find("![Status]")
        packages_pos = output.find("## Packages")

        assert title_pos < generated_pos < exec_summary_pos < status_pos < packages_pos

    def test_report_is_valid_markdown(self) -> None:
        """Test report contains valid Markdown table syntax."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        # Check for table separators
        assert "|--------|" in output
        # Check for proper line structure
        lines = output.split("\n")
        table_lines = [line for line in lines if line.startswith("|")]
        assert len(table_lines) >= 3  # Header, separator, at least one row


class TestScanMarkdownFormatterDisclaimer:
    """Tests for legal disclaimer section."""

    def test_disclaimer_present(self) -> None:
        """Test disclaimer section is present in output."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        assert "NOT LEGAL ADVICE" in output

    def test_disclaimer_after_executive_summary(self) -> None:
        """Test disclaimer appears after executive summary."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        exec_summary_pos = output.find("## Executive Summary")
        disclaimer_pos = output.find("NOT LEGAL ADVICE")

        assert exec_summary_pos < disclaimer_pos

    def test_disclaimer_before_status_badge(self) -> None:
        """Test disclaimer appears before status badge."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        disclaimer_pos = output.find("NOT LEGAL ADVICE")
        status_pos = output.find("![Status]")

        assert disclaimer_pos < status_pos

    def test_disclaimer_contains_not_legal_advice(self) -> None:
        """Test disclaimer contains standard text about not being legal advice."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        assert "does not constitute legal advice" in output

    def test_disclaimer_has_warning_header(self) -> None:
        """Test disclaimer has blockquote format with header."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        assert "> **NOT LEGAL ADVICE**" in output

    def test_disclaimer_matches_constant(self) -> None:
        """Test disclaimer content matches the LEGAL_DISCLAIMER constant."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)

        assert LEGAL_DISCLAIMER in output

    def test_empty_result_shows_disclaimer(self) -> None:
        """Test disclaimer is shown even when no packages found."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult(packages=[], total_packages=0, issues_found=0)

        output = formatter.format_scan_result(result)

        assert "NOT LEGAL ADVICE" in output
        assert "No packages found" in output


class TestScanMarkdownFormatterIgnoredPackages:
    """Tests for ignored packages in Markdown output (FR24)."""

    def test_ignored_packages_in_executive_summary(self) -> None:
        """Test that ignored packages row appears in executive summary table."""
        formatter = ScanMarkdownFormatter()
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

        output = formatter.format_scan_result(result)

        assert "| Packages Ignored | 2 |" in output

    def test_ignored_packages_note_with_names(self) -> None:
        """Test that ignored package names appear in note."""
        formatter = ScanMarkdownFormatter()
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

        output = formatter.format_scan_result(result)

        assert "2 packages ignored: pkg1, pkg2" in output

    def test_no_ignored_packages_row_when_none(self) -> None:
        """Test that no ignored row appears when summary is None."""
        formatter = ScanMarkdownFormatter()
        result = ScanResult(
            packages=[
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            ],
            total_packages=1,
            issues_found=0,
            ignored_packages_summary=None,
        )

        output = formatter.format_scan_result(result)

        assert "Packages Ignored" not in output

    def test_no_ignored_packages_row_when_zero_count(self) -> None:
        """Test that no ignored row appears when count is 0."""
        formatter = ScanMarkdownFormatter()
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

        output = formatter.format_scan_result(result)

        assert "Packages Ignored" not in output
