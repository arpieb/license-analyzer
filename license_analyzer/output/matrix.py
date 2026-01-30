"""Terminal matrix formatter for license compatibility visualization."""
from typing import Optional

from rich.console import Console
from rich.table import Table

from license_analyzer.models.dependency import (
    CompatibilityMatrix,
    CompatibilityStatus,
)
from license_analyzer.models.scan import Verbosity


class MatrixFormatter:
    """Format compatibility matrix for terminal display using Rich.

    Provides visual matrix representation with color-coded cells
    showing license compatibility relationships (FR15).
    """

    # Status indicators and colors
    STATUS_DISPLAY = {
        CompatibilityStatus.COMPATIBLE: ("[green]✓[/green]", "green"),
        CompatibilityStatus.INCOMPATIBLE: ("[red]✗[/red]", "red"),
        CompatibilityStatus.UNKNOWN: ("[yellow]?[/yellow]", "yellow"),
    }

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

    def format_matrix(self, matrix: CompatibilityMatrix) -> None:
        """Format and display compatibility matrix.

        Args:
            matrix: The compatibility matrix to display.
        """
        # Quiet mode: show only incompatibility summary
        if self._verbosity == Verbosity.QUIET:
            self._print_quiet_output(matrix)
            return

        if matrix.size == 0:
            self._console.print("[yellow]No licenses found to display.[/yellow]")
            return

        # Create table
        table = Table(
            title="License Compatibility Matrix",
            show_header=True,
            header_style="bold",
        )

        # Add first column for row headers
        table.add_column("", style="bold")

        # Add column headers (license names)
        for license_name in matrix.licenses:
            table.add_column(
                self._truncate_license(license_name),
                justify="center",
            )

        # Add rows
        for i, row_license in enumerate(matrix.licenses):
            row_data = [self._truncate_license(row_license)]
            for status in matrix.matrix[i]:
                indicator, _ = self.STATUS_DISPLAY[status]
                row_data.append(indicator)
            table.add_row(*row_data)

        # Print table
        self._console.print(table)

        # Print legend
        self._print_legend()

        # Print summary
        self._print_summary(matrix)

        # Print issues if any
        if matrix.has_issues:
            self._print_issues(matrix)

    def _print_quiet_output(self, matrix: CompatibilityMatrix) -> None:
        """Print minimal output for quiet mode.

        Args:
            matrix: The compatibility matrix.
        """
        if matrix.size == 0:
            self._console.print("[yellow]No licenses found[/yellow]")
            return

        incompatible_count = sum(
            1 for issue in matrix.issues
            if issue.status == CompatibilityStatus.INCOMPATIBLE
        )

        if incompatible_count > 0:
            self._console.print(
                f"[red]INCOMPATIBLE[/red] - {incompatible_count} license pair(s)"
            )
            # List incompatible pairs
            for issue in matrix.issues:
                if issue.status == CompatibilityStatus.INCOMPATIBLE:
                    self._console.print(
                        f"  - {issue.license_a} + {issue.license_b}"
                    )
        else:
            self._console.print(
                f"[green]COMPATIBLE[/green] - {matrix.size} licenses checked"
            )

    def _truncate_license(self, license_name: str, max_len: int = 12) -> str:
        """Truncate license name for display.

        Args:
            license_name: Full license name.
            max_len: Maximum length before truncation.

        Returns:
            Truncated license name with ellipsis if needed.
        """
        if len(license_name) <= max_len:
            return license_name
        return license_name[: max_len - 2] + ".."

    def _print_legend(self) -> None:
        """Print color legend for the matrix."""
        self._console.print()
        self._console.print("[bold]Legend:[/bold]")
        self._console.print("  [green]✓[/green] Compatible")
        self._console.print("  [red]✗[/red] Incompatible")
        self._console.print("  [yellow]?[/yellow] Unknown")

    def _print_summary(self, matrix: CompatibilityMatrix) -> None:
        """Print summary statistics.

        Args:
            matrix: The compatibility matrix.
        """
        self._console.print()
        self._console.print(f"[bold]Total licenses:[/bold] {matrix.size}")

        incompatible_count = sum(
            1 for issue in matrix.issues
            if issue.status == CompatibilityStatus.INCOMPATIBLE
        )
        unknown_count = sum(
            1 for issue in matrix.issues
            if issue.status == CompatibilityStatus.UNKNOWN
        )

        if incompatible_count > 0:
            self._console.print(
                f"[bold red]Incompatible pairs:[/bold red] {incompatible_count}"
            )
        else:
            self._console.print("[bold green]Incompatible pairs:[/bold green] 0")

        if unknown_count > 0:
            self._console.print(
                f"[bold yellow]Unknown pairs:[/bold yellow] {unknown_count}"
            )
        else:
            self._console.print("[bold]Unknown pairs:[/bold] 0")

    def _print_issues(self, matrix: CompatibilityMatrix) -> None:
        """Print detailed issues list.

        Args:
            matrix: The compatibility matrix with issues.
        """
        self._console.print()
        self._console.print("[bold]Compatibility Issues:[/bold]")

        for issue in matrix.issues:
            if issue.status == CompatibilityStatus.INCOMPATIBLE:
                self._console.print(
                    f"  [red]✗[/red] {issue.license_a} + {issue.license_b}: "
                    f"{issue.reason}"
                )
            elif issue.status == CompatibilityStatus.UNKNOWN:
                self._console.print(
                    f"  [yellow]?[/yellow] {issue.license_a} + {issue.license_b}: "
                    f"{issue.reason}"
                )
