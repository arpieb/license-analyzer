"""Tests for Markdown tree output formatter."""

from license_analyzer.models.dependency import (
    CircularReference,
    DependencyNode,
    DependencyTree,
)
from license_analyzer.output.tree_markdown import TreeMarkdownFormatter


class TestTreeMarkdownFormatter:
    """Tests for TreeMarkdownFormatter class."""

    def test_format_empty_tree(self) -> None:
        """Test formatting empty tree shows message."""
        formatter = TreeMarkdownFormatter()
        tree = DependencyTree(roots=[])

        result = formatter.format_dependency_tree(tree)

        assert "# Dependency Tree" in result
        assert "*No dependencies found.*" in result

    def test_format_single_root(self) -> None:
        """Test formatting tree with single root node."""
        formatter = TreeMarkdownFormatter()
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)

        assert "# Dependency Tree" in result
        assert "**requests**@2.31.0" in result
        assert "Apache-2.0" in result
        assert "## Summary" in result

    def test_format_nested_tree(self) -> None:
        """Test formatting tree with nested children."""
        formatter = TreeMarkdownFormatter()

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

        # Check all packages appear
        assert "requests" in result
        assert "urllib3" in result
        assert "idna" in result
        # Check tree structure characters
        assert "└──" in result or "├──" in result

    def test_format_multiple_roots(self) -> None:
        """Test formatting tree with multiple root packages."""
        formatter = TreeMarkdownFormatter()

        root1 = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        root2 = DependencyNode(
            name="click", version="8.1.0", depth=0, license="BSD-3-Clause"
        )
        root3 = DependencyNode(name="pydantic", version="2.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root1, root2, root3])

        result = formatter.format_dependency_tree(tree)

        # Check all roots appear
        assert "requests" in result
        assert "click" in result
        assert "pydantic" in result
        # First two roots should use ├── (not last)
        assert "├──" in result
        # Last root should use └── (is last)
        assert "└──" in result


class TestTreeMarkdownFormatterSummary:
    """Tests for summary section in Markdown output."""

    def test_summary_table_present(self) -> None:
        """Test summary includes markdown table."""
        formatter = TreeMarkdownFormatter()
        root = DependencyNode(
            name="requests", version="2.31.0", depth=0, license="Apache-2.0"
        )
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)

        assert "| Metric | Value |" in result
        assert "| Total Packages |" in result
        assert "| Max Depth |" in result

    def test_summary_shows_passing_badge_for_clean(self) -> None:
        """Test passing status badge for no problematic licenses."""
        formatter = TreeMarkdownFormatter()
        root = DependencyNode(name="mit-pkg", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)

        assert "passing" in result
        assert "green" in result

    def test_summary_shows_failing_badge_for_problematic(self) -> None:
        """Test failing status badge for problematic licenses."""
        formatter = TreeMarkdownFormatter()
        root = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)

        assert "failing" in result
        assert "red" in result


class TestTreeMarkdownFormatterProblematic:
    """Tests for problematic section in Markdown output."""

    def test_problematic_section_present(self) -> None:
        """Test problematic section appears for GPL licenses."""
        formatter = TreeMarkdownFormatter()
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

        assert "## ⚠️ Problematic Licenses" in result
        assert "gpl-pkg" in result
        assert "GPL-3.0" in result

    def test_problematic_section_absent_when_clean(self) -> None:
        """Test no problematic section for permissive licenses."""
        formatter = TreeMarkdownFormatter()
        root = DependencyNode(name="mit-pkg", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)

        assert "## ⚠️ Problematic Licenses" not in result

    def test_problematic_table_format(self) -> None:
        """Test problematic section uses table format."""
        formatter = TreeMarkdownFormatter()
        gpl_node = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        tree = DependencyTree(roots=[gpl_node])

        result = formatter.format_dependency_tree(tree)

        assert "| Package | Version | License | Path |" in result
        assert "| gpl-pkg |" in result


