"""Tests for dependency resolver."""

from typing import Optional
from unittest.mock import patch

from license_analyzer.resolvers.dependency import DependencyResolver

# Performance test constant - AC #2 requires 200+ dependencies
MIN_PACKAGES_FOR_PERF_TEST = 200


class MockDistribution:
    """Mock distribution for testing importlib.metadata.Distribution."""

    def __init__(
        self,
        name: str,
        version: str,
        requires: Optional[list[str]] = None,
    ) -> None:
        """Initialize mock distribution."""
        self._metadata = {"Name": name, "Version": version}
        self._requires = requires

    @property
    def metadata(self) -> dict[str, str]:
        """Return metadata dict (mimics Distribution.metadata)."""
        return self._metadata

    @property
    def requires(self) -> Optional[list[str]]:
        """Return requirements list (mimics Distribution.requires)."""
        return self._requires


def create_mock_distributions(
    packages: dict[str, tuple[str, Optional[list[str]]]],
) -> list[MockDistribution]:
    """Create list of mock distributions.

    Args:
        packages: Dict of package_name -> (version, requirements).

    Returns:
        List of MockDistribution objects.
    """
    return [
        MockDistribution(name, version, requires)
        for name, (version, requires) in packages.items()
    ]


class TestDependencyResolverNormalization:
    """Tests for package name normalization."""

    def test_normalize_lowercase(self) -> None:
        """Test normalization converts to lowercase."""
        assert DependencyResolver._normalize("Flask") == "flask"
        assert DependencyResolver._normalize("REQUESTS") == "requests"

    def test_normalize_replaces_hyphens(self) -> None:
        """Test normalization replaces hyphens with underscores."""
        assert DependencyResolver._normalize("flask-restful") == "flask_restful"
        assert DependencyResolver._normalize("my-cool-package") == "my_cool_package"

    def test_normalize_replaces_dots(self) -> None:
        """Test normalization replaces dots with underscores."""
        assert DependencyResolver._normalize("zope.interface") == "zope_interface"

    def test_normalize_combined(self) -> None:
        """Test normalization handles mixed cases."""
        assert DependencyResolver._normalize("Flask-RESTful") == "flask_restful"
        assert DependencyResolver._normalize("Zope.Interface") == "zope_interface"


