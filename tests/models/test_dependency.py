"""Tests for dependency tree models."""
import pytest
from pydantic import ValidationError

from license_analyzer.models.dependency import (
    CategoryStatistics,
    CircularReference,
    CompatibilityResult,
    CompatibilityStatus,
    DependencyNode,
    DependencyTree,
    LicenseStatistics,
)


class TestDependencyNode:
    """Tests for DependencyNode model."""

    def test_create_node_with_required_fields(self) -> None:
        """Test creating a node with required fields."""
        node = DependencyNode(name="requests", version="2.31.0", depth=0)

        assert node.name == "requests"
        assert node.version == "2.31.0"
        assert node.depth == 0
        assert node.license is None
        assert node.children == []

    def test_create_node_with_all_fields(self) -> None:
        """Test creating a node with all fields."""
        child = DependencyNode(name="certifi", version="2023.7.22", depth=1)
        node = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            license="Apache-2.0",
            children=[child],
        )

        assert node.license == "Apache-2.0"
        assert len(node.children) == 1
        assert node.children[0].name == "certifi"

    def test_is_direct_true_for_depth_zero(self) -> None:
        """Test is_direct is True when depth is 0."""
        node = DependencyNode(name="requests", version="2.31.0", depth=0)
        assert node.is_direct is True

    def test_is_direct_false_for_depth_greater_than_zero(self) -> None:
        """Test is_direct is False when depth > 0."""
        node = DependencyNode(name="certifi", version="2023.7.22", depth=1)
        assert node.is_direct is False

        node2 = DependencyNode(name="urllib3", version="2.0.0", depth=5)
        assert node2.is_direct is False

    def test_get_all_descendants_empty(self) -> None:
        """Test get_all_descendants with no children."""
        node = DependencyNode(name="requests", version="2.31.0", depth=0)
        assert node.get_all_descendants() == []

    def test_get_all_descendants_one_level(self) -> None:
        """Test get_all_descendants with one level of children."""
        child1 = DependencyNode(name="certifi", version="2023.7.22", depth=1)
        child2 = DependencyNode(name="urllib3", version="2.0.0", depth=1)
        node = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            children=[child1, child2],
        )

        descendants = node.get_all_descendants()
        assert len(descendants) == 2
        assert child1 in descendants
        assert child2 in descendants

    def test_get_all_descendants_multiple_levels(self) -> None:
        """Test get_all_descendants with nested children."""
        grandchild = DependencyNode(name="idna", version="3.4", depth=2)
        child = DependencyNode(
            name="urllib3",
            version="2.0.0",
            depth=1,
            children=[grandchild],
        )
        node = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            children=[child],
        )

        descendants = node.get_all_descendants()
        assert len(descendants) == 2
        assert child in descendants
        assert grandchild in descendants

    def test_model_forbids_extra_fields(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            DependencyNode(
                name="requests",
                version="2.31.0",
                depth=0,
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_depth_must_be_non_negative(self) -> None:
        """Test that negative depth values are rejected."""
        with pytest.raises(ValidationError):
            DependencyNode(name="requests", version="2.31.0", depth=-1)

    def test_model_serialization_includes_computed_field(self) -> None:
        """Test that is_direct computed field is included in model_dump()."""
        node = DependencyNode(name="requests", version="2.31.0", depth=0)
        dumped = node.model_dump()

        assert "is_direct" in dumped
        assert dumped["is_direct"] is True

    def test_circular_references_default_empty(self) -> None:
        """Test that circular_references defaults to empty list."""
        node = DependencyNode(name="requests", version="2.31.0", depth=0)
        assert node.circular_references == []

    def test_circular_references_can_be_set(self) -> None:
        """Test that circular_references can be populated."""
        node = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            circular_references=["urllib3", "certifi"],
        )
        assert node.circular_references == ["urllib3", "certifi"]

    def test_has_circular_references_false_when_empty(self) -> None:
        """Test has_circular_references is False when no circular refs."""
        node = DependencyNode(name="requests", version="2.31.0", depth=0)
        assert node.has_circular_references is False

    def test_has_circular_references_true_when_populated(self) -> None:
        """Test has_circular_references is True when circular refs exist."""
        node = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            circular_references=["urllib3"],
        )
        assert node.has_circular_references is True

    def test_circular_references_included_in_serialization(self) -> None:
        """Test that circular_references and has_circular_references are in model_dump()."""
        node = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            circular_references=["urllib3"],
        )
        dumped = node.model_dump()

        assert "circular_references" in dumped
        assert dumped["circular_references"] == ["urllib3"]
        assert "has_circular_references" in dumped
        assert dumped["has_circular_references"] is True


