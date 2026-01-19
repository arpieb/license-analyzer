"""Tests for scan models."""
from license_analyzer.models.scan import PackageLicense, ScanResult


class TestScanResult:
    """Tests for ScanResult model."""

    def test_from_packages_calculates_total(self) -> None:
        """Test that from_packages sets total_packages correctly."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="pydantic", version="2.0.0", license="MIT"),
        ]

        result = ScanResult.from_packages(packages)

        assert result.total_packages == 2

    def test_from_packages_counts_issues_for_none_licenses(self) -> None:
        """Test that from_packages counts packages with None license as issues."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="unknown-pkg", version="1.0.0", license=None),
            PackageLicense(name="pydantic", version="2.0.0", license="MIT"),
        ]

        result = ScanResult.from_packages(packages)

        assert result.issues_found == 1

    def test_from_packages_zero_issues_when_all_have_licenses(self) -> None:
        """Test that from_packages returns 0 issues when all packages have licenses."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="pydantic", version="2.0.0", license="MIT"),
        ]

        result = ScanResult.from_packages(packages)

        assert result.issues_found == 0

    def test_from_packages_all_issues_when_none_have_licenses(self) -> None:
        """Test that from_packages counts all packages as issues when none have licenses."""
        packages = [
            PackageLicense(name="pkg-a", version="1.0.0", license=None),
            PackageLicense(name="pkg-b", version="2.0.0", license=None),
        ]

        result = ScanResult.from_packages(packages)

        assert result.issues_found == 2

    def test_from_packages_empty_list(self) -> None:
        """Test that from_packages handles empty package list."""
        packages: list[PackageLicense] = []

        result = ScanResult.from_packages(packages)

        assert result.total_packages == 0
        assert result.issues_found == 0
        assert result.packages == []

    def test_from_packages_preserves_packages(self) -> None:
        """Test that from_packages preserves the package list."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]

        result = ScanResult.from_packages(packages)

        assert result.packages == packages

    def test_has_issues_true_when_issues_exist(self) -> None:
        """Test that has_issues returns True when issues_found > 0."""
        result = ScanResult(
            packages=[],
            total_packages=1,
            issues_found=1,
        )

        assert result.has_issues is True

    def test_has_issues_false_when_no_issues(self) -> None:
        """Test that has_issues returns False when issues_found == 0."""
        result = ScanResult(
            packages=[],
            total_packages=1,
            issues_found=0,
        )

        assert result.has_issues is False

    def test_from_packages_counts_empty_string_license_as_issue(self) -> None:
        """Test that empty string license is counted as an issue."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="MIT"),
            PackageLicense(name="empty-license", version="1.0.0", license=""),
        ]

        result = ScanResult.from_packages(packages)

        assert result.issues_found == 1
