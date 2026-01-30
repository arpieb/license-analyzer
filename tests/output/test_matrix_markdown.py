"""Tests for Markdown matrix formatter."""

from license_analyzer.models.dependency import (
    CompatibilityMatrix,
    CompatibilityResult,
    CompatibilityStatus,
)
from license_analyzer.output.matrix_markdown import MatrixMarkdownFormatter


class TestMatrixMarkdownFormatter:
    """Tests for MatrixMarkdownFormatter class."""

    def test_format_empty_matrix(self) -> None:
        """Test formatting empty matrix shows message."""
        formatter = MatrixMarkdownFormatter()
        matrix = CompatibilityMatrix(licenses=[], matrix=[], issues=[])

        result = formatter.format_matrix(matrix)

        assert "# License Compatibility Matrix" in result
        assert "No licenses found" in result

    def test_format_single_license(self) -> None:
        """Test formatting matrix with single license."""
        formatter = MatrixMarkdownFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert "MIT" in result
        assert "## Compatibility Matrix" in result

    def test_format_multiple_licenses(self) -> None:
        """Test formatting matrix with multiple licenses."""
        formatter = MatrixMarkdownFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT", "Apache-2.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert "MIT" in result
        assert "Apache-2.0" in result


class TestMatrixMarkdownFormatterEmoji:
    """Tests for emoji indicators."""

    def test_compatible_shows_checkmark_emoji(self) -> None:
        """Test compatible status shows checkmark emoji."""
        formatter = MatrixMarkdownFormatter(use_emoji=True)
        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert ":white_check_mark:" in result

    def test_incompatible_shows_x_emoji(self) -> None:
        """Test incompatible status shows X emoji."""
        formatter = MatrixMarkdownFormatter(use_emoji=True)
        matrix = CompatibilityMatrix(
            licenses=["MIT", "GPL-3.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.INCOMPATIBLE],
                [CompatibilityStatus.INCOMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert ":x:" in result

    def test_unknown_shows_question_emoji(self) -> None:
        """Test unknown status shows question emoji."""
        formatter = MatrixMarkdownFormatter(use_emoji=True)
        matrix = CompatibilityMatrix(
            licenses=["MIT", "Unknown"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.UNKNOWN],
                [CompatibilityStatus.UNKNOWN, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert ":question:" in result


class TestMatrixMarkdownFormatterAscii:
    """Tests for ASCII fallback indicators."""

    def test_ascii_compatible_shows_ok(self) -> None:
        """Test ASCII mode shows OK for compatible."""
        formatter = MatrixMarkdownFormatter(use_emoji=False)
        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert "OK" in result
        assert ":white_check_mark:" not in result

    def test_ascii_incompatible_shows_no(self) -> None:
        """Test ASCII mode shows NO for incompatible."""
        formatter = MatrixMarkdownFormatter(use_emoji=False)
        matrix = CompatibilityMatrix(
            licenses=["MIT", "GPL-3.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.INCOMPATIBLE],
                [CompatibilityStatus.INCOMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert "NO" in result
        assert ":x:" not in result

    def test_ascii_unknown_shows_question_marks(self) -> None:
        """Test ASCII mode shows ?? for unknown."""
        formatter = MatrixMarkdownFormatter(use_emoji=False)
        matrix = CompatibilityMatrix(
            licenses=["MIT", "Unknown"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.UNKNOWN],
                [CompatibilityStatus.UNKNOWN, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert "??" in result
        assert ":question:" not in result


class TestMatrixMarkdownFormatterSummary:
    """Tests for summary section."""

    def test_summary_section_present(self) -> None:
        """Test summary section is present."""
        formatter = MatrixMarkdownFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert "## Summary" in result

    def test_summary_shows_total_licenses(self) -> None:
        """Test summary shows total license count."""
        formatter = MatrixMarkdownFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT", "Apache-2.0", "BSD-3-Clause"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE] * 3,
                [CompatibilityStatus.COMPATIBLE] * 3,
                [CompatibilityStatus.COMPATIBLE] * 3,
            ],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert "Total Licenses" in result
        assert "3" in result

    def test_summary_shows_incompatible_count(self) -> None:
        """Test summary shows incompatible pair count."""
        formatter = MatrixMarkdownFormatter()
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

        result = formatter.format_matrix(matrix)

        assert "Incompatible Pairs" in result
        assert "1" in result

    def test_summary_shows_unknown_count(self) -> None:
        """Test summary shows unknown pair count."""
        formatter = MatrixMarkdownFormatter()
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
                    reason="Unknown",
                )
            ],
        )

        result = formatter.format_matrix(matrix)

        assert "Unknown Pairs" in result

    def test_summary_has_status_badge(self) -> None:
        """Test summary includes status badge."""
        formatter = MatrixMarkdownFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert "![Status]" in result
        assert "shields.io" in result


class TestMatrixMarkdownFormatterLegend:
    """Tests for legend section."""

    def test_legend_section_present(self) -> None:
        """Test legend section is present."""
        formatter = MatrixMarkdownFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert "## Legend" in result
        assert "Compatible" in result
        assert "Incompatible" in result
        assert "Unknown" in result


class TestMatrixMarkdownFormatterTable:
    """Tests for table formatting."""

    def test_table_has_headers(self) -> None:
        """Test table has header row."""
        formatter = MatrixMarkdownFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT", "Apache-2.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        # Check for table structure
        assert "| |" in result  # Header starts with empty cell
        assert "|---|" in result  # Separator row

    def test_table_has_row_headers(self) -> None:
        """Test table has bold row headers."""
        formatter = MatrixMarkdownFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert "**MIT**" in result


class TestMatrixMarkdownFormatterIssues:
    """Tests for issues section."""

    def test_issues_section_present_when_issues(self) -> None:
        """Test issues section is present when there are issues."""
        formatter = MatrixMarkdownFormatter()
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

        result = formatter.format_matrix(matrix)

        assert "## Compatibility Issues" in result

    def test_issues_section_absent_when_clean(self) -> None:
        """Test issues section is absent when all compatible."""
        formatter = MatrixMarkdownFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT", "Apache-2.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert "## Compatibility Issues" not in result

    def test_issues_table_includes_details(self) -> None:
        """Test issues table includes license names and reasons."""
        formatter = MatrixMarkdownFormatter()
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

        result = formatter.format_matrix(matrix)

        assert "MIT" in result
        assert "GPL-3.0" in result
        assert "Incompatible" in result
        assert "Copyleft restriction" in result


class TestMatrixMarkdownFormatterTruncation:
    """Tests for license name truncation."""

    def test_long_license_name_truncated(self) -> None:
        """Test long license names are truncated."""
        formatter = MatrixMarkdownFormatter()
        long_license = "Very-Long-License-Name-That-Exceeds-Limit"
        matrix = CompatibilityMatrix(
            licenses=[long_license],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        # Should be truncated with ..
        assert ".." in result
        # Full name should not appear in table headers (before issues section)
        if "## Compatibility Issues" in result:
            before_issues = result.split("## Compatibility Issues")[0]
            assert long_license not in before_issues


class TestMatrixMarkdownFormatterDefaultEmoji:
    """Tests for default emoji setting."""

    def test_default_uses_emoji(self) -> None:
        """Test default formatter uses emoji."""
        formatter = MatrixMarkdownFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        assert ":white_check_mark:" in result
