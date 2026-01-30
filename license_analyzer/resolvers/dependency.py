"""Transitive dependency resolution for license analysis.

Provides DependencyResolver class for building dependency trees (FR7).
Implements circular dependency detection and tracking (FR8).
"""
from importlib.metadata import Distribution, distributions
from typing import Optional

from packaging.requirements import InvalidRequirement, Requirement

from license_analyzer.models.dependency import (
    CircularReference,
    DependencyNode,
    DependencyTree,
)


class DependencyResolver:
    """Resolves transitive dependencies for installed packages.

    Implements FR7: User can view complete transitive dependency tree.
    """

    def __init__(self) -> None:
        """Initialize resolver with package index."""
        # Build index of installed packages for fast lookup
        self._installed: dict[str, Distribution] = {}
        for dist in distributions():
            name = dist.metadata.get("Name")
            if name:
                # Normalize package names (PEP 503)
                self._installed[self._normalize(name)] = dist

    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize package name per PEP 503.

        Args:
            name: Package name to normalize.

        Returns:
            Normalized package name (lowercase, underscores).
        """
        return name.lower().replace("-", "_").replace(".", "_")

    def resolve_tree(
        self,
        root_packages: list[str],
        max_depth: Optional[int] = None,
    ) -> DependencyTree:
        """Build complete dependency tree from root packages.

        Args:
            root_packages: List of direct dependency names.
            max_depth: Maximum depth to traverse (None for unlimited).

        Returns:
            DependencyTree with all resolved dependencies and circular refs.
        """
        visited: set[str] = set()
        circular_refs: list[CircularReference] = []
        roots: list[DependencyNode] = []

        for pkg_name in root_packages:
            node = self._resolve_package(
                pkg_name,
                depth=0,
                max_depth=max_depth,
                visited=visited,
                path=[],
                circular_refs=circular_refs,
            )
            if node is not None:
                roots.append(node)

        return DependencyTree(roots=roots, circular_references=circular_refs)

    def _resolve_package(
        self,
        name: str,
        depth: int,
        max_depth: Optional[int],
        visited: set[str],
        path: list[str],
        circular_refs: list[CircularReference],
    ) -> Optional[DependencyNode]:
        """Recursively resolve a package and its dependencies.

        Args:
            name: Package name to resolve.
            depth: Current depth in tree.
            max_depth: Maximum depth (None for unlimited).
            visited: Set of already visited package names.
            path: Current path from root to this package.
            circular_refs: List to accumulate circular references.

        Returns:
            DependencyNode for the package, or None if not found/visited.
        """
        normalized = self._normalize(name)

        # Skip if already visited (prevents infinite loops)
        # Note: Circular reference recording is handled in _resolve_requirement
        if normalized in visited:
            return None

        visited.add(normalized)

        # Check depth limit
        if max_depth is not None and depth > max_depth:
            return None

        # Get distribution for this package
        dist = self._installed.get(normalized)
        if dist is None:
            return None  # Package not installed

        # Build node
        actual_name = dist.metadata.get("Name", name)
        version = dist.metadata.get("Version", "unknown")
        current_path = path + [actual_name]
        children: list[DependencyNode] = []
        node_circular_references: list[str] = []

        # Resolve child dependencies
        requires = dist.requires or []
        for req_str in requires:
            child_result = self._resolve_requirement(
                req_str,
                depth=depth + 1,
                max_depth=max_depth,
                visited=visited,
                path=current_path,
                circular_refs=circular_refs,
                node_circular_references=node_circular_references,
            )
            if child_result is not None:
                children.append(child_result)

        return DependencyNode(
            name=actual_name,
            version=version,
            depth=depth,
            license=None,  # Populated later by license resolver
            children=children,
            circular_references=node_circular_references,
            origin_path=path,  # FR9: Track path from root to this node
        )

    def _resolve_requirement(
        self,
        req_str: str,
        depth: int,
        max_depth: Optional[int],
        visited: set[str],
        path: list[str],
        circular_refs: list[CircularReference],
        node_circular_references: list[str],
    ) -> Optional[DependencyNode]:
        """Parse and resolve a requirement string.

        Args:
            req_str: Requirement string (e.g., "requests>=2.0.0").
            depth: Current depth in tree.
            max_depth: Maximum depth (None for unlimited).
            visited: Set of already visited package names.
            path: Current path from root to parent package.
            circular_refs: List to accumulate CircularReference objects.
            node_circular_references: Accumulates circular ref names for parent node.

        Returns:
            DependencyNode if requirement should be included, None otherwise.
        """
        try:
            req = Requirement(req_str)

            # Skip if marker doesn't match current environment
            if req.marker and not req.marker.evaluate():
                return None

            # Skip extras-only requirements (handled separately if needed)
            # These are dependencies that only apply when an extra is requested
            if self._is_extras_only_marker(req.marker):
                return None

            # Check if this would create a circular reference
            normalized = self._normalize(req.name)
            if normalized in visited:
                # Record on the parent node
                node_circular_references.append(req.name)
                # Record in the global list
                circular_refs.append(CircularReference(
                    from_package=path[-1] if path else "root",
                    to_package=req.name,
                    path=path + [req.name],
                ))
                return None

            return self._resolve_package(
                req.name,
                depth=depth,
                max_depth=max_depth,
                visited=visited,
                path=path,
                circular_refs=circular_refs,
            )
        except InvalidRequirement:
            # Skip malformed requirements
            return None

    @staticmethod
    def _is_extras_only_marker(marker: Optional[object]) -> bool:
        """Check if marker indicates an extras-only dependency.

        Extras-only dependencies have markers that reference 'extra', like:
        - extra == "dev"
        - extra == 'test'

        Args:
            marker: Parsed marker object from Requirement.

        Returns:
            True if this is an extras-only dependency.
        """
        if marker is None:
            return False
        # Convert marker to string and check for 'extra' variable reference
        marker_str = str(marker)
        return "extra" in marker_str

    def get_installed_packages(self) -> list[str]:
        """Get list of all installed package names.

        Returns:
            List of normalized package names.
        """
        return sorted(self._installed.keys())