class TestDependencyResolverInit:
    """Tests for DependencyResolver initialization."""

    def test_builds_installed_index(self) -> None:
        """Test that resolver builds package index on init."""
        mock_dists = create_mock_distributions(
            {
                "requests": ("2.31.0", None),
                "flask": ("2.0.0", None),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()

            assert "requests" in resolver._installed
            assert "flask" in resolver._installed

    def test_normalizes_package_names_in_index(self) -> None:
        """Test that package names are normalized in index."""
        mock_dists = create_mock_distributions(
            {
                "Flask-RESTful": ("0.3.9", None),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()

            assert "flask_restful" in resolver._installed
            assert "Flask-RESTful" not in resolver._installed


class TestDependencyResolverResolveTree:
    """Tests for resolve_tree method."""

    def test_resolve_single_package_no_deps(self) -> None:
        """Test resolving a single package with no dependencies."""
        mock_dists = create_mock_distributions(
            {
                "requests": ("2.31.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["requests"])

            assert len(tree.roots) == 1
            assert tree.roots[0].name == "requests"
            assert tree.roots[0].version == "2.31.0"
            assert tree.roots[0].depth == 0
            assert tree.roots[0].children == []

    def test_resolve_package_with_direct_deps(self) -> None:
        """Test resolving package with direct dependencies."""
        mock_dists = create_mock_distributions(
            {
                "requests": ("2.31.0", ["certifi>=2017.4.17", "urllib3>=1.21.1"]),
                "certifi": ("2023.7.22", []),
                "urllib3": ("2.0.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["requests"])

            assert len(tree.roots) == 1
            root = tree.roots[0]
            assert root.name == "requests"
            assert root.depth == 0
            assert len(root.children) == 2

            child_names = [c.name for c in root.children]
            assert "certifi" in child_names
            assert "urllib3" in child_names

            for child in root.children:
                assert child.depth == 1

    def test_resolve_transitive_deps(self) -> None:
        """Test resolving transitive dependencies."""
        mock_dists = create_mock_distributions(
            {
                "requests": ("2.31.0", ["urllib3>=1.21.1"]),
                "urllib3": ("2.0.0", ["idna>=2.0.0"]),
                "idna": ("3.4", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["requests"])

            # requests -> urllib3 -> idna
            root = tree.roots[0]
            assert root.name == "requests"
            assert root.depth == 0

            assert len(root.children) == 1
            urllib3 = root.children[0]
            assert urllib3.name == "urllib3"
            assert urllib3.depth == 1

            assert len(urllib3.children) == 1
            idna = urllib3.children[0]
            assert idna.name == "idna"
            assert idna.depth == 2

    def test_resolve_multiple_roots(self) -> None:
        """Test resolving multiple root packages."""
        mock_dists = create_mock_distributions(
            {
                "requests": ("2.31.0", []),
                "click": ("8.1.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["requests", "click"])

            assert len(tree.roots) == 2
            names = [r.name for r in tree.roots]
            assert "requests" in names
            assert "click" in names

    def test_resolve_skips_nonexistent_packages(self) -> None:
        """Test that nonexistent packages are skipped."""
        mock_dists = create_mock_distributions(
            {
                "requests": ("2.31.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["requests", "nonexistent"])

            assert len(tree.roots) == 1
            assert tree.roots[0].name == "requests"

    def test_resolve_handles_diamond_dependency(self) -> None:
        """Test handling of diamond dependency pattern.

        A -> B, C
        B -> D
        C -> D (same package!)
        """
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0", "C>=1.0"]),
                "B": ("1.0.0", ["D>=1.0"]),
                "C": ("1.0.0", ["D>=1.0"]),
                "D": ("1.0.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            # D should only appear once in the tree (visited tracking)
            all_nodes = tree.get_all_nodes()
            d_nodes = [n for n in all_nodes if n.name == "D"]
            assert len(d_nodes) == 1

    def test_resolve_with_max_depth(self) -> None:
        """Test max_depth limits tree traversal."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0"]),
                "B": ("1.0.0", ["C>=1.0"]),
                "C": ("1.0.0", ["D>=1.0"]),
                "D": ("1.0.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()

            # Depth 1: A and B only
            tree = resolver.resolve_tree(["A"], max_depth=1)
            all_nodes = tree.get_all_nodes()
            names = [n.name for n in all_nodes]
            assert "A" in names
            assert "B" in names
            assert "C" not in names
            assert "D" not in names

    def test_resolve_max_depth_zero_returns_root_only(self) -> None:
        """Test max_depth=0 returns only root packages."""
        mock_dists = create_mock_distributions(
            {
                "requests": ("2.31.0", ["certifi>=2017.4.17"]),
                "certifi": ("2023.7.22", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["requests"], max_depth=0)

            assert len(tree.roots) == 1
            assert tree.roots[0].name == "requests"
            assert tree.roots[0].children == []


class TestDependencyResolverMarkerHandling:
    """Tests for environment marker handling."""

    def test_skips_requirements_with_failing_markers(self) -> None:
        """Test that requirements with non-matching markers are skipped."""
        mock_dists = create_mock_distributions(
            {
                "requests": (
                    "2.31.0",
                    [
                        "certifi>=2017.4.17",
                        'win32api; sys_platform == "win32"',  # Will be skipped on non-Windows
                    ],
                ),
                "certifi": ("2023.7.22", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["requests"])

            child_names = [c.name for c in tree.roots[0].children]
            assert "certifi" in child_names
            # win32api should not be included (marker doesn't match)

    def test_skips_extras_only_requirements(self) -> None:
        """Test that extras-only requirements are skipped."""
        mock_dists = create_mock_distributions(
            {
                "requests": (
                    "2.31.0",
                    [
                        "certifi>=2017.4.17",
                        'pytest; extra == "test"',  # Extras-only, should be skipped
                    ],
                ),
                "certifi": ("2023.7.22", []),
                "pytest": ("7.0.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["requests"])

            child_names = [c.name for c in tree.roots[0].children]
            assert "certifi" in child_names
            assert "pytest" not in child_names


class TestDependencyResolverGetInstalledPackages:
    """Tests for get_installed_packages method."""

    def test_returns_sorted_package_names(self) -> None:
        """Test that installed packages are returned sorted."""
        mock_dists = create_mock_distributions(
            {
                "zebra": ("1.0.0", None),
                "apple": ("1.0.0", None),
                "mango": ("1.0.0", None),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            packages = resolver.get_installed_packages()

            assert packages == ["apple", "mango", "zebra"]


class TestDependencyResolverEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_malformed_requirement(self) -> None:
        """Test that malformed requirements are skipped gracefully."""
        mock_dists = create_mock_distributions(
            {
                "requests": (
                    "2.31.0",
                    [
                        "certifi>=2017.4.17",
                        "malformed[[[requirement",  # Invalid syntax
                    ],
                ),
                "certifi": ("2023.7.22", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            # Should not raise, should skip malformed requirement
            tree = resolver.resolve_tree(["requests"])

            assert len(tree.roots) == 1
            child_names = [c.name for c in tree.roots[0].children]
            assert "certifi" in child_names

    def test_handles_none_requires(self) -> None:
        """Test handling of packages with None requires."""
        mock_dist = MockDistribution("requests", "2.31.0", None)

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=[mock_dist],
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["requests"])

            assert len(tree.roots) == 1
            assert tree.roots[0].children == []

    def test_handles_empty_root_list(self) -> None:
        """Test resolving with empty root package list."""
        mock_dists = create_mock_distributions(
            {
                "requests": ("2.31.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree([])

            assert tree.roots == []
            assert tree.total_count == 0

    def test_license_field_is_none_by_default(self) -> None:
        """Test that license field is None (populated later)."""
        mock_dists = create_mock_distributions(
            {
                "requests": ("2.31.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["requests"])

            assert tree.roots[0].license is None


class TestDependencyResolverPerformance:
    """Tests for performance optimization (Task 5)."""

    def test_large_dependency_tree_performance(self) -> None:
        """Test that 200+ dependencies resolve within performance targets (AC #2).

        NFR1: <30 seconds for typical project.
        This test uses mocks, so it should complete in under 1 second.
        """
        import time

        # Create packages exceeding MIN_PACKAGES_FOR_PERF_TEST (200+) with a chain pattern
        total_packages = MIN_PACKAGES_FOR_PERF_TEST + 50  # 250 packages
        root_count = 50
        packages: dict[str, tuple[str, Optional[list[str]]]] = {}
        for i in range(total_packages):
            # Create some chains to simulate transitive deps
            if i < root_count:
                # First 50 are root packages with 4 deps each
                deps = [
                    f"pkg_{i * 4 + j + root_count}>=1.0"
                    for j in range(4)
                    if i * 4 + j + root_count < total_packages
                ]
                packages[f"pkg_{i}"] = ("1.0.0", deps if deps else [])
            else:
                # Rest are leaf packages
                packages[f"pkg_{i}"] = ("1.0.0", [])

        mock_dists = create_mock_distributions(packages)

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()

            start = time.time()
            tree = resolver.resolve_tree([f"pkg_{i}" for i in range(root_count)])
            elapsed = time.time() - start

            # Should complete in under 1 second with mocks
            assert elapsed < 1.0, f"Resolution took {elapsed:.2f}s, expected <1s"

            # Verify we got reasonable number of nodes (at least root_count)
            all_nodes = tree.get_all_nodes()
            assert len(all_nodes) >= root_count, (
                f"Expected at least {root_count} nodes, got {len(all_nodes)}"
            )

    def test_diamond_pattern_efficient(self) -> None:
        """Test that diamond dependencies are processed only once."""
        # Many packages all depend on the same shared dependency
        packages: dict[str, tuple[str, Optional[list[str]]]] = {
            "shared": ("1.0.0", []),
        }
        # 100 packages all depending on "shared"
        for i in range(100):
            packages[f"pkg_{i}"] = ("1.0.0", ["shared>=1.0"])

        mock_dists = create_mock_distributions(packages)

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree([f"pkg_{i}" for i in range(100)])

            # "shared" should appear only once in the tree (visited tracking)
            all_nodes = tree.get_all_nodes()
            shared_count = sum(1 for n in all_nodes if n.name == "shared")
            assert shared_count == 1, (
                f"Expected shared to appear once, found {shared_count}"
            )

    def test_package_index_built_once(self) -> None:
        """Test that package index is built once at resolver init."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0"]),
                "B": ("1.0.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ) as mock_dist:
            resolver = DependencyResolver()

            # distributions() called once during init
            assert mock_dist.call_count == 1

            # Multiple resolve_tree calls should NOT call distributions again
            resolver.resolve_tree(["A"])
            resolver.resolve_tree(["B"])
            resolver.resolve_tree(["A", "B"])

            # Still only 1 call
            assert mock_dist.call_count == 1


class TestDependencyResolverDepthTracking:
    """Tests for dependency depth tracking (Task 3)."""

    def test_root_has_depth_zero(self) -> None:
        """Test that root packages have depth 0."""
        mock_dists = create_mock_distributions(
            {
                "requests": ("2.31.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["requests"])

            assert tree.roots[0].depth == 0
            assert tree.roots[0].is_direct is True

    def test_direct_deps_have_depth_one(self) -> None:
        """Test that direct dependencies have depth 1."""
        mock_dists = create_mock_distributions(
            {
                "requests": ("2.31.0", ["certifi>=2017.4.17"]),
                "certifi": ("2023.7.22", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["requests"])

            certifi = tree.roots[0].children[0]
            assert certifi.depth == 1
            assert certifi.is_direct is False

    def test_depth_increments_through_chain(self) -> None:
        """Test that depth increments through dependency chain."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0"]),
                "B": ("1.0.0", ["C>=1.0"]),
                "C": ("1.0.0", ["D>=1.0"]),
                "D": ("1.0.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            a = tree.roots[0]
            assert a.depth == 0

            b = a.children[0]
            assert b.depth == 1

            c = b.children[0]
            assert c.depth == 2

            d = c.children[0]
            assert d.depth == 3

    def test_get_nodes_at_depth(self) -> None:
        """Test filtering nodes by depth."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0", "C>=1.0"]),
                "B": ("1.0.0", ["D>=1.0"]),
                "C": ("1.0.0", []),
                "D": ("1.0.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            depth_0 = tree.get_nodes_at_depth(0)
            assert len(depth_0) == 1
            assert depth_0[0].name == "A"

            depth_1 = tree.get_nodes_at_depth(1)
            assert len(depth_1) == 2
            names = [n.name for n in depth_1]
            assert "B" in names
            assert "C" in names

            depth_2 = tree.get_nodes_at_depth(2)
            assert len(depth_2) == 1
            assert depth_2[0].name == "D"

    def test_max_depth_property(self) -> None:
        """Test max_depth computed property."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0"]),
                "B": ("1.0.0", ["C>=1.0"]),
                "C": ("1.0.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            assert tree.max_depth == 2


class TestCircularDependencyHandling:
    """Tests for circular dependency detection and handling (FR8)."""

    def test_simple_circular_a_b_a(self) -> None:
        """Test A→B→A circular pattern is detected."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0"]),
                "B": ("1.0.0", ["A>=1.0"]),  # Circular back to A
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            # Should complete without infinite loop
            assert len(tree.roots) == 1

            # Should detect circular reference
            assert tree.has_circular_dependencies
            assert len(tree.circular_references) == 1
            assert tree.circular_references[0].from_package == "B"
            assert tree.circular_references[0].to_package == "A"

    def test_multi_node_circular_a_b_c_a(self) -> None:
        """Test A→B→C→A circular pattern."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0"]),
                "B": ("1.0.0", ["C>=1.0"]),
                "C": ("1.0.0", ["A>=1.0"]),  # Circular back to A
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            assert tree.has_circular_dependencies
            # Path should include A, B, C
            circ = tree.circular_references[0]
            assert "A" in circ.path
            assert "B" in circ.path
            assert "C" in circ.path

    def test_each_package_processed_once(self) -> None:
        """Test that packages in circular refs are only processed once."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0"]),
                "B": ("1.0.0", ["A>=1.0"]),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            all_nodes = tree.get_all_nodes()
            node_names = [n.name for n in all_nodes]

            # Each package should appear exactly once
            assert node_names.count("A") == 1
            assert node_names.count("B") == 1

    def test_circular_ref_does_not_hang(self) -> None:
        """Test that circular dependencies complete within timeout."""
        import time

        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0"]),
                "B": ("1.0.0", ["C>=1.0"]),
                "C": ("1.0.0", ["A>=1.0"]),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()

            start = time.time()
            tree = resolver.resolve_tree(["A"])
            elapsed = time.time() - start

            # Should complete almost instantly with mocks
            assert elapsed < 1.0, f"Circular resolution took {elapsed:.2f}s"
            assert len(tree.roots) == 1

    def test_multiple_separate_circular_references(self) -> None:
        """Test multiple separate circular references in same tree."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0", "C>=1.0"]),
                "B": ("1.0.0", ["A>=1.0"]),  # Circular: B → A
                "C": ("1.0.0", ["D>=1.0"]),
                "D": ("1.0.0", ["C>=1.0"]),  # Circular: D → C
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            # Should detect both circular references
            assert tree.has_circular_dependencies
            assert len(tree.circular_references) == 2

    def test_circular_ref_path_tracking(self) -> None:
        """Test that circular reference path is tracked correctly."""
        mock_dists = create_mock_distributions(
            {
                "root": ("1.0.0", ["mid>=1.0"]),
                "mid": ("1.0.0", ["leaf>=1.0"]),
                "leaf": ("1.0.0", ["root>=1.0"]),  # Circular back to root
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["root"])

            circ = tree.circular_references[0]
            # Path should trace the chain: root → mid → leaf → root
            assert circ.from_package == "leaf"
            assert circ.to_package == "root"
            assert circ.path == ["root", "mid", "leaf", "root"]

    def test_node_circular_references_populated(self) -> None:
        """Test that DependencyNode.circular_references is populated."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0"]),
                "B": ("1.0.0", ["A>=1.0"]),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            # Find node B
            b_node = tree.roots[0].children[0]
            assert b_node.name == "B"

            # B should have A in its circular_references
            assert b_node.has_circular_references
            assert "A" in b_node.circular_references

    def test_no_circular_references_when_none_exist(self) -> None:
        """Test that tree has no circular refs when none exist."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0"]),
                "B": ("1.0.0", ["C>=1.0"]),
                "C": ("1.0.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            assert not tree.has_circular_dependencies
            assert tree.circular_references == []

    def test_diamond_with_circular(self) -> None:
        """Test diamond pattern with circular reference.

        A → B → D
        A → C → D → B (creates circular because B already visited)
        """
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0", "C>=1.0"]),
                "B": ("1.0.0", ["D>=1.0"]),
                "C": ("1.0.0", ["D>=1.0"]),
                "D": (
                    "1.0.0",
                    ["B>=1.0"],
                ),  # D → B creates circular (B already visited)
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            # Should handle diamond + circular
            assert tree.has_circular_dependencies
            all_nodes = tree.get_all_nodes()
            node_names = [n.name for n in all_nodes]

            # Each package should appear at most once
            assert node_names.count("A") == 1
            assert node_names.count("B") == 1


class TestDependencyOriginPathTracking:
    """Tests for dependency origin path tracking (FR9)."""

    def test_root_has_empty_origin_path(self) -> None:
        """Test that root nodes have empty origin_path."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            assert tree.roots[0].origin_path == []

    def test_direct_dep_has_root_in_path(self) -> None:
        """Test depth-1 dependency has parent in origin_path."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0"]),
                "B": ("1.0.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            b_node = tree.roots[0].children[0]
            assert b_node.origin_path == ["A"]

    def test_transitive_dep_has_full_chain(self) -> None:
        """Test depth-3 dependency has full chain in origin_path."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0"]),
                "B": ("1.0.0", ["C>=1.0"]),
                "C": ("1.0.0", ["D>=1.0"]),
                "D": ("1.0.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            d_node = tree.roots[0].children[0].children[0].children[0]
            assert d_node.origin_path == ["A", "B", "C"]

    def test_origin_path_with_multiple_roots(self) -> None:
        """Test origin_path is correct with multiple root packages."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["C>=1.0"]),
                "B": ("1.0.0", ["D>=1.0"]),
                "C": ("1.0.0", []),
                "D": ("1.0.0", []),
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A", "B"])

            # A's child C should have origin_path ["A"]
            c_node = tree.roots[0].children[0]
            assert c_node.origin_path == ["A"]

            # B's child D should have origin_path ["B"]
            d_node = tree.roots[1].children[0]
            assert d_node.origin_path == ["B"]

    def test_origin_path_with_circular_reference(self) -> None:
        """Test origin_path works correctly with circular dependencies."""
        mock_dists = create_mock_distributions(
            {
                "A": ("1.0.0", ["B>=1.0"]),
                "B": ("1.0.0", ["C>=1.0"]),
                "C": ("1.0.0", ["A>=1.0"]),  # Circular back to A
            }
        )

        with patch(
            "license_analyzer.resolvers.dependency.distributions",
            return_value=mock_dists,
        ):
            resolver = DependencyResolver()
            tree = resolver.resolve_tree(["A"])

            # B should have origin_path ["A"]
            b_node = tree.roots[0].children[0]
            assert b_node.origin_path == ["A"]

            # C should have origin_path ["A", "B"]
            c_node = b_node.children[0]
            assert c_node.origin_path == ["A", "B"]
