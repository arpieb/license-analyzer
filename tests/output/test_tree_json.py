"""Tests for JSON tree output formatter."""
import json

from license_analyzer.models.dependency import (
    CircularReference,
    DependencyNode,
    DependencyTree,
)
from license_analyzer.output.tree_json import TreeJsonFormatter


class TestTreeJsonFormatter:
    """Tests for TreeJsonFormatter class."""

    def test_format_empty_tree(self) -> None:
        """Test formatting empty tree returns valid JSON."""
        formatter = TreeJsonFormatter()
        tree = DependencyTree(roots=[])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        assert data["dependencies"] == []
        assert data["summary"]["total_packages"] == 0

    def test_format_single_root(self) -> None:
        """Test formatting tree with single root node."""
        formatter = TreeJsonFormatter()
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        assert len(data["dependencies"]) == 1
        assert data["dependencies"][0]["name"] == "requests"
        assert data["dependencies"][0]["version"] == "2.31.0"
        assert data["dependencies"][0]["license"] == "Apache-2.0"

    def test_format_nested_tree(self) -> None:
        """Test formatting tree with nested children."""
        formatter = TreeJsonFormatter()

        grandchild = DependencyNode(
            name="idna", version="3.4", depth=2, license="BSD-3-Clause"
        )
        child = DependencyNode(
            name="urllib3",
            version="2.0.0",
            depth=1,
            license="MIT",
            children=[grandchild],
        )
        root = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            license="Apache-2.0",
            children=[child],
        )
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        # Check structure
        assert len(data["dependencies"]) == 1
        assert len(data["dependencies"][0]["children"]) == 1
        assert len(data["dependencies"][0]["children"][0]["children"]) == 1

        # Check values
        assert data["dependencies"][0]["children"][0]["name"] == "urllib3"
        assert data["dependencies"][0]["children"][0]["children"][0]["name"] == "idna"


class TestTreeJsonFormatterSummary:
    """Tests for summary in JSON output."""

    def test_summary_includes_totals(self) -> None:
        """Test summary includes total packages and depth."""
        formatter = TreeJsonFormatter()

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
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        assert data["summary"]["total_packages"] == 2
        assert data["summary"]["max_depth"] == 1
        assert data["summary"]["direct_dependencies"] == 1

    def test_summary_includes_problematic_count(self) -> None:
        """Test summary includes problematic license count."""
        formatter = TreeJsonFormatter()

        gpl_node = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        tree = DependencyTree(roots=[gpl_node])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        assert data["summary"]["problematic_licenses"] == 1

    def test_summary_includes_circular_info(self) -> None:
        """Test summary includes circular dependency info."""
        formatter = TreeJsonFormatter()

        root = DependencyNode(
            name="pkg-a",
            version="1.0.0",
            depth=0,
            license="MIT",
            circular_references=["pkg-b"],
        )
        circ_ref = CircularReference(
            from_package="pkg-a", to_package="pkg-b", path=["pkg-a", "pkg-b"]
        )
        tree = DependencyTree(roots=[root], circular_references=[circ_ref])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        assert data["summary"]["has_circular_dependencies"] is True
        assert data["summary"]["circular_dependency_count"] == 1


class TestTreeJsonFormatterProblematic:
    """Tests for problematic section in JSON output."""

    def test_problematic_list_populated(self) -> None:
        """Test problematic list contains flagged packages."""
        formatter = TreeJsonFormatter()

        gpl_node = DependencyNode(
            name="gpl-pkg",
            version="1.0.0",
            depth=1,
            license="GPL-3.0",
            origin_path=["root-pkg"],
        )
        root = DependencyNode(
            name="root-pkg",
            version="1.0.0",
            depth=0,
            license="MIT",
            children=[gpl_node],
        )
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        assert len(data["problematic"]) == 1
        assert data["problematic"][0]["name"] == "gpl-pkg"
        assert data["problematic"][0]["license"] == "GPL-3.0"
        assert "root-pkg" in data["problematic"][0]["path"]

    def test_problematic_list_empty_when_clean(self) -> None:
        """Test problematic list is empty for permissive licenses."""
        formatter = TreeJsonFormatter()

        root = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=0, license="MIT"
        )
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        assert data["problematic"] == []


