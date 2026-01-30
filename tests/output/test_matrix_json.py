"""Tests for JSON matrix formatter."""

import json

from license_analyzer.models.dependency import (
    CompatibilityMatrix,
    CompatibilityResult,
    CompatibilityStatus,
)
from license_analyzer.output.matrix_json import MatrixJsonFormatter


class TestMatrixJsonFormatter:
    """Tests for MatrixJsonFormatter class."""

    def test_format_empty_matrix(self) -> None:
        """Test formatting empty matrix returns valid JSON."""
        formatter = MatrixJsonFormatter()
        matrix = CompatibilityMatrix(licenses=[], matrix=[], issues=[])

        result = formatter.format_matrix(matrix)
        data = json.loads(result)

        assert data["licenses"] == []
        assert data["matrix"] == []
        assert data["summary"]["total_licenses"] == 0

    def test_format_single_license(self) -> None:
        """Test formatting matrix with single license."""
        formatter = MatrixJsonFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )

        result = formatter.format_matrix(matrix)
        data = json.loads(result)

        assert data["licenses"] == ["MIT"]
        assert data["matrix"] == [["compatible"]]
        assert data["summary"]["total_licenses"] == 1

    def test_format_multiple_licenses(self) -> None:
        """Test formatting matrix with multiple licenses."""
        formatter = MatrixJsonFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT", "Apache-2.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )

        result = formatter.format_matrix(matrix)
        data = json.loads(result)

        assert data["licenses"] == ["MIT", "Apache-2.0"]
        assert len(data["matrix"]) == 2
        assert len(data["matrix"][0]) == 2


class TestMatrixJsonFormatterStatus:
    """Tests for status values in JSON output."""

    def test_compatible_status_value(self) -> None:
        """Test compatible status serializes to 'compatible'."""
        formatter = MatrixJsonFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )

        result = formatter.format_matrix(matrix)
        data = json.loads(result)

        assert data["matrix"][0][0] == "compatible"

    def test_incompatible_status_value(self) -> None:
        """Test incompatible status serializes to 'incompatible'."""
        formatter = MatrixJsonFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT", "GPL-3.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.INCOMPATIBLE],
                [CompatibilityStatus.INCOMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )

        result = formatter.format_matrix(matrix)
        data = json.loads(result)

        assert data["matrix"][0][1] == "incompatible"
        assert data["matrix"][1][0] == "incompatible"

    def test_unknown_status_value(self) -> None:
        """Test unknown status serializes to 'unknown'."""
        formatter = MatrixJsonFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT", "Unknown-License"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.UNKNOWN],
                [CompatibilityStatus.UNKNOWN, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )

        result = formatter.format_matrix(matrix)
        data = json.loads(result)

        assert data["matrix"][0][1] == "unknown"
        assert data["matrix"][1][0] == "unknown"


