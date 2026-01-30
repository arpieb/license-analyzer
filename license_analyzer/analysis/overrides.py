"""License override functionality for manual license corrections."""
from __future__ import annotations

from license_analyzer.models.config import AnalyzerConfig
from license_analyzer.models.dependency import DependencyNode, DependencyTree
from license_analyzer.models.scan import PackageLicense


def apply_license_overrides(
    packages: list[PackageLicense],
    config: AnalyzerConfig,
) -> list[PackageLicense]:
    """Apply manual license overrides to packages.

    Overrides are applied AFTER license resolution to preserve the
    original detected license for reporting. Package name matching
    is case-sensitive.

    Args:
        packages: List of packages with resolved licenses.
        config: Configuration with overrides dict.

    Returns:
        List of PackageLicense with overrides applied.
        Original license preserved in original_license field.
        If overrides is None or empty, returns packages unchanged.
    """
    if not config.overrides:
        return packages

    result: list[PackageLicense] = []
    for pkg in packages:
        if pkg.name in config.overrides:
            override = config.overrides[pkg.name]
            result.append(
                PackageLicense(
                    name=pkg.name,
                    version=pkg.version,
                    license=override.license,
                    original_license=pkg.license,
                    override_reason=override.reason,
                )
            )
        else:
            result.append(pkg)

    return result


def apply_overrides_to_tree(
    tree: DependencyTree,
    config: AnalyzerConfig,
) -> DependencyTree:
    """Apply manual license overrides to a dependency tree.

    Recursively walks the tree and applies overrides to matching package names.
    Package name matching is case-sensitive.

    Note: Unlike apply_license_overrides for PackageLicense, the DependencyNode
    model does not track original_license or override_reason. Only the license
    field is updated.

    Args:
        tree: DependencyTree with resolved licenses.
        config: Configuration with overrides dict.

    Returns:
        New DependencyTree with overrides applied.
        If overrides is None or empty, returns tree unchanged.
    """
    if not config.overrides:
        return tree

    def apply_to_node(node: DependencyNode) -> DependencyNode:
        """Recursively apply overrides to a node and its children."""
        # Check if this node has an override
        new_license = node.license
        if node.name in config.overrides:
            new_license = config.overrides[node.name].license

        # Recursively process children
        new_children = [apply_to_node(child) for child in node.children]

        # Create new node with potentially updated license
        return DependencyNode(
            name=node.name,
            version=node.version,
            depth=node.depth,
            license=new_license,
            children=new_children,
            circular_references=node.circular_references,
            origin_path=node.origin_path,
        )

    # Apply to all root nodes
    new_roots = [apply_to_node(root) for root in tree.roots]

    return DependencyTree(
        roots=new_roots,
        circular_references=tree.circular_references,
    )
