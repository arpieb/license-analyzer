"""Markdown matrix formatter for license compatibility visualization."""

from license_analyzer.models.dependency import (
    CompatibilityMatrix,
    CompatibilityStatus,
)


class MatrixMarkdownFormatter:
    """Format compatibility matrix as Markdown output.

    Provides formatted Markdown representation of the compatibility matrix
    for documentation and reports (FR15).
    """

    # Status emoji indicators
    STATUS_EMOJI = {
        CompatibilityStatus.COMPATIBLE: ":white_check_mark:",
        CompatibilityStatus.INCOMPATIBLE: ":x:",
        CompatibilityStatus.UNKNOWN: ":question:",
    }

    # Simpler ASCII indicators as fallback
    STATUS_ASCII = {
        CompatibilityStatus.COMPATIBLE: "OK",
        CompatibilityStatus.INCOMPATIBLE: "NO",
        CompatibilityStatus.UNKNOWN: "??",
    }

    def __init__(self, use_emoji: bool = True) -> None:
        """Initialize the formatter.

        Args:
            use_emoji: If True, use emoji indicators. If False, use ASCII.
        """
        self._indicators = self.STATUS_EMOJI if use_emoji else self.STATUS_ASCII

    def format_matrix(self, matrix: CompatibilityMatrix) -> str:
        """Format compatibility matrix as Markdown string.

        Args:
            matrix: The compatibility matrix to format.

        Returns:
            Markdown string representation of the matrix.
        """
        lines: list[str] = []

        # Title
        lines.append("# License Compatibility Matrix")
        lines.append("")

        if matrix.size == 0:
            lines.append("*No licenses found.*")
            return "\n".join(lines)

        # Summary section
        lines.extend(self._format_summary(matrix))
        lines.append("")

        # Matrix table
        lines.extend(self._format_table(matrix))
        lines.append("")

        # Legend
        lines.extend(self._format_legend())
        lines.append("")

        # Issues section
        if matrix.has_issues:
            lines.extend(self._format_issues(matrix))
            lines.append("")

        return "\n".join(lines)

    def _format_summary(self, matrix: CompatibilityMatrix) -> list[str]:
        """Format summary statistics section.

        Args:
            matrix: The compatibility matrix.

        Returns:
            List of Markdown lines for summary.
        """
        incompatible_count = sum(
            1
            for issue in matrix.issues
            if issue.status == CompatibilityStatus.INCOMPATIBLE
        )
        unknown_count = sum(
            1 for issue in matrix.issues if issue.status == CompatibilityStatus.UNKNOWN
        )

        status = "passing" if incompatible_count == 0 else "failing"
        status_color = "green" if incompatible_count == 0 else "red"

        lines = [
            "## Summary",
            "",
            f"![Status](https://img.shields.io/badge/Compatibility-{status}-{status_color})",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Licenses | {matrix.size} |",
            f"| Incompatible Pairs | {incompatible_count} |",
            f"| Unknown Pairs | {unknown_count} |",
        ]
        return lines

    def _format_table(self, matrix: CompatibilityMatrix) -> list[str]:
        """Format the compatibility matrix table.

        Args:
            matrix: The compatibility matrix.

        Returns:
            List of Markdown lines for the table.
        """
        lines = ["## Compatibility Matrix", ""]

        # Header row
        header = "| |"
        for license_name in matrix.licenses:
            header += f" {self._truncate(license_name)} |"
        lines.append(header)

        # Separator row
        separator = "|---|"
        for _ in matrix.licenses:
            separator += "---|"
        lines.append(separator)

        # Data rows
        for i, row_license in enumerate(matrix.licenses):
            row = f"| **{self._truncate(row_license)}** |"
            for status in matrix.matrix[i]:
                indicator = self._indicators[status]
                row += f" {indicator} |"
            lines.append(row)

        return lines

    def _format_legend(self) -> list[str]:
        """Format the legend section.

        Returns:
            List of Markdown lines for the legend.
        """
        return [
            "## Legend",
            "",
            f"- {self._indicators[CompatibilityStatus.COMPATIBLE]} Compatible",
            f"- {self._indicators[CompatibilityStatus.INCOMPATIBLE]} Incompatible",
            f"- {self._indicators[CompatibilityStatus.UNKNOWN]} Unknown",
        ]

    def _format_issues(self, matrix: CompatibilityMatrix) -> list[str]:
        """Format the issues section.

        Args:
            matrix: The compatibility matrix with issues.

        Returns:
            List of Markdown lines for issues.
        """
        lines = [
            "## Compatibility Issues",
            "",
            "| License A | License B | Status | Reason |",
            "|-----------|-----------|--------|--------|",
        ]

        for issue in matrix.issues:
            status_str = (
                "Incompatible"
                if issue.status == CompatibilityStatus.INCOMPATIBLE
                else "Unknown"
            )
            lines.append(
                f"| {issue.license_a} | {issue.license_b} | "
                f"{status_str} | {issue.reason} |"
            )

        return lines

    def _truncate(self, text: str, max_len: int = 12) -> str:
        """Truncate text for display.

        Args:
            text: Text to truncate.
            max_len: Maximum length.

        Returns:
            Truncated text with ellipsis if needed.
        """
        if len(text) <= max_len:
            return text
        return text[: max_len - 2] + ".."