class TestTreeMarkdownFormatterCircular:
    """Tests for circular dependencies in Markdown output."""

    def test_circular_section_present(self) -> None:
        """Test circular section appears when circular deps exist."""
        formatter = TreeMarkdownFormatter()
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

        assert "## ↺ Circular Dependencies" in result
        assert "pkg-a" in result
        assert "pkg-b" in result

    def test_circular_section_absent_when_none(self) -> None:
        """Test no circular section when no circular deps."""
        formatter = TreeMarkdownFormatter()
        root = DependencyNode(name="pkg", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)

        assert "## ↺ Circular Dependencies" not in result

    def test_circular_marker_in_tree(self) -> None:
        """Test circular marker appears next to node."""
        formatter = TreeMarkdownFormatter()
        root = DependencyNode(
            name="pkg-a",
            version="1.0.0",
            depth=0,
            license="MIT",
            circular_references=["pkg-b"],
        )
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)

        assert "↺" in result


class TestTreeMarkdownFormatterWarnings:
    """Tests for warning markers in Markdown output."""

    def test_warning_marker_for_problematic(self) -> None:
        """Test warning emoji appears for problematic licenses."""
        formatter = TreeMarkdownFormatter()
        root = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)

        assert "⚠️" in result

    def test_no_warning_for_permissive(self) -> None:
        """Test no warning for permissive licenses."""
        formatter = TreeMarkdownFormatter()
        root = DependencyNode(name="mit-pkg", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)

        # Warning should only be in the tree, not in summary for clean tree
        lines = [line for line in result.split("\n") if "mit-pkg" in line]
        for line in lines:
            assert "⚠️" not in line


class TestTreeMarkdownFormatterLicenseCategories:
    """Tests for license categories in Markdown output."""

    def test_license_categories_section_present(self) -> None:
        """Test license categories section is present in output."""
        formatter = TreeMarkdownFormatter()
        root = DependencyNode(name="pkg", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)

        assert "## License Categories" in result

    def test_license_categories_table_format(self) -> None:
        """Test license categories use table format."""
        formatter = TreeMarkdownFormatter()
        root = DependencyNode(name="pkg", version="1.0.0", depth=0, license="MIT")
        tree = DependencyTree(roots=[root])

        result = formatter.format_dependency_tree(tree)

        assert "| Category | Count | Percentage | Licenses |" in result
        assert "|----------|-------|------------|----------|" in result

    def test_license_categories_shows_values(self) -> None:
        """Test license categories show correct values."""
        formatter = TreeMarkdownFormatter()

        mit_node = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=0, license="MIT"
        )
        gpl_node = DependencyNode(
            name="gpl-pkg", version="1.0.0", depth=0, license="GPL-3.0"
        )
        tree = DependencyTree(roots=[mit_node, gpl_node])

        result = formatter.format_dependency_tree(tree)

        # Check table contains category data
        assert "| Permissive | 1 | 50.0% |" in result
        assert "| Copyleft | 1 | 50.0% |" in result

    def test_license_categories_shows_license_names(self) -> None:
        """Test license categories include license identifiers."""
        formatter = TreeMarkdownFormatter()

        mit_node = DependencyNode(
            name="mit-pkg", version="1.0.0", depth=0, license="MIT"
        )
        apache_node = DependencyNode(
            name="apache-pkg", version="1.0.0", depth=0, license="Apache-2.0"
        )
        tree = DependencyTree(roots=[mit_node, apache_node])

        result = formatter.format_dependency_tree(tree)

        # Should show licenses in the table
        assert "MIT" in result
        assert "Apache-2.0" in result

    def test_license_categories_truncates_many_licenses(self) -> None:
        """Test license list truncation with many licenses."""
        formatter = TreeMarkdownFormatter()

        # Create nodes with many permissive licenses (>5 to trigger truncation)
        nodes = []
        licenses = [
            "MIT",
            "Apache-2.0",
            "BSD-3-Clause",
            "ISC",
            "BSD-2-Clause",
            "Unlicense",
            "CC0-1.0",
        ]
        for i, lic in enumerate(licenses):
            nodes.append(
                DependencyNode(name=f"pkg-{i}", version="1.0.0", depth=0, license=lic)
            )
        tree = DependencyTree(roots=nodes)

        result = formatter.format_dependency_tree(tree)

        # Should truncate and show "+N more"
        assert "more)" in result
