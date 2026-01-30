"""Tests for JSON scan result formatter."""
import json
import re

from license_analyzer.constants import LEGAL_DISCLAIMER
from license_analyzer.models.scan import (
    IgnoredPackagesSummary,
    PackageLicense,
    ScanResult,
)
from license_analyzer.output.scan_json import ScanJsonFormatter


class TestScanJsonFormatter:
    """Tests for ScanJsonFormatter class."""

    def test_format_empty_result(self) -> None:
        """Test formatting empty result returns valid JSON."""
        formatter = ScanJsonFormatter()
        result = ScanResult(packages=[], total_packages=0, issues_found=0)

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["packages"] == []
        assert data["summary"]["total_packages"] == 0

    def test_format_single_package(self) -> None:
        """Test formatting result with single package."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert len(data["packages"]) == 1
        assert data["packages"][0]["name"] == "requests"
        assert data["packages"][0]["version"] == "2.28.0"
        assert data["packages"][0]["license"] == "Apache-2.0"

    def test_format_multiple_packages(self) -> None:
        """Test formatting result with multiple packages."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert len(data["packages"]) == 2

    def test_output_is_valid_json(self) -> None:
        """Test output is always valid parseable JSON."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)

        # Should not raise
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_output_is_pretty_printed(self) -> None:
        """Test output is indented for readability."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)

        # Pretty printed JSON has newlines and indentation
        assert "\n" in output
        assert "  " in output


class TestScanJsonFormatterMetadata:
    """Tests for scan_metadata section."""

    def test_scan_metadata_present(self) -> None:
        """Test scan_metadata section is present."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert "scan_metadata" in data

    def test_generated_at_is_iso8601(self) -> None:
        """Test generated_at timestamp is in ISO 8601 format."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        timestamp = data["scan_metadata"]["generated_at"]
        # ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
        iso8601_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
        assert re.match(iso8601_pattern, timestamp)

    def test_tool_version_present(self) -> None:
        """Test tool_version is present in metadata."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert "tool_version" in data["scan_metadata"]
        # Version should be a valid semver string
        assert isinstance(data["scan_metadata"]["tool_version"], str)
        assert len(data["scan_metadata"]["tool_version"]) > 0


class TestScanJsonFormatterSummary:
    """Tests for summary section."""

    def test_summary_section_present(self) -> None:
        """Test summary section is present."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert "summary" in data

    def test_summary_total_packages(self) -> None:
        """Test summary shows total package count."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
            PackageLicense(name="httpx", version="0.24.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["total_packages"] == 3

    def test_summary_licenses_found(self) -> None:
        """Test summary shows licenses found count."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["licenses_found"] == 1

    def test_summary_issues_found(self) -> None:
        """Test summary shows issues found count."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["issues_found"] == 1

    def test_summary_status_pass(self) -> None:
        """Test summary status is 'pass' when no issues."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["status"] == "pass"

    def test_summary_status_issues_found(self) -> None:
        """Test summary status is 'issues_found' when issues exist."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["status"] == "issues_found"

    def test_summary_has_issues_flag_true(self) -> None:
        """Test summary has_issues is true when issues exist."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["has_issues"] is True

    def test_summary_has_issues_flag_false(self) -> None:
        """Test summary has_issues is false when no issues."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["has_issues"] is False


class TestScanJsonFormatterPackages:
    """Tests for packages array."""

    def test_packages_array_present(self) -> None:
        """Test packages array is present."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert "packages" in data
        assert isinstance(data["packages"], list)

    def test_packages_sorted_alphabetically(self) -> None:
        """Test packages are sorted alphabetically by name."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="zlib", version="1.0.0", license="MIT"),
            PackageLicense(name="aiohttp", version="3.0.0", license="Apache-2.0"),
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        names = [pkg["name"] for pkg in data["packages"]]
        assert names == ["aiohttp", "requests", "zlib"]

    def test_packages_sorted_case_insensitive(self) -> None:
        """Test packages are sorted case-insensitively."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="Zlib", version="1.0.0", license="MIT"),
            PackageLicense(name="aiohttp", version="3.0.0", license="Apache-2.0"),
            PackageLicense(name="Requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        names = [pkg["name"] for pkg in data["packages"]]
        assert names == ["aiohttp", "Requests", "Zlib"]

    def test_package_has_license_true(self) -> None:
        """Test has_license is true when license exists."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["packages"][0]["has_license"] is True

    def test_package_has_license_false(self) -> None:
        """Test has_license is false when license is None."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["packages"][0]["has_license"] is False

    def test_package_license_null_in_json(self) -> None:
        """Test license is null in JSON when not found."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["packages"][0]["license"] is None


class TestScanJsonFormatterIssues:
    """Tests for issues array."""

    def test_issues_array_present(self) -> None:
        """Test issues array is present."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert "issues" in data
        assert isinstance(data["issues"], list)

    def test_issues_array_empty_when_no_issues(self) -> None:
        """Test issues array is empty when all packages have licenses."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["issues"] == []

    def test_issues_array_populated_when_issues(self) -> None:
        """Test issues array contains issues when packages have no license."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert len(data["issues"]) == 1
        assert data["issues"][0]["package"] == "unknown"
        assert data["issues"][0]["version"] == "1.0.0"

    def test_issue_has_type(self) -> None:
        """Test issue has issue_type field."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["issues"][0]["issue_type"] == "no_license"

    def test_issue_has_suggestion(self) -> None:
        """Test issue has suggestion field."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert "suggestion" in data["issues"][0]
        assert "Check package documentation" in data["issues"][0]["suggestion"]

    def test_issues_sorted_alphabetically(self) -> None:
        """Test issues are sorted alphabetically by package name."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="zlib-unknown", version="1.0.0", license=None),
            PackageLicense(name="aiohttp-unknown", version="3.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        packages = [issue["package"] for issue in data["issues"]]
        assert packages == ["aiohttp-unknown", "zlib-unknown"]


class TestScanJsonFormatterSnakeCase:
    """Tests for snake_case field naming."""

    def test_all_top_level_fields_snake_case(self) -> None:
        """Test all top-level fields use snake_case."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        for key in data:
            assert "_" in key or key.islower(), f"Key '{key}' is not snake_case"

    def test_scan_metadata_fields_snake_case(self) -> None:
        """Test scan_metadata fields use snake_case."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert "generated_at" in data["scan_metadata"]
        assert "tool_version" in data["scan_metadata"]
        # Verify no camelCase
        assert "generatedAt" not in data["scan_metadata"]
        assert "toolVersion" not in data["scan_metadata"]

    def test_summary_fields_snake_case(self) -> None:
        """Test summary fields use snake_case."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        expected_fields = [
            "total_packages",
            "licenses_found",
            "issues_found",
            "has_issues",
        ]
        for field in expected_fields:
            assert field in data["summary"], f"Missing field: {field}"

        # Verify no camelCase
        camel_case_fields = [
            "totalPackages",
            "licensesFound",
            "issuesFound",
            "hasIssues",
        ]
        for field in camel_case_fields:
            assert field not in data["summary"], f"Found camelCase: {field}"

    def test_package_fields_snake_case(self) -> None:
        """Test package fields use snake_case."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert "has_license" in data["packages"][0]
        assert "hasLicense" not in data["packages"][0]

    def test_issue_fields_snake_case(self) -> None:
        """Test issue fields use snake_case."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert "issue_type" in data["issues"][0]
        assert "issueType" not in data["issues"][0]


