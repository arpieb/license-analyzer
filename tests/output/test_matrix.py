"""Tests for terminal matrix formatter."""

from io import StringIO

from rich.console import Console

from license_analyzer.models.dependency import (
    CompatibilityMatrix,
    CompatibilityResult,
    CompatibilityStatus,
)
from license_analyzer.output.matrix import MatrixFormatter


class TestMatrixFormatter:
    """Tests for MatrixFormatter class."""

    def test_format_empty_matrix(self) -> None:
        """Test formatting empty matrix shows message."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = MatrixFormatter(console=console)

        matrix = CompatibilityMatrix(licenses=[], matrix=[], issues=[])
        formatter.format_matrix(matrix)

        result = output.getvalue()
        assert "No licenses found" in result

    def test_format_single_license(self) -> None:
        """Test formatting matrix with single license."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = MatrixFormatter(console=console)

        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )
        formatter.format_matrix(matrix)

        result = output.getvalue()
        assert "MIT" in result
        # Rich may split title across lines, so check for key words
        assert "Compatibility" in result
        assert "Matrix" in result

    def test_format_multiple_licenses(self) -> None:
        """Test formatting matrix with multiple licenses."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = MatrixFormatter(console=console)

        matrix = CompatibilityMatrix(
            licenses=["MIT", "Apache-2.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )
        formatter.format_matrix(matrix)

        result = output.getvalue()
        assert "MIT" in result
        assert "Apache-2.0" in result


class TestMatrixFormatterStatusDisplay:
    """Tests for status display in terminal output."""

    def test_compatible_shows_checkmark(self) -> None:
        """Test compatible status shows checkmark."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = MatrixFormatter(console=console)

        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )
        formatter.format_matrix(matrix)

        result = output.getvalue()
        # Rich uses ANSI codes, so we check for the character
        assert "\u2713" in result  # checkmark

    def test_incompatible_shows_x(self) -> None:
        """Test incompatible status shows X."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = MatrixFormatter(console=console)

        matrix = CompatibilityMatrix(
            licenses=["MIT", "GPL-3.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.INCOMPATIBLE],
                [CompatibilityStatus.INCOMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[
                CompatibilityResult(
                    license_a="MIT",
                    license_b="GPL-3.0",
                    status=CompatibilityStatus.INCOMPATIBLE,
                    reason="Test incompatibility",
                )
            ],
        )
        formatter.format_matrix(matrix)

        result = output.getvalue()
        assert "\u2717" in result  # X mark

    def test_unknown_shows_question(self) -> None:
        """Test unknown status shows question mark."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = MatrixFormatter(console=console)

        matrix = CompatibilityMatrix(
            licenses=["MIT", "Unknown-License"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.UNKNOWN],
                [CompatibilityStatus.UNKNOWN, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[
                CompatibilityResult(
                    license_a="MIT",
                    license_b="Unknown-License",
                    status=CompatibilityStatus.UNKNOWN,
                    reason="Unknown license",
                )
            ],
        )
        formatter.format_matrix(matrix)

        result = output.getvalue()
        assert "?" in result


class TestMatrixFormatterLegend:
    """Tests for legend display."""

    def test_legend_displayed(self) -> None:
        """Test legend is displayed."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = MatrixFormatter(console=console)

        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )
        formatter.format_matrix(matrix)

        result = output.getvalue()
        assert "Legend" in result
        assert "Compatible" in result
        assert "Incompatible" in result
        assert "Unknown" in result


class TestMatrixFormatterSummary:
    """Tests for summary display."""

    def test_summary_shows_total(self) -> None:
        """Test summary shows total licenses."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = MatrixFormatter(console=console)

        matrix = CompatibilityMatrix(
            licenses=["MIT", "Apache-2.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )
        formatter.format_matrix(matrix)

        result = output.getvalue()
        assert "Total licenses" in result
        assert "2" in result

    def test_summary_shows_incompatible_count(self) -> None:
        """Test summary shows incompatible pair count."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = MatrixFormatter(console=console)

        matrix = CompatibilityMatrix(
            licenses=["MIT", "GPL-3.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.INCOMPATIBLE],
                [CompatibilityStatus.INCOMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[
                CompatibilityResult(
                    license_a="MIT",
                    license_b="GPL-3.0",
                    status=CompatibilityStatus.INCOMPATIBLE,
                    reason="Test",
                )
            ],
        )
        formatter.format_matrix(matrix)

        result = output.getvalue()
        assert "Incompatible pairs" in result


class TestMatrixFormatterIssues:
    """Tests for issues display."""

    def test_issues_displayed_when_present(self) -> None:
        """Test issues are displayed when there are incompatibilities."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = MatrixFormatter(console=console)

        matrix = CompatibilityMatrix(
            licenses=["MIT", "GPL-3.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.INCOMPATIBLE],
                [CompatibilityStatus.INCOMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[
                CompatibilityResult(
                    license_a="MIT",
                    license_b="GPL-3.0",
                    status=CompatibilityStatus.INCOMPATIBLE,
                    reason="Copyleft restriction",
                )
            ],
        )
        formatter.format_matrix(matrix)

        result = output.getvalue()
        assert "Compatibility Issues" in result
        assert "MIT" in result
        assert "GPL-3.0" in result

    def test_no_issues_section_when_clean(self) -> None:
        """Test no issues section when all compatible."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = MatrixFormatter(console=console)

        matrix = CompatibilityMatrix(
            licenses=["MIT", "Apache-2.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )
        formatter.format_matrix(matrix)

        result = output.getvalue()
        # Issues section should not appear
        assert "Compatibility Issues" not in result


class TestMatrixFormatterTruncation:
    """Tests for license name truncation."""

    def test_long_license_name_truncated(self) -> None:
        """Test long license names are truncated."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        formatter = MatrixFormatter(console=console)

        long_license = "Very-Long-License-Name-That-Exceeds-Limit"
        matrix = CompatibilityMatrix(
            licenses=[long_license],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )
        formatter.format_matrix(matrix)

        result = output.getvalue()
        # Should be truncated with ..
        assert ".." in result


class TestMatrixFormatterConsoleDefault:
    """Tests for console initialization."""

    def test_default_console_created(self) -> None:
        """Test formatter creates default console if none provided."""
        formatter = MatrixFormatter()
        # Should not raise - verifies internal console exists
        assert formatter._console is not None