class TestMatrixJsonFormatterSummary:
    """Tests for summary section in JSON output."""

    def test_summary_includes_total_licenses(self) -> None:
        """Test summary includes total license count."""
        formatter = MatrixJsonFormatter()
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
        data = json.loads(result)

        assert data["summary"]["total_licenses"] == 3

    def test_summary_has_issues_flag(self) -> None:
        """Test summary includes has_issues flag."""
        formatter = MatrixJsonFormatter()

        # No issues
        matrix_clean = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )
        result_clean = formatter.format_matrix(matrix_clean)
        data_clean = json.loads(result_clean)
        assert data_clean["summary"]["has_issues"] is False

        # With issues
        matrix_issues = CompatibilityMatrix(
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
        result_issues = formatter.format_matrix(matrix_issues)
        data_issues = json.loads(result_issues)
        assert data_issues["summary"]["has_issues"] is True

    def test_summary_incompatible_count(self) -> None:
        """Test summary includes incompatible pair count."""
        formatter = MatrixJsonFormatter()
        ok = CompatibilityStatus.COMPATIBLE
        no = CompatibilityStatus.INCOMPATIBLE
        matrix = CompatibilityMatrix(
            licenses=["MIT", "GPL-3.0", "AGPL-3.0"],
            matrix=[
                [ok, no, no],
                [no, ok, ok],
                [no, ok, ok],
            ],
            issues=[
                CompatibilityResult(
                    license_a="MIT",
                    license_b="GPL-3.0",
                    status=CompatibilityStatus.INCOMPATIBLE,
                    reason="Test",
                ),
                CompatibilityResult(
                    license_a="MIT",
                    license_b="AGPL-3.0",
                    status=CompatibilityStatus.INCOMPATIBLE,
                    reason="Test",
                ),
            ],
        )

        result = formatter.format_matrix(matrix)
        data = json.loads(result)

        assert data["summary"]["incompatible_pairs"] == 2

    def test_summary_unknown_count(self) -> None:
        """Test summary includes unknown pair count."""
        formatter = MatrixJsonFormatter()
        ok = CompatibilityStatus.COMPATIBLE
        unk = CompatibilityStatus.UNKNOWN
        matrix = CompatibilityMatrix(
            licenses=["MIT", "Unknown-1", "Unknown-2"],
            matrix=[
                [ok, unk, unk],
                [unk, ok, unk],
                [unk, unk, ok],
            ],
            issues=[
                CompatibilityResult(
                    license_a="MIT",
                    license_b="Unknown-1",
                    status=CompatibilityStatus.UNKNOWN,
                    reason="Unknown",
                ),
                CompatibilityResult(
                    license_a="MIT",
                    license_b="Unknown-2",
                    status=CompatibilityStatus.UNKNOWN,
                    reason="Unknown",
                ),
                CompatibilityResult(
                    license_a="Unknown-1",
                    license_b="Unknown-2",
                    status=CompatibilityStatus.UNKNOWN,
                    reason="Unknown",
                ),
            ],
        )

        result = formatter.format_matrix(matrix)
        data = json.loads(result)

        assert data["summary"]["unknown_pairs"] == 3


class TestMatrixJsonFormatterIssues:
    """Tests for issues section in JSON output."""

    def test_issues_list_empty_when_clean(self) -> None:
        """Test issues list is empty when all compatible."""
        formatter = MatrixJsonFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT", "Apache-2.0"],
            matrix=[
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
                [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.COMPATIBLE],
            ],
            issues=[],
        )

        result = formatter.format_matrix(matrix)
        data = json.loads(result)

        assert data["issues"] == []

    def test_issues_include_details(self) -> None:
        """Test issues include full details."""
        formatter = MatrixJsonFormatter()
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
        data = json.loads(result)

        assert len(data["issues"]) == 1
        issue = data["issues"][0]
        assert issue["license_a"] == "MIT"
        assert issue["license_b"] == "GPL-3.0"
        assert issue["status"] == "incompatible"
        assert issue["reason"] == "Copyleft restriction"

    def test_issues_include_unknown_status(self) -> None:
        """Test issues include unknown status issues."""
        formatter = MatrixJsonFormatter()
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
                    reason="License not recognized",
                )
            ],
        )

        result = formatter.format_matrix(matrix)
        data = json.loads(result)

        assert len(data["issues"]) == 1
        assert data["issues"][0]["status"] == "unknown"


class TestMatrixJsonFormatterValidJson:
    """Tests for JSON validity."""

    def test_output_is_valid_json(self) -> None:
        """Test output is always valid JSON."""
        formatter = MatrixJsonFormatter()
        ok = CompatibilityStatus.COMPATIBLE
        no = CompatibilityStatus.INCOMPATIBLE
        matrix = CompatibilityMatrix(
            licenses=["MIT", "Apache-2.0", "GPL-3.0"],
            matrix=[
                [ok, ok, no],
                [ok, ok, ok],
                [no, ok, ok],
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

        # Should not raise
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_output_is_pretty_printed(self) -> None:
        """Test output is indented for readability."""
        formatter = MatrixJsonFormatter()
        matrix = CompatibilityMatrix(
            licenses=["MIT"],
            matrix=[[CompatibilityStatus.COMPATIBLE]],
            issues=[],
        )

        result = formatter.format_matrix(matrix)

        # Pretty printed JSON has newlines
        assert "\n" in result
        # And indentation
        assert "  " in result