class TestScanJsonFormatterExecutiveSummary:
    """Tests for executive summary fields in JSON output."""

    def test_summary_has_overall_status(self) -> None:
        """Test summary includes overall_status field."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert "overall_status" in data["summary"]

    def test_summary_has_status_message(self) -> None:
        """Test summary includes status_message field."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert "status_message" in data["summary"]

    def test_overall_status_pass(self) -> None:
        """Test overall_status is PASS when no issues."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["overall_status"] == "PASS"

    def test_overall_status_issues_found(self) -> None:
        """Test overall_status is ISSUES_FOUND when issues exist."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["overall_status"] == "ISSUES_FOUND"

    def test_status_message_pass(self) -> None:
        """Test status_message when no issues."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["status_message"] == "All packages compatible"

    def test_status_message_issues_found(self) -> None:
        """Test status_message when issues exist."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown1", version="1.0.0", license=None),
            PackageLicense(name="unknown2", version="2.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["status_message"] == "2 issue(s) require attention"

    def test_status_fields_snake_case(self) -> None:
        """Test executive summary fields use snake_case."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        # Verify snake_case fields
        assert "overall_status" in data["summary"]
        assert "status_message" in data["summary"]
        # Verify no camelCase
        assert "overallStatus" not in data["summary"]
        assert "statusMessage" not in data["summary"]

    def test_existing_summary_fields_preserved(self) -> None:
        """Test existing summary fields are still present."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        # All existing fields should still be present
        assert "total_packages" in data["summary"]
        assert "licenses_found" in data["summary"]
        assert "issues_found" in data["summary"]
        assert "status" in data["summary"]
        assert "has_issues" in data["summary"]


class TestScanJsonFormatterEdgeCases:
    """Tests for edge cases."""

    def test_empty_string_license_treated_as_no_license(self) -> None:
        """Test empty string license is treated as no license (has_license=False)."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="pkg-empty-license", version="1.0.0", license=""),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        # Empty string license should be treated as no license
        assert data["packages"][0]["has_license"] is False
        assert data["packages"][0]["license"] == ""

    def test_section_order_in_output(self) -> None:
        """Test JSON sections appear in logical order."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)

        # Verify sections appear in expected order
        scan_metadata_pos = output.find('"scan_metadata"')
        summary_pos = output.find('"summary"')
        packages_pos = output.find('"packages"')
        issues_pos = output.find('"issues"')

        assert scan_metadata_pos < summary_pos < packages_pos < issues_pos

    def test_tool_version_matches_package_version(self) -> None:
        """Test tool_version uses actual package version."""
        from license_analyzer import __version__

        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["scan_metadata"]["tool_version"] == __version__

    def test_status_message_no_packages_scanned(self) -> None:
        """Test status_message when no packages scanned."""
        formatter = ScanJsonFormatter()
        result = ScanResult(packages=[], total_packages=0, issues_found=0)

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["overall_status"] == "PASS"
        assert data["summary"]["status_message"] == "No packages scanned"

    def test_status_message_singular_issue(self) -> None:
        """Test status_message with single issue uses correct pluralization."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["status_message"] == "1 issue(s) require attention"


class TestScanJsonFormatterDisclaimer:
    """Tests for legal disclaimer in JSON output."""

    def test_metadata_has_disclaimer(self) -> None:
        """Test scan_metadata includes disclaimer field."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert "disclaimer" in data["scan_metadata"]

    def test_metadata_has_disclaimer_type(self) -> None:
        """Test scan_metadata includes disclaimer_type field."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert "disclaimer_type" in data["scan_metadata"]

    def test_disclaimer_matches_constant(self) -> None:
        """Test disclaimer text matches the LEGAL_DISCLAIMER constant."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["scan_metadata"]["disclaimer"] == LEGAL_DISCLAIMER

    def test_disclaimer_type_is_informational(self) -> None:
        """Test disclaimer_type value is 'informational'."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["scan_metadata"]["disclaimer_type"] == "informational"

    def test_disclaimer_fields_snake_case(self) -> None:
        """Test disclaimer fields use snake_case naming."""
        formatter = ScanJsonFormatter()
        result = ScanResult.from_packages([
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ])

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        # Verify snake_case fields
        assert "disclaimer" in data["scan_metadata"]
        assert "disclaimer_type" in data["scan_metadata"]
        # Verify no camelCase
        assert "disclaimerType" not in data["scan_metadata"]


class TestScanJsonFormatterIgnoredPackages:
    """Tests for ignored packages in JSON output (FR24)."""

    def test_ignored_packages_in_summary(self) -> None:
        """Test that ignored_packages appears in summary when packages ignored."""
        formatter = ScanJsonFormatter()
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
        data = json.loads(output)

        assert data["summary"]["ignored_packages"] is not None
        assert data["summary"]["ignored_packages"]["count"] == 2
        assert data["summary"]["ignored_packages"]["names"] == ["pkg1", "pkg2"]

    def test_ignored_packages_null_when_none(self) -> None:
        """Test that ignored_packages is null when no summary."""
        formatter = ScanJsonFormatter()
        result = ScanResult(
            packages=[
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            ],
            total_packages=1,
            issues_found=0,
            ignored_packages_summary=None,
        )

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["ignored_packages"] is None

    def test_ignored_packages_null_when_zero_count(self) -> None:
        """Test that ignored_packages is null when count is 0."""
        formatter = ScanJsonFormatter()
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
        data = json.loads(output)

        assert data["summary"]["ignored_packages"] is None

    def test_ignored_packages_empty_names_list(self) -> None:
        """Test ignored_packages with count but None names uses empty list."""
        formatter = ScanJsonFormatter()
        result = ScanResult(
            packages=[
                PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            ],
            total_packages=1,
            issues_found=0,
            ignored_packages_summary=IgnoredPackagesSummary(
                ignored_count=2,
                ignored_names=None,
            ),
        )

        output = formatter.format_scan_result(result)
        data = json.loads(output)

        assert data["summary"]["ignored_packages"]["count"] == 2
        assert data["summary"]["ignored_packages"]["names"] == []