class TestDependencyTree:
    """Tests for DependencyTree model."""

    def test_create_empty_tree(self) -> None:
        """Test creating an empty tree."""
        tree = DependencyTree()
        assert tree.roots == []
        assert tree.total_count == 0
        assert tree.max_depth == 0

    def test_create_tree_with_roots(self) -> None:
        """Test creating a tree with root nodes."""
        root1 = DependencyNode(name="requests", version="2.31.0", depth=0)
        root2 = DependencyNode(name="click", version="8.1.0", depth=0)
        tree = DependencyTree(roots=[root1, root2])

        assert len(tree.roots) == 2
        assert tree.total_count == 2

    def test_get_all_nodes_flattens_tree(self) -> None:
        """Test get_all_nodes returns all nodes in tree."""
        grandchild = DependencyNode(name="idna", version="3.4", depth=2)
        child = DependencyNode(
            name="urllib3",
            version="2.0.0",
            depth=1,
            children=[grandchild],
        )
        root = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            children=[child],
        )
        tree = DependencyTree(roots=[root])

        all_nodes = tree.get_all_nodes()
        assert len(all_nodes) == 3
        names = [n.name for n in all_nodes]
        assert "requests" in names
        assert "urllib3" in names
        assert "idna" in names

    def test_get_nodes_at_depth(self) -> None:
        """Test filtering nodes by depth."""
        child1 = DependencyNode(name="certifi", version="2023.7.22", depth=1)
        child2 = DependencyNode(name="urllib3", version="2.0.0", depth=1)
        root = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            children=[child1, child2],
        )
        tree = DependencyTree(roots=[root])

        depth_0 = tree.get_nodes_at_depth(0)
        assert len(depth_0) == 1
        assert depth_0[0].name == "requests"

        depth_1 = tree.get_nodes_at_depth(1)
        assert len(depth_1) == 2
        names = [n.name for n in depth_1]
        assert "certifi" in names
        assert "urllib3" in names

        depth_2 = tree.get_nodes_at_depth(2)
        assert len(depth_2) == 0

    def test_total_count_property(self) -> None:
        """Test total_count computed property."""
        child = DependencyNode(name="urllib3", version="2.0.0", depth=1)
        root = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            children=[child],
        )
        tree = DependencyTree(roots=[root])

        assert tree.total_count == 2

    def test_max_depth_property(self) -> None:
        """Test max_depth computed property."""
        grandchild = DependencyNode(name="idna", version="3.4", depth=2)
        child = DependencyNode(
            name="urllib3",
            version="2.0.0",
            depth=1,
            children=[grandchild],
        )
        root = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            children=[child],
        )
        tree = DependencyTree(roots=[root])

        assert tree.max_depth == 2

    def test_max_depth_empty_tree(self) -> None:
        """Test max_depth with empty tree."""
        tree = DependencyTree()
        assert tree.max_depth == 0

    def test_model_forbids_extra_fields(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            DependencyTree(
                roots=[],
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_multiple_roots_with_shared_names(self) -> None:
        """Test tree with multiple root packages."""
        root1 = DependencyNode(name="requests", version="2.31.0", depth=0)
        root2 = DependencyNode(name="httpx", version="0.24.0", depth=0)
        tree = DependencyTree(roots=[root1, root2])

        all_nodes = tree.get_all_nodes()
        assert len(all_nodes) == 2
        assert tree.total_count == 2

    def test_model_serialization_includes_computed_fields(self) -> None:
        """Test that computed fields are included in model_dump()."""
        root = DependencyNode(name="requests", version="2.31.0", depth=0)
        tree = DependencyTree(roots=[root])
        dumped = tree.model_dump()

        assert "total_count" in dumped
        assert dumped["total_count"] == 1
        assert "max_depth" in dumped
        assert dumped["max_depth"] == 0

    def test_circular_references_default_empty(self) -> None:
        """Test that circular_references defaults to empty list."""
        tree = DependencyTree()
        assert tree.circular_references == []

    def test_circular_references_can_be_set(self) -> None:
        """Test that circular_references can be populated."""
        circ_ref = CircularReference(
            from_package="B",
            to_package="A",
            path=["A", "B", "A"],
        )
        tree = DependencyTree(circular_references=[circ_ref])
        assert len(tree.circular_references) == 1
        assert tree.circular_references[0].from_package == "B"

    def test_has_circular_dependencies_false_when_empty(self) -> None:
        """Test has_circular_dependencies is False when no circular refs."""
        tree = DependencyTree()
        assert tree.has_circular_dependencies is False

    def test_has_circular_dependencies_true_when_populated(self) -> None:
        """Test has_circular_dependencies is True when circular refs exist."""
        circ_ref = CircularReference(
            from_package="B",
            to_package="A",
            path=["A", "B", "A"],
        )
        tree = DependencyTree(circular_references=[circ_ref])
        assert tree.has_circular_dependencies is True

    def test_get_paths_to_package_single_path(self) -> None:
        """Test get_paths_to_package with single path."""
        child = DependencyNode(name="urllib3", version="2.0.0", depth=1)
        root = DependencyNode(
            name="requests",
            version="2.31.0",
            depth=0,
            children=[child],
        )
        tree = DependencyTree(roots=[root])

        paths = tree.get_paths_to_package("urllib3")
        assert len(paths) == 1
        assert len(paths[0]) == 2
        assert paths[0][0].name == "requests"
        assert paths[0][1].name == "urllib3"

    def test_get_paths_to_package_multiple_paths_diamond(self) -> None:
        """Test get_paths_to_package with diamond pattern."""
        # A → B → D
        # A → C → D
        d_via_b = DependencyNode(name="D", version="1.0.0", depth=2)
        d_via_c = DependencyNode(name="D", version="1.0.0", depth=2)
        b = DependencyNode(name="B", version="1.0.0", depth=1, children=[d_via_b])
        c = DependencyNode(name="C", version="1.0.0", depth=1, children=[d_via_c])
        a = DependencyNode(name="A", version="1.0.0", depth=0, children=[b, c])
        tree = DependencyTree(roots=[a])

        paths = tree.get_paths_to_package("D")
        assert len(paths) == 2

        # First path: A → B → D
        assert paths[0][0].name == "A"
        assert paths[0][1].name == "B"
        assert paths[0][2].name == "D"

        # Second path: A → C → D
        assert paths[1][0].name == "A"
        assert paths[1][1].name == "C"
        assert paths[1][2].name == "D"

    def test_get_paths_to_package_case_insensitive(self) -> None:
        """Test get_paths_to_package is case-insensitive."""
        child = DependencyNode(name="Flask-RESTful", version="0.3.9", depth=1)
        root = DependencyNode(
            name="myapp",
            version="1.0.0",
            depth=0,
            children=[child],
        )
        tree = DependencyTree(roots=[root])

        # Should find with different cases and separators
        paths = tree.get_paths_to_package("flask-restful")
        assert len(paths) == 1
        assert paths[0][1].name == "Flask-RESTful"

        paths2 = tree.get_paths_to_package("FLASK_RESTFUL")
        assert len(paths2) == 1

    def test_get_paths_to_package_not_found(self) -> None:
        """Test get_paths_to_package returns empty list when not found."""
        root = DependencyNode(name="requests", version="2.31.0", depth=0)
        tree = DependencyTree(roots=[root])

        paths = tree.get_paths_to_package("nonexistent")
        assert paths == []

    def test_get_paths_to_package_root_node(self) -> None:
        """Test get_paths_to_package finds root node."""
        root = DependencyNode(name="requests", version="2.31.0", depth=0)
        tree = DependencyTree(roots=[root])

        paths = tree.get_paths_to_package("requests")
        assert len(paths) == 1
        assert len(paths[0]) == 1
        assert paths[0][0].name == "requests"

    def test_format_path_with_versions_single_node(self) -> None:
        """Test format_path_with_versions with single node."""
        root = DependencyNode(name="requests", version="2.31.0", depth=0)
        path = [root]

        result = DependencyTree.format_path_with_versions(path)
        assert result == "requests@2.31.0"

    def test_format_path_with_versions_chain(self) -> None:
        """Test format_path_with_versions with full chain."""
        root = DependencyNode(name="requests", version="2.31.0", depth=0)
        child = DependencyNode(name="urllib3", version="2.0.0", depth=1)
        grandchild = DependencyNode(name="idna", version="3.4", depth=2)
        path = [root, child, grandchild]

        result = DependencyTree.format_path_with_versions(path)
        assert result == "requests@2.31.0 → urllib3@2.0.0 → idna@3.4"

    def test_format_path_with_versions_empty(self) -> None:
        """Test format_path_with_versions with empty path."""
        result = DependencyTree.format_path_with_versions([])
        assert result == ""

    def test_format_path_with_versions_integration(self) -> None:
        """Test format_path_with_versions with get_paths_to_package."""
        grandchild = DependencyNode(name="idna", version="3.4", depth=2)
        child = DependencyNode(
            name="urllib3", version="2.0.0", depth=1, children=[grandchild]
        )
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, children=[child]
        )
        tree = DependencyTree(roots=[root])

        paths = tree.get_paths_to_package("idna")
        assert len(paths) == 1
        formatted = DependencyTree.format_path_with_versions(paths[0])
        assert formatted == "requests@2.31.0 → urllib3@2.0.0 → idna@3.4"


class TestDependencyNodeOriginPath:
    """Tests for origin path tracking (FR9)."""

    def test_origin_path_default_empty(self) -> None:
        """Test that origin_path defaults to empty list."""
        node = DependencyNode(name="requests", version="2.31.0", depth=0)
        assert node.origin_path == []

    def test_origin_path_single_parent(self) -> None:
        """Test origin_path with one parent."""
        node = DependencyNode(
            name="urllib3",
            version="2.0.0",
            depth=1,
            origin_path=["requests"],
        )
        assert node.origin_path == ["requests"]

    def test_origin_path_chain(self) -> None:
        """Test origin_path with chain of parents."""
        node = DependencyNode(
            name="idna",
            version="3.4",
            depth=2,
            origin_path=["requests", "urllib3"],
        )
        assert node.origin_path == ["requests", "urllib3"]

    def test_origin_path_included_in_serialization(self) -> None:
        """Test that origin_path is included in model_dump()."""
        node = DependencyNode(
            name="urllib3",
            version="2.0.0",
            depth=1,
            origin_path=["requests"],
        )
        dumped = node.model_dump()
        assert "origin_path" in dumped
        assert dumped["origin_path"] == ["requests"]

    def test_get_origin_path_display_root(self) -> None:
        """Test display format for root node."""
        node = DependencyNode(name="requests", version="2.31.0", depth=0)
        assert node.get_origin_path_display() == "requests"

    def test_get_origin_path_display_depth_one(self) -> None:
        """Test display format for depth-1 node."""
        node = DependencyNode(
            name="urllib3",
            version="2.0.0",
            depth=1,
            origin_path=["requests"],
        )
        assert node.get_origin_path_display() == "requests → urllib3"

    def test_get_origin_path_display_deep_chain(self) -> None:
        """Test display format for deep chain."""
        node = DependencyNode(
            name="idna",
            version="3.4",
            depth=2,
            origin_path=["requests", "urllib3"],
        )
        assert node.get_origin_path_display() == "requests → urllib3 → idna"


class TestDependencyTreeInfectionPaths:
    """Tests for infection path tracking (FR10)."""

    def test_get_nodes_with_problematic_licenses_single(self) -> None:
        """Test finding a single node with problematic license."""
        gpl_node = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=2, license="GPL-3.0"
        )
        mit_child = DependencyNode(
            name="mit-pkg",
            version="1.0.0",
            depth=1,
            license="MIT",
            children=[gpl_node],
        )
        root = DependencyNode(
            name="myapp",
            version="1.0.0",
            depth=0,
            license="MIT",
            children=[mit_child],
        )
        tree = DependencyTree(roots=[root])

        problematic = tree.get_nodes_with_problematic_licenses()
        assert len(problematic) == 1
        assert problematic[0].name == "gpl-pkg"

    def test_get_nodes_with_problematic_licenses_multiple(self) -> None:
        """Test finding multiple nodes with problematic licenses."""
        gpl_node = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=1, license="GPL-3.0"
        )
        agpl_node = DependencyNode(
            name="agpl-pkg", version="1.0.0", depth=1, license="AGPL-3.0"
        )
        root = DependencyNode(
            name="myapp",
            version="1.0.0",
            depth=0,
            license="MIT",
            children=[gpl_node, agpl_node],
        )
        tree = DependencyTree(roots=[root])

        problematic = tree.get_nodes_with_problematic_licenses()
        assert len(problematic) == 2
        names = [n.name for n in problematic]
        assert "gpl-pkg" in names
        assert "agpl-pkg" in names

    def test_get_nodes_with_problematic_licenses_none(self) -> None:
        """Test no problematic licenses found."""
        mit_node = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=1, license="MIT"
        )
        root = DependencyNode(
            name="myapp",
            version="1.0.0",
            depth=0,
            license="Apache-2.0",
            children=[mit_node],
        )
        tree = DependencyTree(roots=[root])

        problematic = tree.get_nodes_with_problematic_licenses()
        assert len(problematic) == 0

    def test_get_infection_paths_single_path(self) -> None:
        """Test getting infection path for single route."""
        gpl_node = DependencyNode(
            name="gpl-pkg",
            version="1.0.0",
            depth=2,
            license="GPL-3.0",
            origin_path=["myapp", "mit-pkg"],
        )
        mit_child = DependencyNode(
            name="mit-pkg",
            version="1.0.0",
            depth=1,
            license="MIT",
            children=[gpl_node],
            origin_path=["myapp"],
        )
        root = DependencyNode(
            name="myapp",
            version="1.0.0",
            depth=0,
            license="MIT",
            children=[mit_child],
        )
        tree = DependencyTree(roots=[root])

        infection_paths = tree.get_infection_paths()
        assert "gpl-pkg" in infection_paths
        assert len(infection_paths["gpl-pkg"]) == 1
        # Path should be: myapp -> mit-pkg -> gpl-pkg
        path = infection_paths["gpl-pkg"][0]
        assert len(path) == 3
        assert path[0].name == "myapp"
        assert path[1].name == "mit-pkg"
        assert path[2].name == "gpl-pkg"

    def test_get_infection_paths_multiple_paths(self) -> None:
        """Test getting infection paths when multiple routes exist (AC #2)."""
        # Diamond pattern: myapp -> A -> gpl-pkg, myapp -> B -> gpl-pkg
        gpl_via_a = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=2, license="GPL-3.0"
        )
        gpl_via_b = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=2, license="GPL-3.0"
        )
        pkg_a = DependencyNode(
            name="pkg-a",
            version="1.0.0",
            depth=1,
            license="MIT",
            children=[gpl_via_a],
        )
        pkg_b = DependencyNode(
            name="pkg-b",
            version="1.0.0",
            depth=1,
            license="MIT",
            children=[gpl_via_b],
        )
        root = DependencyNode(
            name="myapp",
            version="1.0.0",
            depth=0,
            license="MIT",
            children=[pkg_a, pkg_b],
        )
        tree = DependencyTree(roots=[root])

        infection_paths = tree.get_infection_paths()
        assert "gpl-pkg" in infection_paths
        # Should have 2 paths to gpl-pkg
        assert len(infection_paths["gpl-pkg"]) == 2

    def test_get_introducing_dependency_transitive(self) -> None:
        """Test finding which direct dep introduced problematic license."""
        gpl_node = DependencyNode(
            name="gpl-pkg",
            version="1.0.0",
            depth=2,
            license="GPL-3.0",
            origin_path=["requests", "urllib3"],
        )
        requests_root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        tree = DependencyTree(roots=[requests_root])

        introducing = tree.get_introducing_dependency(gpl_node)
        assert introducing is not None
        assert introducing.name == "requests"

    def test_get_introducing_dependency_direct(self) -> None:
        """Test that direct dependency returns None (it IS the introducer)."""
        gpl_root = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        tree = DependencyTree(roots=[gpl_root])

        introducing = tree.get_introducing_dependency(gpl_root)
        assert introducing is None

    def test_get_introducing_dependency_no_origin_path(self) -> None:
        """Test node without origin_path returns None."""
        gpl_node = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=1, license="GPL-3.0"
        )
        tree = DependencyTree(roots=[])

        introducing = tree.get_introducing_dependency(gpl_node)
        assert introducing is None

    def test_format_infection_path(self) -> None:
        """Test infection path formatting with license info."""
        root = DependencyNode(
            name="myapp", version="1.0.0", depth=0, license="MIT"
        )
        child = DependencyNode(
            name="middleware", version="2.0.0", depth=1, license="Apache-2.0"
        )
        gpl_node = DependencyNode(
            name="gpl-pkg", version="3.0.0", depth=2, license="GPL-3.0"
        )
        path = [root, child, gpl_node]

        formatted = DependencyTree.format_infection_path(path)
        assert "myapp@1.0.0 (MIT)" in formatted
        assert "middleware@2.0.0 (Apache-2.0)" in formatted
        assert "gpl-pkg@3.0.0 (GPL-3.0)" in formatted
        assert "⚠️" in formatted  # Warning marker on problematic

    def test_format_infection_path_empty(self) -> None:
        """Test formatting empty path."""
        formatted = DependencyTree.format_infection_path([])
        assert formatted == ""

    def test_format_infection_path_with_none_license(self) -> None:
        """Test formatting path when node has None license."""
        root = DependencyNode(
            name="myapp", version="1.0.0", depth=0, license=None
        )
        child = DependencyNode(
            name="unknown-pkg", version="2.0.0", depth=1, license=None
        )
        path = [root, child]

        formatted = DependencyTree.format_infection_path(path)
        assert "myapp@1.0.0 (Unknown)" in formatted
        assert "unknown-pkg@2.0.0 (Unknown)" in formatted
        # No warning marker since Unknown is not problematic
        assert "⚠️" not in formatted


