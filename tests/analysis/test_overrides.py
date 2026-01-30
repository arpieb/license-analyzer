"""Tests for license override functionality."""

from license_analyzer.analysis.overrides import (
    apply_license_overrides,
    apply_overrides_to_tree,
)
from license_analyzer.models.config import AnalyzerConfig, LicenseOverride
from license_analyzer.models.dependency import DependencyNode, DependencyTree
from license_analyzer.models.scan import PackageLicense


class TestApplyLicenseOverrides:
    """Tests for apply_license_overrides function."""

    def test_applies_override_license(self) -> None:
        """Test that override license replaces detected license."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="Unknown"),
        ]
        config = AnalyzerConfig(
            overrides={
                "requests": LicenseOverride(
                    license="Apache-2.0",
                    reason="Verified from LICENSE file",
                ),
            }
        )

        result = apply_license_overrides(packages, config)

        assert len(result) == 1
        assert result[0].license == "Apache-2.0"

    def test_preserves_original_license(self) -> None:
        """Test that original license is preserved in original_license field."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ]
        config = AnalyzerConfig(
            overrides={
                "requests": LicenseOverride(
                    license="Apache-2.0",
                    reason="Verified from LICENSE file",
                ),
            }
        )

        result = apply_license_overrides(packages, config)

        assert result[0].original_license == "MIT"

    def test_preserves_none_original_license(self) -> None:
        """Test that None original license is preserved."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license=None),
        ]
        config = AnalyzerConfig(
            overrides={
                "requests": LicenseOverride(
                    license="MIT",
                    reason="Manually verified",
                ),
            }
        )

        result = apply_license_overrides(packages, config)

        assert result[0].original_license is None
        assert result[0].license == "MIT"

    def test_attaches_override_reason(self) -> None:
        """Test that override reason is attached to package."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="Unknown"),
        ]
        config = AnalyzerConfig(
            overrides={
                "requests": LicenseOverride(
                    license="MIT",
                    reason="Verified from LICENSE file",
                ),
            }
        )

        result = apply_license_overrides(packages, config)

        assert result[0].override_reason == "Verified from LICENSE file"

    def test_none_config_returns_unchanged(self) -> None:
        """Test that None overrides config returns packages unchanged."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]
        config = AnalyzerConfig(overrides=None)

        result = apply_license_overrides(packages, config)

        assert result == packages
        # Verify packages are not modified
        assert result[0].original_license is None
        assert result[0].override_reason is None

    def test_empty_overrides_returns_unchanged(self) -> None:
        """Test that empty overrides dict returns packages unchanged."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="MIT"),
        ]
        config = AnalyzerConfig(overrides={})

        result = apply_license_overrides(packages, config)

        assert result == packages

    def test_non_existent_package_no_error(self) -> None:
        """Test that override for non-existent package doesn't cause error."""
        packages = [
            PackageLicense(name="click", version="8.1.0", license="BSD-3-Clause"),
        ]
        config = AnalyzerConfig(
            overrides={
                "nonexistent": LicenseOverride(
                    license="MIT",
                    reason="Package not installed",
                ),
            }
        )

        result = apply_license_overrides(packages, config)

        # Package unchanged since override doesn't apply
        assert len(result) == 1
        assert result[0].name == "click"
        assert result[0].license == "BSD-3-Clause"
        assert result[0].override_reason is None

    def test_multiple_overrides(self) -> None:
        """Test multiple packages can be overridden."""
        packages = [
            PackageLicense(name="requests", version="2.28.0", license="Unknown"),
            PackageLicense(name="click", version="8.1.0", license="Unknown"),
            PackageLicense(name="pydantic", version="2.0.0", license="MIT"),
        ]
        config = AnalyzerConfig(
            overrides={
                "requests": LicenseOverride(
                    license="Apache-2.0",
                    reason="Verified from repo",
                ),
                "click": LicenseOverride(
                    license="BSD-3-Clause",
                    reason="Verified from PyPI",
                ),
            }
        )

        result = apply_license_overrides(packages, config)

        # Check requests was overridden
        requests_pkg = next(p for p in result if p.name == "requests")
        assert requests_pkg.license == "Apache-2.0"
        assert requests_pkg.is_overridden

        # Check click was overridden
        click_pkg = next(p for p in result if p.name == "click")
        assert click_pkg.license == "BSD-3-Clause"
        assert click_pkg.is_overridden

        # Check pydantic was NOT overridden
        pydantic_pkg = next(p for p in result if p.name == "pydantic")
        assert pydantic_pkg.license == "MIT"
        assert not pydantic_pkg.is_overridden

    def test_case_sensitive_matching(self) -> None:
        """Test that package name matching is case-sensitive."""
        packages = [
            PackageLicense(name="Requests", version="2.28.0", license="MIT"),
        ]
        config = AnalyzerConfig(
            overrides={
                "requests": LicenseOverride(  # lowercase
                    license="Apache-2.0",
                    reason="Override",
                ),
            }
        )

        result = apply_license_overrides(packages, config)

        # "Requests" != "requests", so should not be overridden
        assert result[0].license == "MIT"
        assert not result[0].is_overridden

    def test_preserves_package_order(self) -> None:
        """Test that package order is preserved."""
        packages = [
            PackageLicense(name="aaa", version="1.0.0", license="MIT"),
            PackageLicense(name="bbb", version="1.0.0", license="MIT"),
            PackageLicense(name="ccc", version="1.0.0", license="MIT"),
        ]
        config = AnalyzerConfig(
            overrides={
                "bbb": LicenseOverride(
                    license="Apache-2.0",
                    reason="Override middle package",
                ),
            }
        )

        result = apply_license_overrides(packages, config)

        assert result[0].name == "aaa"
        assert result[1].name == "bbb"
        assert result[2].name == "ccc"


