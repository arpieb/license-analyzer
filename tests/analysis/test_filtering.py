"""Tests for package filtering functionality."""

from license_analyzer.analysis.filtering import FilterResult, filter_ignored_packages
from license_analyzer.models.config import AnalyzerConfig
from license_analyzer.models.scan import PackageLicense


class TestFilterIgnoredPackages:
    """Tests for filter_ignored_packages function."""

    def test_none_ignored_returns_all(self) -> None:
        """Test that None ignored_packages returns all packages."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]
        config = AnalyzerConfig(ignored_packages=None)

        result = filter_ignored_packages(packages, config)

        assert result.packages == packages
        assert result.ignored_count == 0
        assert result.ignored_names == []

    def test_empty_ignored_returns_all(self) -> None:
        """Test that empty ignored_packages list returns all packages."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
        ]
        config = AnalyzerConfig(ignored_packages=[])

        result = filter_ignored_packages(packages, config)

        assert result.packages == packages
        assert result.ignored_count == 0
        assert result.ignored_names == []

    def test_single_package_ignored(self) -> None:
        """Test filtering a single package."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]
        config = AnalyzerConfig(ignored_packages=["requests"])

        result = filter_ignored_packages(packages, config)

        assert len(result.packages) == 1
        assert result.packages[0].name == "click"
        assert result.ignored_count == 1
        assert result.ignored_names == ["requests"]

    def test_multiple_packages_ignored(self) -> None:
        """Test filtering multiple packages."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
            PackageLicense(name="pydantic", version="2.0.0", license="MIT"),
        ]
        config = AnalyzerConfig(ignored_packages=["requests", "click"])

        result = filter_ignored_packages(packages, config)

        assert len(result.packages) == 1
        assert result.packages[0].name == "pydantic"
        assert result.ignored_count == 2
        assert set(result.ignored_names) == {"requests", "click"}

    def test_all_packages_ignored(self) -> None:
        """Test filtering all packages."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]
        config = AnalyzerConfig(ignored_packages=["requests", "click"])

        result = filter_ignored_packages(packages, config)

        assert len(result.packages) == 0
        assert result.ignored_count == 2
        assert set(result.ignored_names) == {"requests", "click"}

    def test_nonexistent_package_in_ignore_list(self) -> None:
        """Test that nonexistent packages in ignore list don't cause errors."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
        ]
        config = AnalyzerConfig(ignored_packages=["nonexistent", "also-not-here"])

        result = filter_ignored_packages(packages, config)

        assert result.packages == packages
        assert result.ignored_count == 0
        assert result.ignored_names == []

    def test_mixed_existing_and_nonexistent(self) -> None:
        """Test ignore list with both existing and nonexistent packages."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]
        config = AnalyzerConfig(ignored_packages=["requests", "nonexistent"])

        result = filter_ignored_packages(packages, config)

        assert len(result.packages) == 1
        assert result.packages[0].name == "click"
        assert result.ignored_count == 1
        assert result.ignored_names == ["requests"]

    def test_empty_packages_list(self) -> None:
        """Test filtering empty packages list."""
        packages: list[PackageLicense] = []
        config = AnalyzerConfig(ignored_packages=["requests"])

        result = filter_ignored_packages(packages, config)

        assert result.packages == []
        assert result.ignored_count == 0
        assert result.ignored_names == []

    def test_case_sensitive_matching(self) -> None:
        """Test that package name matching is case-sensitive."""
        packages = [
            PackageLicense(name="Requests", version="2.28.0", license="Apache-2.0"),
        ]
        config = AnalyzerConfig(ignored_packages=["requests"])  # lowercase

        result = filter_ignored_packages(packages, config)

        # "Requests" != "requests", so should not be filtered
        assert len(result.packages) == 1
        assert result.packages[0].name == "Requests"
        assert result.ignored_count == 0

    def test_preserves_package_order(self) -> None:
        """Test that non-ignored packages maintain their order."""
        packages = [
            PackageLicense(name="aaa", version="1.0.0", license="MIT"),
            PackageLicense(name="bbb", version="1.0.0", license="MIT"),
            PackageLicense(name="ccc", version="1.0.0", license="MIT"),
            PackageLicense(name="ddd", version="1.0.0", license="MIT"),
        ]
        config = AnalyzerConfig(ignored_packages=["bbb"])

        result = filter_ignored_packages(packages, config)

        assert len(result.packages) == 3
        assert result.packages[0].name == "aaa"
        assert result.packages[1].name == "ccc"
        assert result.packages[2].name == "ddd"

    def test_default_config_no_filtering(self) -> None:
        """Test that default config (ignored_packages=None) does no filtering."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="Apache-2.0"),
        ]
        config = AnalyzerConfig()  # Default config

        result = filter_ignored_packages(packages, config)

        assert result.packages == packages
        assert result.ignored_count == 0


class TestFilterResult:
    """Tests for FilterResult namedtuple."""

    def test_filter_result_is_namedtuple(self) -> None:
        """Test that FilterResult is a proper NamedTuple."""
        result = FilterResult(packages=[], ignored_count=0, ignored_names=[])

        assert hasattr(result, "packages")
        assert hasattr(result, "ignored_count")
        assert hasattr(result, "ignored_names")

    def test_filter_result_fields_accessible(self) -> None:
        """Test FilterResult fields are accessible."""
        packages = [PackageLicense(name="test", version="1.0.0", license="MIT")]
        result = FilterResult(
            packages=packages,
            ignored_count=2,
            ignored_names=["pkg1", "pkg2"],
        )

        assert result.packages == packages
        assert result.ignored_count == 2
        assert result.ignored_names == ["pkg1", "pkg2"]

    def test_filter_result_unpacking(self) -> None:
        """Test FilterResult can be unpacked."""
        packages = [PackageLicense(name="test", version="1.0.0", license="MIT")]
        result = FilterResult(
            packages=packages,
            ignored_count=1,
            ignored_names=["ignored"],
        )

        pkgs, count, names = result

        assert pkgs == packages
        assert count == 1
        assert names == ["ignored"]