class TestCompatibilityStatus:
    """Tests for CompatibilityStatus enum."""

    def test_compatible_value(self) -> None:
        """Test COMPATIBLE enum value."""
        assert CompatibilityStatus.COMPATIBLE.value == "compatible"

    def test_incompatible_value(self) -> None:
        """Test INCOMPATIBLE enum value."""
        assert CompatibilityStatus.INCOMPATIBLE.value == "incompatible"

    def test_unknown_value(self) -> None:
        """Test UNKNOWN enum value."""
        assert CompatibilityStatus.UNKNOWN.value == "unknown"


class TestCompatibilityResult:
    """Tests for CompatibilityResult model."""

    def test_create_compatible_result(self) -> None:
        """Test creating a compatible result."""
        result = CompatibilityResult(
            license_a="MIT",
            license_b="Apache-2.0",
            status=CompatibilityStatus.COMPATIBLE,
            reason="Both licenses are permissive",
        )
        assert result.license_a == "MIT"
        assert result.license_b == "Apache-2.0"
        assert result.status == CompatibilityStatus.COMPATIBLE
        assert result.reason == "Both licenses are permissive"
        assert result.compatible is True

    def test_create_incompatible_result(self) -> None:
        """Test creating an incompatible result."""
        result = CompatibilityResult(
            license_a="GPL-2.0",
            license_b="Apache-2.0",
            status=CompatibilityStatus.INCOMPATIBLE,
            reason="GPL-2.0 has patent clause conflict with Apache-2.0",
        )
        assert result.status == CompatibilityStatus.INCOMPATIBLE
        assert result.compatible is False

    def test_create_unknown_result(self) -> None:
        """Test creating an unknown result."""
        result = CompatibilityResult(
            license_a="MIT",
            license_b="Custom-License",
            status=CompatibilityStatus.UNKNOWN,
            reason="Custom-License is not a recognized SPDX identifier",
        )
        assert result.status == CompatibilityStatus.UNKNOWN
        assert result.compatible is False

    def test_model_forbids_extra_fields(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            CompatibilityResult(
                license_a="MIT",
                license_b="Apache-2.0",
                status=CompatibilityStatus.COMPATIBLE,
                reason="Both permissive",
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_model_serialization(self) -> None:
        """Test CompatibilityResult serialization."""
        result = CompatibilityResult(
            license_a="MIT",
            license_b="GPL-3.0",
            status=CompatibilityStatus.COMPATIBLE,
            reason="MIT can be used in GPL projects",
        )
        dumped = result.model_dump()
        assert dumped["license_a"] == "MIT"
        assert dumped["license_b"] == "GPL-3.0"
        assert dumped["status"] == CompatibilityStatus.COMPATIBLE
        assert dumped["reason"] == "MIT can be used in GPL projects"
        assert dumped["compatible"] is True


class TestCircularReference:
    """Tests for CircularReference model."""

    def test_create_circular_reference(self) -> None:
        """Test creating a CircularReference."""
        circ = CircularReference(
            from_package="B",
            to_package="A",
            path=["A", "B", "A"],
        )
        assert circ.from_package == "B"
        assert circ.to_package == "A"
        assert circ.path == ["A", "B", "A"]

    def test_path_defaults_to_empty(self) -> None:
        """Test that path defaults to empty list."""
        circ = CircularReference(from_package="B", to_package="A")
        assert circ.path == []

    def test_model_forbids_extra_fields(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            CircularReference(
                from_package="B",
                to_package="A",
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_model_serialization(self) -> None:
        """Test CircularReference serialization."""
        circ = CircularReference(
            from_package="B",
            to_package="A",
            path=["A", "B", "A"],
        )
        dumped = circ.model_dump()
        assert dumped == {
            "from_package": "B",
            "to_package": "A",
            "path": ["A", "B", "A"],
        }


class TestCategoryStatistics:
    """Tests for CategoryStatistics model."""

    def test_create_category_statistics(self) -> None:
        """Test creating CategoryStatistics."""
        stats = CategoryStatistics(
            category="Permissive",
            count=5,
            percentage=50.0,
            licenses=["MIT", "Apache-2.0"],
        )
        assert stats.category == "Permissive"
        assert stats.count == 5
        assert stats.percentage == 50.0
        assert stats.licenses == ["MIT", "Apache-2.0"]

    def test_licenses_defaults_to_empty(self) -> None:
        """Test licenses defaults to empty list."""
        stats = CategoryStatistics(
            category="Unknown",
            count=0,
            percentage=0.0,
        )
        assert stats.licenses == []

    def test_model_forbids_extra_fields(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            CategoryStatistics(
                category="Permissive",
                count=1,
                percentage=100.0,
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_count_cannot_be_negative(self) -> None:
        """Test that count must be >= 0."""
        with pytest.raises(ValidationError):
            CategoryStatistics(
                category="Permissive",
                count=-1,
                percentage=0.0,
            )

    def test_percentage_must_be_in_range(self) -> None:
        """Test that percentage must be between 0 and 100."""
        # Test below 0
        with pytest.raises(ValidationError):
            CategoryStatistics(
                category="Permissive",
                count=1,
                percentage=-5.0,
            )

        # Test above 100
        with pytest.raises(ValidationError):
            CategoryStatistics(
                category="Permissive",
                count=1,
                percentage=150.0,
            )


class TestLicenseStatistics:
    """Tests for LicenseStatistics model."""

    def test_create_license_statistics(self) -> None:
        """Test creating LicenseStatistics."""
        permissive = CategoryStatistics(
            category="Permissive", count=3, percentage=60.0, licenses=["MIT"]
        )
        copyleft = CategoryStatistics(
            category="Copyleft", count=1, percentage=20.0, licenses=["GPL-3.0"]
        )
        weak = CategoryStatistics(
            category="Weak Copyleft", count=0, percentage=0.0, licenses=[]
        )
        unknown = CategoryStatistics(
            category="Unknown", count=1, percentage=20.0, licenses=["Unknown"]
        )

        stats = LicenseStatistics(
            total_packages=5,
            permissive=permissive,
            copyleft=copyleft,
            weak_copyleft=weak,
            unknown=unknown,
        )

        assert stats.total_packages == 5
        assert stats.permissive.count == 3
        assert stats.copyleft.count == 1

    def test_to_dict(self) -> None:
        """Test to_dict returns all categories."""
        permissive = CategoryStatistics(
            category="Permissive", count=1, percentage=100.0, licenses=["MIT"]
        )
        copyleft = CategoryStatistics(
            category="Copyleft", count=0, percentage=0.0, licenses=[]
        )
        weak = CategoryStatistics(
            category="Weak Copyleft", count=0, percentage=0.0, licenses=[]
        )
        unknown = CategoryStatistics(
            category="Unknown", count=0, percentage=0.0, licenses=[]
        )

        stats = LicenseStatistics(
            total_packages=1,
            permissive=permissive,
            copyleft=copyleft,
            weak_copyleft=weak,
            unknown=unknown,
        )

        result = stats.to_dict()
        assert "permissive" in result
        assert "copyleft" in result
        assert "weak_copyleft" in result
        assert "unknown" in result

    def test_model_forbids_extra_fields(self) -> None:
        """Test that extra fields are forbidden."""
        permissive = CategoryStatistics(
            category="Permissive", count=1, percentage=100.0, licenses=["MIT"]
        )
        copyleft = CategoryStatistics(
            category="Copyleft", count=0, percentage=0.0, licenses=[]
        )
        weak = CategoryStatistics(
            category="Weak Copyleft", count=0, percentage=0.0, licenses=[]
        )
        unknown = CategoryStatistics(
            category="Unknown", count=0, percentage=0.0, licenses=[]
        )

        with pytest.raises(ValidationError):
            LicenseStatistics(
                total_packages=1,
                permissive=permissive,
                copyleft=copyleft,
                weak_copyleft=weak,
                unknown=unknown,
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_total_packages_cannot_be_negative(self) -> None:
        """Test that total_packages must be >= 0."""
        permissive = CategoryStatistics(
            category="Permissive", count=0, percentage=0.0, licenses=[]
        )
        copyleft = CategoryStatistics(
            category="Copyleft", count=0, percentage=0.0, licenses=[]
        )
        weak = CategoryStatistics(
            category="Weak Copyleft", count=0, percentage=0.0, licenses=[]
        )
        unknown = CategoryStatistics(
            category="Unknown", count=0, percentage=0.0, licenses=[]
        )

        with pytest.raises(ValidationError):
            LicenseStatistics(
                total_packages=-1,
                permissive=permissive,
                copyleft=copyleft,
                weak_copyleft=weak,
                unknown=unknown,
            )


class TestDependencyTreeLicenseStatistics:
    """Tests for DependencyTree.get_license_statistics()."""

    def test_empty_tree_statistics(self) -> None:
        """Test statistics for empty tree."""
        tree = DependencyTree(roots=[])
        stats = tree.get_license_statistics()

        assert stats.total_packages == 0
        assert stats.permissive.count == 0
        assert stats.copyleft.count == 0
        assert stats.weak_copyleft.count == 0
        assert stats.unknown.count == 0

    def test_all_permissive_licenses(self) -> None:
        """Test statistics when all licenses are permissive."""
        root1 = DependencyNode(
            name="pkg-a", version="1.0.0", depth=0, license="MIT"
        )
        root2 = DependencyNode(
            name="pkg-b", version="1.0.0", depth=0, license="Apache-2.0"
        )
        tree = DependencyTree(roots=[root1, root2])

        stats = tree.get_license_statistics()

        assert stats.total_packages == 2
        assert stats.permissive.count == 2
        assert stats.permissive.percentage == 100.0
        assert "MIT" in stats.permissive.licenses
        assert "Apache-2.0" in stats.permissive.licenses

    def test_mixed_licenses(self) -> None:
        """Test statistics with mixed license types."""
        root1 = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=0, license="MIT"
        )
        root2 = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        root3 = DependencyNode(
            name="lgpl-pkg", version="1.0.0", depth=0, license="LGPL-3.0"
        )
        root4 = DependencyNode(
            name="unknown-pkg", version="1.0.0", depth=0, license=None
        )
        tree = DependencyTree(roots=[root1, root2, root3, root4])

        stats = tree.get_license_statistics()

        assert stats.total_packages == 4
        assert stats.permissive.count == 1
        assert stats.permissive.percentage == 25.0
        assert stats.copyleft.count == 1
        assert stats.copyleft.percentage == 25.0
        assert stats.weak_copyleft.count == 1
        assert stats.weak_copyleft.percentage == 25.0
        assert stats.unknown.count == 1
        assert stats.unknown.percentage == 25.0

    def test_nested_tree_statistics(self) -> None:
        """Test statistics include nested children."""
        child = DependencyNode(
            name="child-pkg", version="1.0.0", depth=1, license="Apache-2.0"
        )
        root = DependencyNode(
            name="root-pkg",
            version="1.0.0",
            depth=0,
            license="MIT",
            children=[child],
        )
        tree = DependencyTree(roots=[root])

        stats = tree.get_license_statistics()

        assert stats.total_packages == 2
        assert stats.permissive.count == 2
        assert "MIT" in stats.permissive.licenses
        assert "Apache-2.0" in stats.permissive.licenses

    def test_unknown_license_as_none(self) -> None:
        """Test None license is counted as Unknown."""
        root = DependencyNode(
            name="pkg", version="1.0.0", depth=0, license=None
        )
        tree = DependencyTree(roots=[root])

        stats = tree.get_license_statistics()

        assert stats.unknown.count == 1
        assert "Unknown" in stats.unknown.licenses

    def test_percentage_rounding(self) -> None:
        """Test percentage is rounded to 1 decimal place."""
        # 3 packages: 1 MIT, 1 GPL, 1 Unknown = 33.3% each
        root1 = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=0, license="MIT"
        )
        root2 = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        root3 = DependencyNode(
            name="unknown-pkg", version="1.0.0", depth=0, license=None
        )
        tree = DependencyTree(roots=[root1, root2, root3])

        stats = tree.get_license_statistics()

        assert stats.permissive.percentage == 33.3
        assert stats.copyleft.percentage == 33.3
        assert stats.unknown.percentage == 33.3


class TestDependencyTreeCompatibilityIssues:
    """Tests for DependencyTree.get_compatibility_issues()."""

    def test_empty_tree_no_issues(self) -> None:
        """Test empty tree returns no compatibility issues."""
        tree = DependencyTree(roots=[])
        issues = tree.get_compatibility_issues()
        assert len(issues) == 0

    def test_all_permissive_no_issues(self) -> None:
        """Test all permissive licenses returns no issues."""
        root1 = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=0, license="MIT"
        )
        root2 = DependencyNode(
            name="apache-pkg", version="1.0.0", depth=0, license="Apache-2.0"
        )
        root3 = DependencyNode(
            name="bsd-pkg", version="1.0.0", depth=0, license="BSD-3-Clause"
        )
        tree = DependencyTree(roots=[root1, root2, root3])

        issues = tree.get_compatibility_issues()
        assert len(issues) == 0

    def test_gpl2_gpl3_incompatible(self) -> None:
        """Test GPL-2.0 + GPL-3.0 returns incompatible issue."""
        root1 = DependencyNode(
            name="gpl2-pkg", version="1.0.0", depth=0, license="GPL-2.0"
        )
        root2 = DependencyNode(
            name="gpl3-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        tree = DependencyTree(roots=[root1, root2])

        issues = tree.get_compatibility_issues()
        assert len(issues) == 1
        assert issues[0].status == CompatibilityStatus.INCOMPATIBLE

    def test_mixed_with_permissive_and_gpl_versions(self) -> None:
        """Test mixed licenses returns only incompatible pairs."""
        # MIT + Apache = compatible
        # GPL-2.0 + GPL-3.0 = incompatible
        # MIT + GPL-2.0 = compatible (MIT can be in GPL)
        # MIT + GPL-3.0 = compatible (MIT can be in GPL)
        # Apache + GPL-2.0 = compatible
        # Apache + GPL-3.0 = compatible
        root1 = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=0, license="MIT"
        )
        root2 = DependencyNode(
            name="gpl2-pkg", version="1.0.0", depth=0, license="GPL-2.0"
        )
        root3 = DependencyNode(
            name="gpl3-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        tree = DependencyTree(roots=[root1, root2, root3])

        issues = tree.get_compatibility_issues()
        # Only GPL-2.0 + GPL-3.0 should be incompatible
        assert len(issues) == 1
        assert issues[0].status == CompatibilityStatus.INCOMPATIBLE

    def test_nested_tree_collects_all_licenses(self) -> None:
        """Test nested tree collects licenses from all depths."""
        child = DependencyNode(
            name="gpl3-child", version="1.0.0", depth=1, license="GPL-3.0"
        )
        root = DependencyNode(
            name="gpl2-root", version="1.0.0", depth=0, license="GPL-2.0",
            children=[child]
        )
        tree = DependencyTree(roots=[root])

        issues = tree.get_compatibility_issues()
        assert len(issues) == 1
        assert issues[0].status == CompatibilityStatus.INCOMPATIBLE

    def test_unknown_license_reported(self) -> None:
        """Test unknown license is reported as unknown compatibility."""
        root1 = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=0, license="MIT"
        )
        root2 = DependencyNode(
            name="custom-pkg", version="1.0.0", depth=0, license="Custom-License"
        )
        tree = DependencyTree(roots=[root1, root2])

        issues = tree.get_compatibility_issues()
        assert len(issues) == 1
        assert issues[0].status == CompatibilityStatus.UNKNOWN

    def test_none_licenses_skipped(self) -> None:
        """Test None licenses are filtered out before checking."""
        root1 = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=0, license="MIT"
        )
        root2 = DependencyNode(
            name="no-license-pkg", version="1.0.0", depth=0, license=None
        )
        tree = DependencyTree(roots=[root1, root2])

        issues = tree.get_compatibility_issues()
        # None is filtered out, only MIT remains - no pairs to check
        assert len(issues) == 0


class TestCompatibilityMatrix:
    """Tests for CompatibilityMatrix model."""

    def test_create_empty_matrix(self) -> None:
        """Test creating an empty matrix."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        matrix = CompatibilityMatrix(licenses=[], matrix=[], issues=[])

        assert matrix.licenses == []
        assert matrix.matrix == []
        assert matrix.size == 0
        assert matrix.has_issues is False

    def test_create_matrix_with_licenses(self) -> None:
        """Test creating a matrix with licenses."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        matrix = CompatibilityMatrix(
            licenses=["MIT", "Apache-2.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )

        assert matrix.licenses == ["MIT", "Apache-2.0"]
        assert matrix.size == 2
        assert matrix.has_issues is False

    def test_size_computed_property(self) -> None:
        """Test size returns correct count."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        matrix = CompatibilityMatrix(
            licenses=["MIT", "Apache-2.0", "BSD-3-Clause"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE] * 3,
                [CompatibilityStatus.COMPATIBLE] * 3,
                [CompatibilityStatus.COMPATIBLE] * 3,
            ],
            issues=[],
        )

        assert matrix.size == 3

    def test_has_issues_true_when_issues_exist(self) -> None:
        """Test has_issues is True when issues are present."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        matrix = CompatibilityMatrix(
            licenses=["MIT", "GPL-3.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.INCOMPATIBLE],
                [CompatibilityStatus.INCOMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[
                CompatibilityResult(
                    license_a="MIT",
                    license_b="GPL-3.0",
                    status=CompatibilityStatus.INCOMPATIBLE,
                    reason="Copyleft restriction",
                )
            ],
        )

        assert matrix.has_issues is True

    def test_get_status_returns_correct_status(self) -> None:
        """Test get_status returns correct status for license pair."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        matrix = CompatibilityMatrix(
            licenses=["MIT", "GPL-3.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.INCOMPATIBLE],
                [CompatibilityStatus.INCOMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )

        assert matrix.get_status("MIT", "MIT") == CompatibilityStatus.COMPATIBLE
        assert matrix.get_status("MIT", "GPL-3.0") == CompatibilityStatus.INCOMPATIBLE
        assert matrix.get_status("GPL-3.0", "MIT") == CompatibilityStatus.INCOMPATIBLE
        assert matrix.get_status("GPL-3.0", "GPL-3.0") == CompatibilityStatus.COMPATIBLE

    def test_get_status_raises_for_unknown_license(self) -> None:
        """Test get_status raises ValueError for unknown license."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )

        with pytest.raises(ValueError, match="License not in matrix"):
            matrix.get_status("MIT", "Unknown")

        with pytest.raises(ValueError, match="License not in matrix"):
            matrix.get_status("Unknown", "MIT")

    def test_model_forbids_extra_fields(self) -> None:
        """Test model rejects extra fields."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        with pytest.raises(ValidationError):
            CompatibilityMatrix(
                licenses=[],
                matrix=[],
                issues=[],
                extra_field="not allowed",
            )


class TestCompatibilityMatrixFromDependencyTree:
    """Tests for CompatibilityMatrix.from_dependency_tree factory method."""

    def test_empty_tree_creates_empty_matrix(self) -> None:
        """Test empty tree creates empty matrix."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        tree = DependencyTree(roots=[])
        matrix = CompatibilityMatrix.from_dependency_tree(tree)

        assert matrix.licenses == []
        assert matrix.matrix == []
        assert matrix.size == 0

    def test_single_license_creates_1x1_matrix(self) -> None:
        """Test single license creates 1x1 matrix."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        root = DependencyNode(name="pkg", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root])

        matrix = CompatibilityMatrix.from_dependency_tree(tree)

        assert matrix.licenses == ["MIT"]
        assert matrix.size == 1
        assert matrix.matrix[0][0] == CompatibilityStatus.COMPATIBLE

    def test_multiple_licenses_creates_nxn_matrix(self) -> None:
        """Test multiple licenses creates NxN matrix."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        root1 = DependencyNode(name="pkg1", version="1.0.0", depth=0, license="MIT")
        root2 = DependencyNode(
            name="pkg2", version="1.0.0", depth=0, license="Apache-2.0"
        )
        root3 = DependencyNode(
            name="pkg3", version="1.0.0", depth=0, license="BSD-3-Clause"
        )
        tree = DependencyTree(roots=[root1, root2, root3])

        matrix = CompatibilityMatrix.from_dependency_tree(tree)

        assert matrix.size == 3
        assert len(matrix.matrix) == 3
        assert all(len(row) == 3 for row in matrix.matrix)

    def test_licenses_are_sorted(self) -> None:
        """Test licenses are sorted alphabetically."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        root1 = DependencyNode(name="pkg1", version="1.0.0", depth=0, license="MIT")
        root2 = DependencyNode(
            name="pkg2", version="1.0.0", depth=0, license="Apache-2.0"
        )
        tree = DependencyTree(roots=[root1, root2])

        matrix = CompatibilityMatrix.from_dependency_tree(tree)

        # Apache-2.0 comes before MIT alphabetically
        assert matrix.licenses == ["Apache-2.0", "MIT"]

    def test_duplicate_licenses_deduplicated(self) -> None:
        """Test duplicate licenses are deduplicated."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        root1 = DependencyNode(name="pkg1", version="1.0.0", depth=0, license="MIT")
        root2 = DependencyNode(name="pkg2", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root1, root2])

        matrix = CompatibilityMatrix.from_dependency_tree(tree)

        assert matrix.licenses == ["MIT"]
        assert matrix.size == 1

    def test_none_licenses_excluded(self) -> None:
        """Test None licenses are excluded from matrix."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        root1 = DependencyNode(name="pkg1", version="1.0.0", depth=0, license="MIT")
        root2 = DependencyNode(name="pkg2", version="1.0.0", depth=0, license=None)
        tree = DependencyTree(roots=[root1, root2])

        matrix = CompatibilityMatrix.from_dependency_tree(tree)

        assert matrix.licenses == ["MIT"]
        assert matrix.size == 1

    def test_issues_deduplicated(self) -> None:
        """Test issues are deduplicated for symmetric pairs."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        # GPL-2.0 and GPL-3.0 are incompatible with each other
        root1 = DependencyNode(name="pkg1", version="1.0.0", depth=0, license="GPL-2.0")
        root2 = DependencyNode(name="pkg2", version="1.0.0", depth=0, license="GPL-3.0")
        tree = DependencyTree(roots=[root1, root2])

        matrix = CompatibilityMatrix.from_dependency_tree(tree)

        # Should only have one issue for GPL-2.0/GPL-3.0 pair, not two
        incompatible_issues = [
            i for i in matrix.issues
            if i.status == CompatibilityStatus.INCOMPATIBLE
        ]
        assert len(incompatible_issues) == 1

    def test_diagonal_always_compatible(self) -> None:
        """Test diagonal (same license) is always compatible."""
        from license_analyzer.models.dependency import CompatibilityMatrix

        root1 = DependencyNode(name="pkg1", version="1.0.0", depth=0, license="MIT")
        root2 = DependencyNode(name="pkg2", version="1.0.0", depth=0, license="GPL-3.0")
        tree = DependencyTree(roots=[root1, root2])

        matrix = CompatibilityMatrix.from_dependency_tree(tree)

        # Diagonal entries should all be compatible
        for i in range(matrix.size):
            assert matrix.matrix[i][i] == CompatibilityStatus.COMPATIBLE