class TestTreeJsonFormatterCircular:
    """Tests for circular references in JSON output."""

    def test_circular_references_listed(self) -> None:
        """Test circular references are listed in output."""
        formatter = TreeJsonFormatter()

        root = DependencyNode(
            name="pkg-a",
            version="1.0.0",
            depth=0,
            license="MIT",
            circular_references=["pkg-b"],
        )
        circ_ref = CircularReference(
            from_package="pkg-a", to_package="pkg-b", path=["pkg-a", "pkg-b"]
        )
        tree = DependencyTree(roots=[root], circular_references=[circ_ref])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        assert len(data["circular_references"]) == 1
        assert data["circular_references"][0]["from_package"] == "pkg-a"
        assert data["circular_references"][0]["to_package"] == "pkg-b"

    def test_node_includes_is_problematic_flag(self) -> None:
        """Test each node includes is_problematic flag."""
        formatter = TreeJsonFormatter()

        gpl_node = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        mit_node = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=0, license="MIT"
        )
        tree = DependencyTree(roots=[gpl_node, mit_node])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        gpl_dep = next(d for d in data["dependencies"] if d["name"] == "gpl-pkg")
        mit_dep = next(d for d in data["dependencies"] if d["name"] == "mit-pkg")

        assert gpl_dep["is_problematic"] is True
        assert mit_dep["is_problematic"] is False


class TestTreeJsonFormatterLicenseCategories:
    """Tests for license categories in JSON output."""

    def test_license_categories_present(self) -> None:
        """Test license_categories section is present in output."""
        formatter = TreeJsonFormatter()
        root = DependencyNode(
            name="pkg", version="1.0.0", depth=0, license="MIT"
        )
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        assert "license_categories" in data
        assert "permissive" in data["license_categories"]
        assert "copyleft" in data["license_categories"]
        assert "weak_copyleft" in data["license_categories"]
        assert "unknown" in data["license_categories"]

    def test_license_categories_structure(self) -> None:
        """Test each category has correct structure."""
        formatter = TreeJsonFormatter()
        root = DependencyNode(
            name="pkg", version="1.0.0", depth=0, license="MIT"
        )
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        permissive = data["license_categories"]["permissive"]
        assert "count" in permissive
        assert "percentage" in permissive
        assert "licenses" in permissive
        assert isinstance(permissive["licenses"], list)

    def test_license_categories_counts(self) -> None:
        """Test license categories have correct counts."""
        formatter = TreeJsonFormatter()

        mit_node = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=0, license="MIT"
        )
        gpl_node = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        tree = DependencyTree(roots=[mit_node, gpl_node])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        assert data["license_categories"]["permissive"]["count"] == 1
        assert data["license_categories"]["copyleft"]["count"] == 1
        assert data["license_categories"]["permissive"]["percentage"] == 50.0
        assert data["license_categories"]["copyleft"]["percentage"] == 50.0

    def test_license_categories_licenses_list(self) -> None:
        """Test licenses list contains unique license identifiers."""
        formatter = TreeJsonFormatter()

        mit_node1 = DependencyNode(
            name="mit-pkg1", version="1.0.0", depth=0, license="MIT"
        )
        mit_node2 = DependencyNode(
            name="mit-pkg2", version="1.0.0", depth=0, license="MIT"
        )
        apache_node = DependencyNode(
            name="apache-pkg", version="1.0.0", depth=0, license="Apache-2.0"
        )
        tree = DependencyTree(roots=[mit_node1, mit_node2, apache_node])

        result = formatter.format_dependency_tree(tree)
        data = json.loads(result)

        licenses = data["license_categories"]["permissive"]["licenses"]
        assert "MIT" in licenses
        assert "Apache-2.0" in licenses
        # MIT should only appear once despite two packages
        assert licenses.count("MIT") == 1
