"""Terminal output formatter using Rich."""
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from license_analyzer.constants import LEGAL_DISCLAIMER_SHORT
from license_analyzer.models.scan import ScanResult, Verbosity


class TerminalFormatter:
    """Format scan results for terminal display using Rich.

    This formatter creates a formatted table display of license scan results
    with color coding for known and unknown licenses.
    """

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

    def format_scan_result(self, result: ScanResult) -> None:
        """Format and display scan results as a Rich table.

        Args:
            result: The scan result to display.
        """
        # Quiet mode: show only status line and issues
        if self._verbosity == Verbosity.QUIET:
            self._print_quiet_output(result)
            return

        if result.total_packages == 0:
            # Still show disclaimer even for empty results (FR19)
            self._print_disclaimer()
            self._console.print("[yellow]No packages found[/yellow]")
            return

        # Executive summary (FR18)
        self._print_executive_summary(result)

        # Legal disclaimer after executive summary (FR19 - consistent with markdown)
        self._print_disclaimer()

        table = Table(title="License Scan Results")

        table.add_column("Package", style="cyan", no_wrap=True)
        table.add_column("Version", style="magenta")
        table.add_column("License", style="green")

        # Sort packages alphabetically (consistent with other formatters)
        sorted_packages = sorted(result.packages, key=lambda p: p.name.lower())

        for pkg in sorted_packages:
            license_display = pkg.license if pkg.license else "[yellow]Unknown[/yellow]"
            # Add override marker if package was overridden (FR25)
            if pkg.is_overridden:
                if self._verbosity == Verbosity.VERBOSE and pkg.override_reason:
                    original = pkg.original_license or "Unknown"
                    license_display += (
                        f" [blue][override: was {original}, "
                        f"reason: {pkg.override_reason}][/blue]"
                    )
                else:
                    license_display += " [blue][override][/blue]"
            table.add_row(pkg.name, pkg.version, license_display)

        self._console.print(table)

        # Display policy violations if any (FR23)
        if result.policy_violations:
            self._print_policy_violations(result)

        self._console.print(f"\n[bold]Total packages:[/bold] {result.total_packages}")
        self._console.print(f"[bold]Issues found:[/bold] {result.issues_found}")
        if result.policy_violations:
            self._console.print(
                f"[bold]Policy violations:[/bold] {len(result.policy_violations)}"
            )

    def _print_quiet_output(self, result: ScanResult) -> None:
        """Print minimal output for quiet mode.

        Args:
            result: The scan result to display.
        """
        if result.total_packages == 0:
            self._console.print("[yellow]No packages found[/yellow]")
            return

        # Status line
        if result.has_issues:
            total_issues = result.issues_found + len(result.policy_violations)
            self._console.print(
                f"[red]ISSUES FOUND[/red] - "
                f"{total_issues} issue(s) require attention"
            )
            # List packages with missing licenses
            for pkg in result.packages:
                if not pkg.license:
                    msg = f"  - {pkg.name}@{pkg.version}: "
                    msg += "[yellow]No license found[/yellow]"
                    self._console.print(msg)
            # List policy violations (FR23)
            for violation in result.policy_violations:
                msg = f"  - {violation.package_name}@{violation.package_version}: "
                msg += f"[red]{violation.reason}[/red]"
                self._console.print(msg)
        else:
            self._console.print(
                f"[green]PASS[/green] - All {result.total_packages} packages compatible"
            )

    def _print_disclaimer(self) -> None:
        """Print legal disclaimer panel.

        Displays a prominent disclaimer that this is not legal advice (FR19).
        Uses yellow styling to indicate informational warning.
        """
        panel = Panel(
            LEGAL_DISCLAIMER_SHORT,
            title="[bold yellow]NOT LEGAL ADVICE[/bold yellow]",
            border_style="yellow",
        )
        self._console.print(panel)
        self._console.print("")

    def _print_executive_summary(self, result: ScanResult) -> None:
        """Print executive summary panel.

        Args:
            result: The scan result to summarize.
        """
        licenses_found = result.total_packages - result.issues_found
        total_issues = result.issues_found + len(result.policy_violations)

        # Determine status and color
        if result.has_issues:
            status = "ISSUES FOUND"
            status_color = "red"
            message = f"{total_issues} issue(s) require attention"
        else:
            status = "PASS"
            status_color = "green"
            message = "All packages compatible"

        # Build summary content
        summary_lines = [
            f"Total Packages: {result.total_packages}",
            f"Licenses Found: {licenses_found}",
            f"Issues: {result.issues_found}",
        ]

        # Add policy violations line if any exist
        if result.policy_violations:
            summary_lines.append(f"Policy Violations: {len(result.policy_violations)}")

        # Add ignored packages line if any were ignored (FR24)
        if result.ignored_packages_summary and result.ignored_packages_summary.ignored_count > 0:
            ignored = result.ignored_packages_summary
            if ignored.ignored_names:
                names_str = ", ".join(ignored.ignored_names[:3])
                if len(ignored.ignored_names) > 3:
                    names_str += f", ... (+{len(ignored.ignored_names) - 3} more)"
                summary_lines.append(f"Packages Ignored: {ignored.ignored_count} ({names_str})")
            else:
                summary_lines.append(f"Packages Ignored: {ignored.ignored_count}")

        # Add overrides count if any were applied (FR25)
        overrides_count = sum(1 for pkg in result.packages if pkg.is_overridden)
        if overrides_count > 0:
            summary_lines.append(f"Overrides Applied: {overrides_count}")

        summary_lines.extend([
            "",
            f"Status: [{status_color}]{status}[/{status_color}]",
            f"[{status_color}]{message}[/{status_color}]",
        ])

        panel = Panel(
            "\n".join(summary_lines),
            title="[bold]EXECUTIVE SUMMARY[/bold]",
            border_style=status_color,
        )
        self._console.print(panel)
        self._console.print("")

    def _print_policy_violations(self, result: ScanResult) -> None:
        """Print policy violations section.

        Args:
            result: The scan result with policy violations.
        """
        self._console.print("")
        self._console.print(
            f"[bold red]Policy Violations ({len(result.policy_violations)})[/bold red]"
        )

        for violation in result.policy_violations:
            license_str = violation.detected_license or "Unknown"
            self._console.print(
                f"  [red]![/red] {violation.package_name}@{violation.package_version} "
                f"([yellow]{license_str}[/yellow]): {violation.reason}"
            )
