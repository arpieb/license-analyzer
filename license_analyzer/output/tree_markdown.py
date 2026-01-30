"""Markdown output formatter for dependency tree."""
from license_analyzer.analysis.problematic import is_problematic_license
from license_analyzer.models.dependency import DependencyNode, DependencyTree


class TreeMarkdownFormatter:
    """Format dependency tree as Markdown output.

    Provides formatted Markdown representation of the dependency tree
    for documentation and reports.
    """

    def format_dependency_tree(self, tree: DependencyTree) -> str:
        """Format dependency tree as Markdown string.

        Args:
            tree: The dependency tree to format.

        Returns:
            Markdown string representation of the tree.
        """
        lines: list[str] = []

        # Title
        lines.append("# Dependency Tree")
        lines.append("")

        if not tree.roots:
            lines.append("*No dependencies found.*")
            return "\n".join(lines)

        # Summary section
        lines.extend(self._format_summary(tree))
        lines.append("")

        # License categories section
        lines.extend(self._format_license_categories(tree))
        lines.append("")

        # Tree structure
        lines.append("## Dependencies")
        lines.append("")
        for i, root in enumerate(tree.roots):
            is_last_root = i == len(tree.roots) - 1
            lines.extend(self._format_node(root, prefix="", is_last=is_last_root))
        lines.append("")

        # Problematic licenses section
        problematic = tree.get_nodes_with_problematic_licenses()
        if problematic:
            lines.extend(self._format_problematic_section(problematic))
            lines.append("")

        # Circular dependencies section
        if tree.has_circular_dependencies:
            lines.extend(self._format_circular_section(tree))
            lines.append("")

        return "\n".join(lines)

    def _format_summary(self, tree: DependencyTree) -> list[str]:
        """Format summary statistics section.

        Args:
            tree: The dependency tree.

        Returns:
            List of Markdown lines for summary.
        """
        problematic_count = len(tree.get_nodes_with_problematic_licenses())
        status = "passing" if problematic_count == 0 else "failing"
        status_color = "green" if problematic_count == 0 else "red"

        lines = [
            "## Summary",
            "",
            f"![Status](https://img.shields.io/badge/License%20Check-{status}-{status_color})",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Packages | {tree.total_count} |",
            f"| Direct Dependencies | {len(tree.roots)} |",
            f"| Max Depth | {tree.max_depth} |",
            f"| Problematic Licenses | {problematic_count} |",
            f"| Circular Dependencies | {len(tree.circular_references)} |",
        ]
        return lines

    def _format_node(
        self, node: DependencyNode, prefix: str, is_last: bool
    ) -> list[str]:
        """Format a single node and its children.

        Args:
            node: The node to format.
            prefix: Current indentation prefix.
            is_last: Whether this is the last sibling.

        Returns:
            List of Markdown lines for this node and children.
        """
        lines: list[str] = []

        # Tree characters
        connector = "└── " if is_last else "├── "
        child_prefix = prefix + ("    " if is_last else "│   ")

        # Node content
        license_str = node.license or "Unknown"

        # Warning indicator for problematic
        warning = " ⚠️" if is_problematic_license(node.license) else ""

        # Circular reference indicator
        circular = " ↺" if node.has_circular_references else ""

        # Format the line
        node_info = f"**{node.name}**@{node.version} ({license_str}){warning}{circular}"
        lines.append(f"{prefix}{connector}{node_info}")

        # Add circular reference details as sub-items
        for circ_ref in node.circular_references:
            circ_line = f"{child_prefix}↺ *circular: {circ_ref}*"
            lines.append(circ_line)

        # Recursively add children
        children = node.children
        for i, child in enumerate(children):
            is_child_last = i == len(children) - 1
            lines.extend(self._format_node(child, child_prefix, is_child_last))

        return lines

    def _format_license_categories(self, tree: DependencyTree) -> list[str]:
        """Format license categories breakdown section.

        Args:
            tree: The dependency tree.

        Returns:
            List of Markdown lines for license categories.
        """
        stats = tree.get_license_statistics()

        lines = [
            "## License Categories",
            "",
            "| Category | Count | Percentage | Licenses |",
            "|----------|-------|------------|----------|",
        ]

        for _name, cat_stats in stats.to_dict().items():
            licenses_str = ", ".join(cat_stats.licenses[:5])  # Limit to first 5
            if len(cat_stats.licenses) > 5:
                licenses_str += f", ... (+{len(cat_stats.licenses) - 5} more)"
            lines.append(
                f"| {cat_stats.category} | {cat_stats.count} | "
                f"{cat_stats.percentage}% | {licenses_str} |"
            )

        return lines

    def _format_problematic_section(
        self, problematic: list[DependencyNode]
    ) -> list[str]:
        """Format problematic licenses section.

        Args:
            problematic: List of nodes with problematic licenses.

        Returns:
            List of Markdown lines.
        """
        lines = [
            "## ⚠️ Problematic Licenses",
            "",
            "The following packages have licenses that may be problematic",
            "for commercial or permissive-licensed projects:",
            "",
            "| Package | Version | License | Path |",
            "|---------|---------|---------|------|",
        ]

        for node in problematic:
            path = node.get_origin_path_display()
            lines.append(f"| {node.name} | {node.version} | {node.license} | {path} |")

        return lines

    def _format_circular_section(self, tree: DependencyTree) -> list[str]:
        """Format circular dependencies section.

        Args:
            tree: The dependency tree.

        Returns:
            List of Markdown lines.
        """
        lines = [
            "## ↺ Circular Dependencies",
            "",
            "The following circular dependencies were detected:",
            "",
        ]

        for ref in tree.circular_references:
            path_str = " → ".join(ref.path)
            lines.append(f"- {ref.from_package} → {ref.to_package}: `{path_str}`")

        return lines
