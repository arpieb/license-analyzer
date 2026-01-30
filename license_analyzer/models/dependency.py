"""Dependency tree models for license-analyzer.

Provides data structures for representing transitive dependency relationships (FR7).
Includes circular dependency detection and tracking (FR8).
Includes license compatibility checking models (FR13).
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class CompatibilityStatus(Enum):
    """Status of license compatibility check."""

    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


class CompatibilityResult(BaseModel):
    """Result of a license compatibility check between two licenses.

    Implements FR13: System can identify license compatibility issues.
    """

    license_a: str = Field(description="First license identifier")
    license_b: str = Field(description="Second license identifier")
    status: CompatibilityStatus = Field(description="Compatibility status")
    reason: str = Field(description="Explanation of compatibility determination")

    model_config = {"extra": "forbid"}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def compatible(self) -> bool:
        """True if licenses are compatible."""
        return self.status == CompatibilityStatus.COMPATIBLE


class CategoryStatistics(BaseModel):
    """Statistics for a single license category."""

    category: str = Field(description="License category name")
    count: int = Field(ge=0, description="Number of packages in this category")
    percentage: float = Field(ge=0, le=100, description="Percentage of total packages")
    licenses: list[str] = Field(
        default_factory=list,
        description="Unique license identifiers in this category",
    )

    model_config = {"extra": "forbid"}


class LicenseStatistics(BaseModel):
    """Aggregated license statistics for a dependency tree."""

    total_packages: int = Field(ge=0, description="Total number of packages")
    permissive: CategoryStatistics = Field(description="Permissive license stats")
    copyleft: CategoryStatistics = Field(description="Strong copyleft license stats")
    weak_copyleft: CategoryStatistics = Field(description="Weak copyleft license stats")
    unknown: CategoryStatistics = Field(description="Unknown license stats")

    model_config = {"extra": "forbid"}

    def to_dict(self) -> dict[str, "CategoryStatistics"]:
        """Return categories as a dictionary for iteration.

        Returns:
            Dict mapping category name to CategoryStatistics.
        """
        return {
            "permissive": self.permissive,
            "copyleft": self.copyleft,
            "weak_copyleft": self.weak_copyleft,
            "unknown": self.unknown,
        }


class CircularReference(BaseModel):
    """Represents a detected circular dependency.

    Implements FR8: System can resolve circular dependencies without infinite loops.
    """

    from_package: str = Field(description="Package that created the circular reference")
    to_package: str = Field(description="Package being referenced circularly")
    path: list[str] = Field(
        default_factory=list,
        description="Full path from root to circular reference",
    )

    model_config = {"extra": "forbid"}


class DependencyNode(BaseModel):
    """A node in the dependency tree.

    Represents a single package with its version, depth in the tree,
    license information, and child dependencies.
    """

    name: str = Field(description="Package name")
    version: str = Field(description="Package version")
    depth: int = Field(ge=0, description="Depth in dependency tree (0 = direct)")
    license: Optional[str] = Field(
        default=None,
        description="SPDX license identifier",
    )
    children: list["DependencyNode"] = Field(
        default_factory=list,
        description="Child dependencies",
    )
    circular_references: list[str] = Field(
        default_factory=list,
        description="Package names that would create circular dependencies",
    )
    origin_path: list[str] = Field(
        default_factory=list,
        description="Path from root to this node (package names)",
    )

    model_config = {"extra": "forbid"}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_direct(self) -> bool:
        """True if this is a direct dependency (depth 0)."""
        return self.depth == 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_circular_references(self) -> bool:
        """True if this node has circular references."""
        return len(self.circular_references) > 0

    def get_all_descendants(self) -> list["DependencyNode"]:
        """Get all descendant nodes (flattened).

        Returns:
            List of all nodes below this node in the tree.
        """
        result: list[DependencyNode] = []
        for child in self.children:
            result.append(child)
            result.extend(child.get_all_descendants())
        return result

    def get_origin_path_display(self) -> str:
        """Get formatted origin path string.

        Returns:
            Formatted string like "requests → urllib3 → idna" or just the
            package name for root nodes.
        """
        if not self.origin_path:
            return self.name  # This IS the root
        return " → ".join(self.origin_path + [self.name])


class DependencyTree(BaseModel):
    """Container for the complete dependency tree.

    Provides helper methods for traversing and querying the tree structure.
    Tracks circular references detected during tree resolution (FR8).
    """

    roots: list[DependencyNode] = Field(
        default_factory=list,
        description="Root nodes (direct dependencies)",
    )
    circular_references: list[CircularReference] = Field(
        default_factory=list,
        description="All detected circular references in tree",
    )

    model_config = {"extra": "forbid"}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_circular_dependencies(self) -> bool:
        """True if tree contains any circular dependencies."""
        return len(self.circular_references) > 0

    def get_all_nodes(self) -> list[DependencyNode]:
        """Get all nodes in the tree (flattened).

        Returns:
            List of all nodes including roots and their descendants.
        """
        result: list[DependencyNode] = []
        for root in self.roots:
            result.append(root)
            result.extend(root.get_all_descendants())
        return result

    def get_nodes_at_depth(self, depth: int) -> list[DependencyNode]:
        """Get all nodes at a specific depth.

        Args:
            depth: The depth level to filter by (0 = direct dependencies).

        Returns:
            List of nodes at the specified depth.
        """
        return [node for node in self.get_all_nodes() if node.depth == depth]

    def get_paths_to_package(self, package_name: str) -> list[list[DependencyNode]]:
        """Get all paths to nodes matching the given package name.

        Args:
            package_name: Name of package to find (case-insensitive).

        Returns:
            List of paths, where each path is a list of nodes from root to target.
        """
        normalized = package_name.lower().replace("-", "_").replace(".", "_")
        paths: list[list[DependencyNode]] = []

        def find_paths(
            node: DependencyNode, current_path: list[DependencyNode]
        ) -> None:
            current_path = current_path + [node]
            node_normalized = node.name.lower().replace("-", "_").replace(".", "_")
            if node_normalized == normalized:
                paths.append(current_path)
            for child in node.children:
                find_paths(child, current_path)

        for root in self.roots:
            find_paths(root, [])

        return paths

    @staticmethod
    def format_path_with_versions(path: list[DependencyNode]) -> str:
        """Format a path of nodes with versions.

        Args:
            path: List of DependencyNode from root to target.

        Returns:
            Formatted string like "requests@2.31.0 → urllib3@2.0.0 → idna@3.4"
        """
        if not path:
            return ""
        return " → ".join(f"{node.name}@{node.version}" for node in path)

    def get_nodes_with_problematic_licenses(self) -> list[DependencyNode]:
        """Get all nodes that have problematic licenses.

        Problematic licenses include GPL, AGPL, LGPL, and other copyleft
        licenses that may impose restrictions on derivative works (FR10).

        Returns:
            List of nodes with licenses in the problematic set.
        """
        # Lazy import to avoid circular dependency
        from license_analyzer.analysis.problematic import is_problematic_license

        return [
            node
            for node in self.get_all_nodes()
            if is_problematic_license(node.license)
        ]

    def get_infection_paths(self) -> dict[str, list[list[DependencyNode]]]:
        """Get all paths to packages with problematic licenses.

        Returns a mapping of problematic package names to all paths
        leading to them, allowing users to see how each problematic
        license entered their dependency tree (FR10).

        Returns:
            Dict mapping package name to list of paths leading to it.
        """
        result: dict[str, list[list[DependencyNode]]] = {}
        for node in self.get_nodes_with_problematic_licenses():
            paths = self.get_paths_to_package(node.name)
            if paths:
                result[node.name] = paths
        return result

    def get_introducing_dependency(
        self, node: DependencyNode
    ) -> Optional[DependencyNode]:
        """Get the direct dependency that introduced a transitive package.

        Identifies which top-level (depth=0) dependency is responsible
        for bringing a problematic transitive dependency into the tree.

        Args:
            node: A node in the tree (typically a problematic one).

        Returns:
            The depth-0 dependency that led to this node, or None if
            node is a root or has no origin_path.
        """
        if node.depth == 0:
            return None  # Node IS a direct dependency
        if not node.origin_path:
            return None
        # First element of origin_path is the direct dependency
        direct_name = node.origin_path[0]
        for root in self.roots:
            if root.name == direct_name:
                return root
        return None

    @staticmethod
    def format_infection_path(path: list[DependencyNode]) -> str:
        """Format a path highlighting the problematic package.

        Shows the full path with license information at each step,
        with a warning marker on problematic licenses.

        Args:
            path: List of nodes from root to problematic package.

        Returns:
            Formatted string with license info and warning marker.
        """
        # Lazy import to avoid circular dependency
        from license_analyzer.analysis.problematic import is_problematic_license

        if not path:
            return ""

        parts: list[str] = []
        for node in path:
            license_str = node.license or "Unknown"
            marker = " ⚠️" if is_problematic_license(node.license) else ""
            parts.append(f"{node.name}@{node.version} ({license_str}){marker}")
        return " → ".join(parts)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_count(self) -> int:
        """Total number of packages in the tree."""
        return len(self.get_all_nodes())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def max_depth(self) -> int:
        """Maximum depth in the tree."""
        nodes = self.get_all_nodes()
        return max((n.depth for n in nodes), default=0)

    def get_license_statistics(self) -> LicenseStatistics:
        """Get aggregated license statistics for the tree.

        Categorizes all packages by license type and provides counts,
        percentages, and lists of unique licenses per category.

        Returns:
            LicenseStatistics with breakdown by category.
        """
        # Lazy import to avoid circular dependency
        from license_analyzer.analysis.problematic import (
            LicenseCategory,
            get_license_category,
        )

        nodes = self.get_all_nodes()
        total = len(nodes)

        # Initialize category tracking with typed structure
        counts: dict[LicenseCategory, int] = {
            LicenseCategory.PERMISSIVE: 0,
            LicenseCategory.COPYLEFT: 0,
            LicenseCategory.WEAK_COPYLEFT: 0,
            LicenseCategory.UNKNOWN: 0,
        }
        licenses: dict[LicenseCategory, set[str]] = {
            LicenseCategory.PERMISSIVE: set(),
            LicenseCategory.COPYLEFT: set(),
            LicenseCategory.WEAK_COPYLEFT: set(),
            LicenseCategory.UNKNOWN: set(),
        }

        # Categorize each node
        for node in nodes:
            category = get_license_category(node.license)
            # Map PROPRIETARY to UNKNOWN for statistics
            if category == LicenseCategory.PROPRIETARY:
                category = LicenseCategory.UNKNOWN

            counts[category] += 1
            licenses[category].add(node.license or "Unknown")

        def make_stats(cat: LicenseCategory, name: str) -> CategoryStatistics:
            count = counts[cat]
            license_set = licenses[cat]
            pct = (count / total * 100) if total > 0 else 0.0
            return CategoryStatistics(
                category=name,
                count=count,
                percentage=round(pct, 1),
                licenses=sorted(license_set),
            )

        return LicenseStatistics(
            total_packages=total,
            permissive=make_stats(LicenseCategory.PERMISSIVE, "Permissive"),
            copyleft=make_stats(LicenseCategory.COPYLEFT, "Copyleft"),
            weak_copyleft=make_stats(LicenseCategory.WEAK_COPYLEFT, "Weak Copyleft"),
            unknown=make_stats(LicenseCategory.UNKNOWN, "Unknown"),
        )

    def get_compatibility_issues(self) -> list["CompatibilityResult"]:
        """Get all license compatibility issues in the tree.

        Checks all unique license pairs for compatibility and returns
        those that are incompatible or have unknown compatibility (FR13).

        Returns:
            List of CompatibilityResult for non-compatible license pairs.
        """
        # Lazy import to avoid circular dependency
        from license_analyzer.analysis.compatibility import check_all_compatibility

        # Collect all unique licenses from nodes
        licenses: list[str] = []
        for node in self.get_all_nodes():
            if node.license:
                licenses.append(node.license)

        return check_all_compatibility(licenses)


class CompatibilityMatrix(BaseModel):
    """Matrix representation of license compatibility for visualization.

    Implements FR15: Visual compatibility matrix showing license relationships.
    """

    licenses: list[str] = Field(
        description="Ordered list of unique licenses (row/column headers)"
    )
    matrix: list[list[CompatibilityStatus]] = Field(
        description="2D matrix of compatibility statuses [row][col]"
    )
    issues: list[CompatibilityResult] = Field(
        default_factory=list,
        description="List of incompatible or unknown pairs with details",
    )

    model_config = {"extra": "forbid"}

    @classmethod
    def from_dependency_tree(cls, tree: "DependencyTree") -> "CompatibilityMatrix":
        """Build a compatibility matrix from a dependency tree.

        Args:
            tree: DependencyTree containing packages with licenses.

        Returns:
            CompatibilityMatrix with all unique licenses and their compatibility.
        """
        # Lazy import to avoid circular dependency
        from license_analyzer.analysis.compatibility import check_license_compatibility

        # Collect unique licenses
        license_set: set[str] = set()
        for node in tree.get_all_nodes():
            if node.license:
                license_set.add(node.license)

        # Sort for consistent ordering
        licenses = sorted(license_set)

        # Build the matrix
        matrix: list[list[CompatibilityStatus]] = []
        issues: list[CompatibilityResult] = []
        seen_issues: set[tuple[str, str]] = set()

        for row_license in licenses:
            row: list[CompatibilityStatus] = []
            for col_license in licenses:
                if row_license == col_license:
                    # Same license is always compatible
                    row.append(CompatibilityStatus.COMPATIBLE)
                else:
                    result = check_license_compatibility(row_license, col_license)
                    row.append(result.status)

                    # Track issues (deduplicate symmetric pairs)
                    if result.status != CompatibilityStatus.COMPATIBLE:
                        pair = tuple(sorted([row_license, col_license]))
                        pair_key = (pair[0], pair[1])
                        if pair_key not in seen_issues:
                            seen_issues.add(pair_key)
                            issues.append(result)

            matrix.append(row)

        return cls(licenses=licenses, matrix=matrix, issues=issues)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_issues(self) -> bool:
        """True if any compatibility issues exist."""
        return len(self.issues) > 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def size(self) -> int:
        """Number of unique licenses in the matrix."""
        return len(self.licenses)

    def get_status(self, license_a: str, license_b: str) -> CompatibilityStatus:
        """Get compatibility status between two licenses.

        Args:
            license_a: First license identifier.
            license_b: Second license identifier.

        Returns:
            CompatibilityStatus for the pair.

        Raises:
            ValueError: If either license is not in the matrix.
        """
        try:
            row_idx = self.licenses.index(license_a)
            col_idx = self.licenses.index(license_b)
            return self.matrix[row_idx][col_idx]
        except ValueError as e:
            raise ValueError(f"License not in matrix: {e}") from e
