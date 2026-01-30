"""JSON output formatter for dependency tree."""

import json
from typing import Any

from license_analyzer.analysis.problematic import is_problematic_license
from license_analyzer.models.dependency import DependencyNode, DependencyTree


class TreeJsonFormatter:
    """Format dependency tree as JSON output.

    Provides structured JSON representation of the dependency tree
    for programmatic processing and CI/CD integration.
    """

    def format_dependency_tree(self, tree: DependencyTree) -> str:
        """Format dependency tree as JSON string.

        Args:
            tree: The dependency tree to format.

        Returns:
            JSON string representation of the tree.
        """
        output = self._build_output(tree)
        return json.dumps(output, indent=2)

    def _build_output(self, tree: DependencyTree) -> dict[str, Any]:
        """Build the output dictionary structure.

        Args:
            tree: The dependency tree to convert.

        Returns:
            Dictionary ready for JSON serialization.
        """
        # Get problematic nodes for summary
        problematic_nodes = tree.get_nodes_with_problematic_licenses()

        # Get license statistics
        license_stats = tree.get_license_statistics()

        return {
            "dependencies": [self._node_to_dict(root) for root in tree.roots],
            "summary": {
                "total_packages": tree.total_count,
                "max_depth": tree.max_depth,
                "direct_dependencies": len(tree.roots),
                "problematic_licenses": len(problematic_nodes),
                "has_circular_dependencies": tree.has_circular_dependencies,
                "circular_dependency_count": len(tree.circular_references),
            },
            "license_categories": {
                "permissive": {
                    "count": license_stats.permissive.count,
                    "percentage": license_stats.permissive.percentage,
                    "licenses": license_stats.permissive.licenses,
                },
                "copyleft": {
                    "count": license_stats.copyleft.count,
                    "percentage": license_stats.copyleft.percentage,
                    "licenses": license_stats.copyleft.licenses,
                },
                "weak_copyleft": {
                    "count": license_stats.weak_copyleft.count,
                    "percentage": license_stats.weak_copyleft.percentage,
                    "licenses": license_stats.weak_copyleft.licenses,
                },
                "unknown": {
                    "count": license_stats.unknown.count,
                    "percentage": license_stats.unknown.percentage,
                    "licenses": license_stats.unknown.licenses,
                },
            },
            "problematic": [
                {
                    "name": node.name,
                    "version": node.version,
                    "license": node.license,
                    "path": node.get_origin_path_display(),
                }
                for node in problematic_nodes
            ],
            "circular_references": [
                {
                    "from_package": ref.from_package,
                    "to_package": ref.to_package,
                    "path": ref.path,
                }
                for ref in tree.circular_references
            ],
        }

    def _node_to_dict(self, node: DependencyNode) -> dict[str, Any]:
        """Convert a dependency node to dictionary.

        Args:
            node: The node to convert.

        Returns:
            Dictionary representation of the node.
        """
        return {
            "name": node.name,
            "version": node.version,
            "license": node.license,
            "depth": node.depth,
            "is_problematic": is_problematic_license(node.license),
            "has_circular_references": node.has_circular_references,
            "circular_references": node.circular_references,
            "children": [self._node_to_dict(child) for child in node.children],
        }
