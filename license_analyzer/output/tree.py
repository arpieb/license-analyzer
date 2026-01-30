"""Tree output formatter for dependency visualization."""
from typing import Optional

from rich.console import Console
from rich.tree import Tree

from license_analyzer.analysis.problematic import (
    LicenseCategory,
    get_license_category,
    is_problematic_license,
)
from license_analyzer.models.dependency import DependencyNode, DependencyTree
from license_analyzer.models.scan import Verbosity


class TreeFormatter:
    """Format dependency tree for terminal display using Rich.

    Provides visual tree representation with color-coded licenses,
    circular dependency markers, and summary statistics.
    """

    # Color mapping for license categories
    LICENSE_COLORS = {
        LicenseCategory.PERMISSIVE: "green",
        LicenseCategory.WEAK_COPYLEFT: "yellow",
        LicenseCategory.COPYLEFT: "red",
        LicenseCategory.PROPRIETARY: "red",
        LicenseCategory.UNKNOWN: "dim yellow",
    }

    # Markers
    CIRCULAR_MARKER = " [cyan]↺[/cyan]"
    WARNING_MARKER = " [red]⚠[/red]"

    def __init__(
        self,
        console: Optional[Console] = None,
        verbosity: Verbosity = Verbosity.NORMAL,
    ) -> None:
        """Initialize the formatter with a Rich console.

        Args:
            console: Optional Rich Console instance. If not provided,
                a new Console will be created.
            verbosity: Output verbosity level.
        """
        self._console = console if console is not None else Console()
        self._verbosity = verbosity

    def format_dependency_tree(self, tree: DependencyTree) -> None:
        """Format and display dependency tree.

        Args:
            tree: The dependency tree to display.
        """
        # Quiet mode: show only summary and problematic licenses
        if self._verbosity == Verbosity.QUIET:
            self._print_quiet_output(tree)
            return

        if not tree.roots:
            self._console.print("[yellow]No dependencies found[/yellow]")
            return

        # Create root tree
        rich_tree = Tree("[bold]Dependencies[/bold]")

        # Add each root package
        for root in tree.roots:
            self._add_node_to_tree(rich_tree, root)

        # Print the tree
        self._console.print(rich_tree)

        # Print summary
        self._print_summary(tree)

    def _print_quiet_output(self, tree: DependencyTree) -> None:
        """Print minimal output for quiet mode.

        Shows only summary statistics and problematic licenses.

        Args:
            tree: The dependency tree to summarize.
        """
        if not tree.roots:
            self._console.print("[yellow]No dependencies found[/yellow]")
            return

        # Summary stats on one line
        problematic = tree.get_nodes_with_problematic_licenses()
        prob_count = len(problematic)

        if prob_count > 0:
            self._console.print(
                f"[red]ISSUES FOUND[/red] - {tree.total_count} packages, "
                f"{prob_count} problematic"
            )
            # List problematic licenses
            for node in problematic:
                path_display = node.get_origin_path_display()
                self._console.print(f"  - {path_display}: [red]{node.license}[/red]")
        else:
            self._console.print(
                f"[green]PASS[/green] - {tree.total_count} packages, "
                f"depth {tree.max_depth}"
            )

    def _add_node_to_tree(self, parent: Tree, node: DependencyNode) -> None:
        """Recursively add a node and its children to the tree.

        Args:
            parent: Parent Rich Tree node.
            node: DependencyNode to add.
        """
        label = self._format_node_label(node)
        branch = parent.add(label)

        # Add circular reference indicators as leaf nodes
        for circ_ref in node.circular_references:
            branch.add(f"[dim]{circ_ref}[/dim]{self.CIRCULAR_MARKER}")

        # Recursively add children
        for child in node.children:
            self._add_node_to_tree(branch, child)

    def _format_node_label(self, node: DependencyNode) -> str:
        """Format a single node's label with colors and markers.

        Args:
            node: DependencyNode to format.

        Returns:
            Formatted Rich markup string.
        """
        # Package name and version
        name_version = f"{node.name}@{node.version}"

        # License with color
        license_str = node.license or "Unknown"
        category = get_license_category(node.license)
        color = self.LICENSE_COLORS.get(category, "white")
        license_display = f"[{color}]{license_str}[/{color}]"

        # Warning marker for problematic licenses
        warning = self.WARNING_MARKER if is_problematic_license(node.license) else ""

        # Circular reference marker if this node has any
        circular = self.CIRCULAR_MARKER if node.has_circular_references else ""

        return f"{name_version} ({license_display}){warning}{circular}"

    def _print_summary(self, tree: DependencyTree) -> None:
        """Print summary statistics after the tree.

        Args:
            tree: The dependency tree to summarize.
        """
        self._console.print()  # Blank line

        # Basic stats
        self._console.print(f"[bold]Total packages:[/bold] {tree.total_count}")
        self._console.print(f"[bold]Max depth:[/bold] {tree.max_depth}")

        # Direct dependencies count
        direct_count = len(tree.roots)
        self._console.print(f"[bold]Direct dependencies:[/bold] {direct_count}")

        # License category breakdown
        self._print_license_categories(tree)

        # Problematic licenses count
        problematic = tree.get_nodes_with_problematic_licenses()
        if problematic:
            self._console.print(
                f"[bold red]Problematic licenses:[/bold red] {len(problematic)}"
            )
            for node in problematic:
                path_display = node.get_origin_path_display()
                self._console.print(f"  [red]⚠ {path_display}[/red] ({node.license})")
        else:
            self._console.print("[bold green]Problematic licenses:[/bold green] 0")

        # Circular dependencies
        if tree.has_circular_dependencies:
            circ_count = len(tree.circular_references)
            self._console.print(
                f"[bold cyan]Circular dependencies:[/bold cyan] {circ_count}"
            )
        else:
            self._console.print("[bold]Circular dependencies:[/bold] 0")

    def _print_license_categories(self, tree: DependencyTree) -> None:
        """Print license category breakdown.

        Args:
            tree: The dependency tree to analyze.
        """
        stats = tree.get_license_statistics()

        self._console.print()
        self._console.print("[bold]License Categories:[/bold]")

        # Category colors
        colors = {
            "permissive": "green",
            "copyleft": "red",
            "weak_copyleft": "yellow",
            "unknown": "dim yellow",
        }

        for name, cat_stats in stats.to_dict().items():
            color = colors.get(name, "white")
            if cat_stats.count > 0:
                self._console.print(
                    f"  [{color}]{cat_stats.category}:[/{color}] "
                    f"{cat_stats.count} ({cat_stats.percentage}%)"
                )
        self._console.print()