class TestPackageLicenseIsOverridden:
    """Tests for PackageLicense.is_overridden property."""

    def test_is_overridden_true_when_reason_set(self) -> None:
        """Test is_overridden is True when override_reason is set."""
        pkg = PackageLicense(
            name="test",
            version="1.0.0",
            license="MIT",
            override_reason="Some reason",
        )

        assert pkg.is_overridden is True

    def test_is_overridden_false_when_reason_none(self) -> None:
        """Test is_overridden is False when override_reason is None."""
        pkg = PackageLicense(
            name="test",
            version="1.0.0",
            license="MIT",
            override_reason=None,
        )

        assert pkg.is_overridden is False

    def test_is_overridden_false_by_default(self) -> None:
        """Test is_overridden is False by default."""
        pkg = PackageLicense(
            name="test",
            version="1.0.0",
            license="MIT",
        )

        assert pkg.is_overridden is False

    def test_is_overridden_with_empty_reason(self) -> None:
        """Test is_overridden is True even with empty string reason."""
        pkg = PackageLicense(
            name="test",
            version="1.0.0",
            license="MIT",
            override_reason="",  # Empty string is still "set"
        )

        # Empty string is truthy for is not None check
        assert pkg.is_overridden is True


class TestApplyOverridesToTree:
    """Tests for apply_overrides_to_tree function."""

    def test_applies_override_to_root_node(self) -> None:
        """Test that override is applied to a root node."""
        tree = DependencyTree(
            roots=[
                DependencyNode(
                    name="requests",
                    version="2.28.0",
                    depth=0,
                    license="Unknown",
                    children=[],
                ),
            ],
        )
        config = AnalyzerConfig(
            overrides={
                "requests": LicenseOverride(
                    license="Apache-2.0",
                    reason="Verified",
                ),
            }
        )

        result = apply_overrides_to_tree(tree, config)

        assert result.roots[0].license == "Apache-2.0"

    def test_applies_override_to_child_node(self) -> None:
        """Test that override is applied to a child node."""
        tree = DependencyTree(
            roots=[
                DependencyNode(
                    name="requests",
                    version="2.28.0",
                    depth=0,
                    license="Apache-2.0",
                    children=[
                        DependencyNode(
                            name="urllib3",
                            version="2.0.0",
                            depth=1,
                            license="Unknown",
                            children=[],
                        ),
                    ],
                ),
            ],
        )
        config = AnalyzerConfig(
            overrides={
                "urllib3": LicenseOverride(
                    license="MIT",
                    reason="Verified",
                ),
            }
        )

        result = apply_overrides_to_tree(tree, config)

        assert result.roots[0].license == "Apache-2.0"  # Unchanged
        assert result.roots[0].children[0].license == "MIT"  # Overridden

    def test_applies_override_to_deeply_nested_node(self) -> None:
        """Test that override is applied to deeply nested nodes."""
        tree = DependencyTree(
            roots=[
                DependencyNode(
                    name="a",
                    version="1.0.0",
                    depth=0,
                    license="MIT",
                    children=[
                        DependencyNode(
                            name="b",
                            version="1.0.0",
                            depth=1,
                            license="MIT",
                            children=[
                                DependencyNode(
                                    name="c",
                                    version="1.0.0",
                                    depth=2,
                                    license="Unknown",
                                    children=[],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        config = AnalyzerConfig(
            overrides={
                "c": LicenseOverride(
                    license="BSD-3-Clause",
                    reason="Verified",
                ),
            }
        )

        result = apply_overrides_to_tree(tree, config)

        assert result.roots[0].children[0].children[0].license == "BSD-3-Clause"

    def test_none_overrides_returns_unchanged(self) -> None:
        """Test that None overrides returns tree unchanged."""
        tree = DependencyTree(
            roots=[
                DependencyNode(
                    name="requests",
                    version="2.28.0",
                    depth=0,
                    license="MIT",
                    children=[],
                ),
            ],
        )
        config = AnalyzerConfig(overrides=None)

        result = apply_overrides_to_tree(tree, config)

        assert result == tree

    def test_empty_overrides_returns_unchanged(self) -> None:
        """Test that empty overrides returns tree unchanged."""
        tree = DependencyTree(
            roots=[
                DependencyNode(
                    name="requests",
                    version="2.28.0",
                    depth=0,
                    license="MIT",
                    children=[],
                ),
            ],
        )
        config = AnalyzerConfig(overrides={})

        result = apply_overrides_to_tree(tree, config)

        assert result == tree

    def test_preserves_circular_references(self) -> None:
        """Test that circular references are preserved."""
        from license_analyzer.models.dependency import CircularReference

        tree = DependencyTree(
            roots=[
                DependencyNode(
                    name="a",
                    version="1.0.0",
                    depth=0,
                    license="MIT",
                    children=[],
                    circular_references=["b"],
                ),
            ],
            circular_references=[
                CircularReference(
                    from_package="a",
                    to_package="b",
                    path=["a", "b"],
                ),
            ],
        )
        config = AnalyzerConfig(
            overrides={
                "a": LicenseOverride(license="Apache-2.0", reason="Test"),
            }
        )

        result = apply_overrides_to_tree(tree, config)

        assert result.roots[0].circular_references == ["b"]
        assert len(result.circular_references) == 1
        assert result.circular_references[0].from_package == "a"

    def test_multiple_overrides_in_tree(self) -> None:
        """Test multiple packages can be overridden in a tree."""
        tree = DependencyTree(
            roots=[
                DependencyNode(
                    name="a",
                    version="1.0.0",
                    depth=0,
                    license="Unknown",
                    children=[
                        DependencyNode(
                            name="b",
                            version="1.0.0",
                            depth=1,
                            license="Unknown",
                            children=[],
                        ),
                    ],
                ),
                DependencyNode(
                    name="c",
                    version="1.0.0",
                    depth=0,
                    license="Unknown",
                    children=[],
                ),
            ],
        )
        config = AnalyzerConfig(
            overrides={
                "a": LicenseOverride(license="MIT", reason="Verified"),
                "b": LicenseOverride(license="Apache-2.0", reason="Verified"),
                "c": LicenseOverride(license="BSD-3-Clause", reason="Verified"),
            }
        )

        result = apply_overrides_to_tree(tree, config)

        assert result.roots[0].license == "MIT"
        assert result.roots[0].children[0].license == "Apache-2.0"
        assert result.roots[1].license == "BSD-3-Clause"
