"""Terminal output formatter using Rich."""
from typing import Optional

from rich.console import Console
from rich.table import Table

from license_analyzer.models.scan import ScanResult


class TerminalFormatter:
    """Format scan results for terminal display using Rich.

    This formatter creates a formatted table display of license scan results
    with color coding for known and unknown licenses.
    """

    def __init__(self, console: Optional[Console] = None) -> None:
        """Initialize the formatter with a Rich console.

        Args:
            console: Optional Rich Console instance. If not provided,
                a new Console will be created.
        """
        self._console = console if console is not None else Console()

    def format_scan_result(self, result: ScanResult) -> None:
        """Format and display scan results as a Rich table.

        Args:
            result: The scan result to display.
        """
        if result.total_packages == 0:
            self._console.print("[yellow]No packages found[/yellow]")
            return

        table = Table(title="License Scan Results")

        table.add_column("Package", style="cyan", no_wrap=True)
        table.add_column("Version", style="magenta")
        table.add_column("License", style="green")

        for pkg in result.packages:
            license_display = pkg.license if pkg.license else "[yellow]Unknown[/yellow]"
            table.add_row(pkg.name, pkg.version, license_display)

        self._console.print(table)
        self._console.print(f"\n[bold]Total packages:[/bold] {result.total_packages}")
        self._console.print(f"[bold]Issues found:[/bold] {result.issues_found}")
