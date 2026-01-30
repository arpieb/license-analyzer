"""Tests for tree output formatter."""

from io import StringIO

from rich.console import Console

from license_analyzer.models.dependency import (
    CircularReference,
    DependencyNode,
    DependencyTree,
)
from license_analyzer.output.tree import TreeFormatter


class TestTreeFormatter:
    """Tests for TreeFormatter class."""

    def test_init_creates_default_console(self) -> None:
        """Test TreeFormatter creates console if not provided."""
        formatter = TreeFormatter()
        assert formatter._console is not None

    def test_init_uses_provided_console(self) -> None:
        """Test TreeFormatter uses provided console."""
        console = Console()
        formatter = TreeFormatter(console=console)
        assert formatter._console is console

    def test_format_empty_tree(self) -> None:
        """Test formatting empty tree shows message."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        formatter = TreeFormatter(console=console)

        tree = DependencyTree(roots=[])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "No dependencies found" in result

    def test_format_single_root(self) -> None:
        """Test formatting tree with single root node."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        tree = DependencyTree(roots=[root])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "requests@2.31.0" in result
        assert "Apache-2.0" in result
        assert "Total packages:" in result
        assert "1" in result

    def test_format_nested_tree(self) -> None:
        """Test formatting tree with nested children."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

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
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "requests@2.31.0" in result
        assert "urllib3@2.0.0" in result
        assert "idna@3.4" in result
        assert "Max depth:" in result
        assert "2" in result


class TestTreeFormatterLicenseColors:
    """Tests for license color coding."""

    def test_permissive_license_shown(self) -> None:
        """Test permissive licenses are displayed."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

        root = DependencyNode(name="pkg", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "MIT" in result

    def test_weak_copyleft_license_shown(self) -> None:
        """Test weak copyleft licenses (LGPL, MPL) are displayed correctly."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

        root = DependencyNode(
            name="lgpl-pkg", version="1.0.0", depth=0, license="LGPL-3.0"
        )
        tree = DependencyTree(roots=[root])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "LGPL-3.0" in result
        # LGPL is problematic, so should show warning and be in problematic list
        assert "Problematic licenses:" in result

    def test_problematic_license_has_warning(self) -> None:
        """Test problematic licenses show warning marker."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

        root = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        tree = DependencyTree(roots=[root])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "GPL-3.0" in result
        assert "Problematic licenses:" in result
        # Should show count of 1
        assert "1" in result

    def test_unknown_license_shown(self) -> None:
        """Test unknown/None licenses show as Unknown."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

        root = DependencyNode(name="mystery", version="1.0.0", depth=0, license=None)
        tree = DependencyTree(roots=[root])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "Unknown" in result


class TestTreeFormatterCircularDependencies:
    """Tests for circular dependency display."""

    def test_circular_reference_marker_shown(self) -> None:
        """Test circular references show marker."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

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
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        # Should show circular marker
        assert "↺" in result
        assert "Circular dependencies:" in result

    def test_no_circular_references_shows_zero(self) -> None:
        """Test no circular references shows 0 count."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

        root = DependencyNode(name="pkg", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "Circular dependencies:" in result
        assert "0" in result


class TestTreeFormatterSummary:
    """Tests for summary statistics."""

    def test_summary_shows_total_count(self) -> None:
        """Test summary shows correct total count."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

        child = DependencyNode(name="child", version="1.0.0", depth=1, license="MIT")
        root = DependencyNode(
            name="root",
            version="1.0.0",
            depth=0,
            license="MIT",
            children=[child],
        )
        tree = DependencyTree(roots=[root])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "Total packages:" in result
        # Total should be 2
        assert "2" in result

    def test_summary_shows_direct_deps_count(self) -> None:
        """Test summary shows direct dependencies count."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

        root1 = DependencyNode(name="pkg-a", version="1.0.0", depth=0, license="MIT")
        root2 = DependencyNode(name="pkg-b", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root1, root2])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "Direct dependencies:" in result
        # Should show 2 direct deps

    def test_summary_shows_problematic_paths(self) -> None:
        """Test summary shows problematic license paths."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

        gpl_child = DependencyNode(
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
            children=[gpl_child],
        )
        tree = DependencyTree(roots=[root])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "Problematic licenses:" in result
        # Should show the path
        assert "root-pkg" in result
        assert "gpl-pkg" in result


class TestTreeFormatterNodeLabel:
    """Tests for node label formatting."""

    def test_format_node_label_basic(self) -> None:
        """Test basic node label format."""
        formatter = TreeFormatter()
        node = DependencyNode(name="requests", version="2.31.0", depth=0, license="MIT")

        label = formatter._format_node_label(node)

        assert "requests@2.31.0" in label
        assert "MIT" in label

    def test_format_node_label_with_warning(self) -> None:
        """Test node label includes warning for problematic license."""
        formatter = TreeFormatter()
        node = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )

        label = formatter._format_node_label(node)

        assert "gpl-pkg@1.0.0" in label
        assert "GPL-3.0" in label
        # Should have warning marker
        assert "⚠" in label

    def test_format_node_label_unknown_license(self) -> None:
        """Test node label shows Unknown for None license."""
        formatter = TreeFormatter()
        node = DependencyNode(name="mystery", version="1.0.0", depth=0, license=None)

        label = formatter._format_node_label(node)

        assert "mystery@1.0.0" in label
        assert "Unknown" in label


class TestTreeFormatterLicenseCategories:
    """Tests for license category display."""

    def test_license_categories_section_displayed(self) -> None:
        """Test license categories section appears in output."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

        root = DependencyNode(name="pkg", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "License Categories:" in result

    def test_license_categories_shows_permissive(self) -> None:
        """Test permissive category is shown with count."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

        root = DependencyNode(name="pkg", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "Permissive" in result
        assert "100" in result  # 100%

    def test_license_categories_shows_mixed_categories(self) -> None:
        """Test mixed license categories are all shown."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

        mit_node = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=0, license="MIT"
        )
        gpl_node = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        tree = DependencyTree(roots=[mit_node, gpl_node])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        assert "Permissive" in result
        assert "Copyleft" in result
        assert "50" in result  # 50% each

    def test_license_categories_only_shows_nonzero(self) -> None:
        """Test only non-zero categories are displayed."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = TreeFormatter(console=console)

        root = DependencyNode(name="pkg", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root])
        formatter.format_dependency_tree(tree)

        result = output.getvalue()
        # Should show Permissive but not others
        assert "Permissive" in result
        # Count of 0 lines that mention Copyleft - it should not appear at all
        lines = result.split("\n")
        copyleft_lines = [line for line in lines if "Copyleft:" in line and "1" in line]
        assert len(copyleft_lines) == 0
