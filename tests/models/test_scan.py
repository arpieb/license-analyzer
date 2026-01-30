"""Tests for scan models."""

from license_analyzer.models.config import AnalyzerConfig
from license_analyzer.models.scan import (
    IgnoredPackagesSummary,
    PackageLicense,
    ScanOptions,
    ScanResult,
    Verbosity,
)


class TestVerbosity:
    """Tests for Verbosity enum."""

    def test_verbosity_has_quiet_value(self) -> None:
        """Test that Verbosity enum has QUIET value."""
        assert Verbosity.QUIET.value == "quiet"

    def test_verbosity_has_normal_value(self) -> None:
        """Test that Verbosity enum has NORMAL value."""
        assert Verbosity.NORMAL.value == "normal"

    def test_verbosity_has_verbose_value(self) -> None:
        """Test that Verbosity enum has VERBOSE value."""
        assert Verbosity.VERBOSE.value == "verbose"

    def test_verbosity_enum_has_three_values(self) -> None:
        """Test that Verbosity enum has exactly three values."""
        assert len(Verbosity) == 3


class TestScanOptions:
    """Tests for ScanOptions model."""

    def test_scan_options_accepts_verbosity(self) -> None:
        """Test that ScanOptions accepts verbosity parameter."""
        options = ScanOptions(verbosity=Verbosity.VERBOSE)

        assert options.verbosity == Verbosity.VERBOSE

    def test_scan_options_default_verbosity_is_normal(self) -> None:
        """Test that ScanOptions default verbosity is NORMAL."""
        options = ScanOptions()

        assert options.verbosity == Verbosity.NORMAL

    def test_scan_options_quiet_verbosity(self) -> None:
        """Test that ScanOptions accepts QUIET verbosity."""
        options = ScanOptions(verbosity=Verbosity.QUIET)

        assert options.verbosity == Verbosity.QUIET


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


class TestScanResultWithConfig:
    """Tests for ScanResult.from_packages_with_config factory method."""

    def test_from_packages_with_config_calculates_violations(self) -> None:
        """Test that from_packages_with_config detects policy violations."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="MIT"),
            PackageLicense(name="gpl-pkg", version="1.0.0", license="GPL-3.0"),
        ]
        config = AnalyzerConfig(allowed_licenses=["MIT"])

        result = ScanResult.from_packages_with_config(packages, config)

        assert len(result.policy_violations) == 1
        assert result.policy_violations[0].package_name == "gpl-pkg"

    def test_from_packages_with_config_no_violations_when_all_allowed(self) -> None:
        """Test that no violations when all licenses allowed."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="MIT"),
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
        ]
        config = AnalyzerConfig(allowed_licenses=["MIT", "Apache-2.0"])

        result = ScanResult.from_packages_with_config(packages, config)

        assert len(result.policy_violations) == 0

    def test_from_packages_with_config_no_policy_when_none(self) -> None:
        """Test that no policy checking when allowed_licenses is None."""
        packages = [
            PackageLicense(name="gpl-pkg", version="1.0.0", license="GPL-3.0"),
        ]
        config = AnalyzerConfig(allowed_licenses=None)

        result = ScanResult.from_packages_with_config(packages, config)

        assert len(result.policy_violations) == 0

    def test_from_packages_with_config_calculates_issues_too(self) -> None:
        """Test that issues_found is still calculated correctly."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="MIT"),
            PackageLicense(name="unknown", version="1.0.0", license=None),
        ]
        config = AnalyzerConfig(allowed_licenses=["MIT"])

        result = ScanResult.from_packages_with_config(packages, config)

        assert result.issues_found == 1  # unknown license
        assert len(result.policy_violations) == 1  # unknown is also a violation

    def test_from_packages_with_config_has_issues_with_violations(self) -> None:
        """Test that has_issues is True when policy violations exist."""
        packages = [
            PackageLicense(name="gpl-pkg", version="1.0.0", license="GPL-3.0"),
        ]
        config = AnalyzerConfig(allowed_licenses=["MIT"])

        result = ScanResult.from_packages_with_config(packages, config)

        assert result.has_issues is True
        assert result.issues_found == 0  # No missing licenses
        assert len(result.policy_violations) == 1  # But policy violation

    def test_from_packages_with_config_preserves_packages(self) -> None:
        """Test that packages are preserved in result."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="MIT"),
        ]
        config = AnalyzerConfig(allowed_licenses=["MIT"])

        result = ScanResult.from_packages_with_config(packages, config)

        assert result.packages == packages
        assert result.total_packages == 1

    def test_from_packages_with_config_accepts_ignored_summary(self) -> None:
        """Test that ignored_summary is stored in result."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="MIT"),
        ]
        config = AnalyzerConfig()
        ignored = IgnoredPackagesSummary(
            ignored_count=2,
            ignored_names=["pkg1", "pkg2"],
        )

        result = ScanResult.from_packages_with_config(packages, config, ignored)

        assert result.ignored_packages_summary is not None
        assert result.ignored_packages_summary.ignored_count == 2
        assert result.ignored_packages_summary.ignored_names == ["pkg1", "pkg2"]

    def test_from_packages_with_config_none_ignored_summary(self) -> None:
        """Test that ignored_summary defaults to None."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="MIT"),
        ]
        config = AnalyzerConfig()

        result = ScanResult.from_packages_with_config(packages, config)

        assert result.ignored_packages_summary is None


class TestIgnoredPackagesSummary:
    """Tests for IgnoredPackagesSummary model."""

    def test_ignored_packages_summary_creation(self) -> None:
        """Test basic IgnoredPackagesSummary creation."""
        summary = IgnoredPackagesSummary(
            ignored_count=3,
            ignored_names=["pkg1", "pkg2", "pkg3"],
        )

        assert summary.ignored_count == 3
        assert summary.ignored_names == ["pkg1", "pkg2", "pkg3"]

    def test_ignored_packages_summary_defaults(self) -> None:
        """Test IgnoredPackagesSummary default values."""
        summary = IgnoredPackagesSummary()

        assert summary.ignored_count == 0
        assert summary.ignored_names is None

    def test_ignored_packages_summary_zero_count(self) -> None:
        """Test IgnoredPackagesSummary with zero count."""
        summary = IgnoredPackagesSummary(ignored_count=0, ignored_names=[])

        assert summary.ignored_count == 0
        assert summary.ignored_names == []

    def test_ignored_packages_summary_with_empty_names(self) -> None:
        """Test IgnoredPackagesSummary with empty names list."""
        summary = IgnoredPackagesSummary(
            ignored_count=0,
            ignored_names=[],
        )

        assert summary.ignored_count == 0
        assert summary.ignored_names == []

    def test_ignored_packages_summary_none_names(self) -> None:
        """Test IgnoredPackagesSummary with None names."""
        summary = IgnoredPackagesSummary(
            ignored_count=1,
            ignored_names=None,
        )

        assert summary.ignored_count == 1
        assert summary.ignored_names is None
