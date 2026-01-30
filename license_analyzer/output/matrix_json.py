"""JSON matrix formatter for license compatibility visualization."""
import json
from typing import Any

from license_analyzer.models.dependency import (
    CompatibilityMatrix,
    CompatibilityStatus,
)


class MatrixJsonFormatter:
    """Format compatibility matrix as JSON output.

    Provides structured JSON representation of the compatibility matrix
    for programmatic processing and CI/CD integration (FR15).
    """

    def format_matrix(self, matrix: CompatibilityMatrix) -> str:
        """Format compatibility matrix as JSON string.

        Args:
            matrix: The compatibility matrix to format.

        Returns:
            JSON string representation of the matrix.
        """
        output = self._build_output(matrix)
        return json.dumps(output, indent=2)

    def _build_output(self, matrix: CompatibilityMatrix) -> dict[str, Any]:
        """Build the output dictionary structure.

        Args:
            matrix: The compatibility matrix to convert.

        Returns:
            Dictionary ready for JSON serialization.
        """
        # Convert matrix to string statuses
        matrix_data: list[list[str]] = []
        for row in matrix.matrix:
            matrix_data.append([status.value for status in row])

        # Count issues by type
        incompatible_count = sum(
            1 for issue in matrix.issues
            if issue.status == CompatibilityStatus.INCOMPATIBLE
        )
        unknown_count = sum(
            1 for issue in matrix.issues
            if issue.status == CompatibilityStatus.UNKNOWN
        )

        return {
            "licenses": matrix.licenses,
            "matrix": matrix_data,
            "summary": {
                "total_licenses": matrix.size,
                "has_issues": matrix.has_issues,
                "incompatible_pairs": incompatible_count,
                "unknown_pairs": unknown_count,
            },
            "issues": [
                {
                    "license_a": issue.license_a,
                    "license_b": issue.license_b,
                    "status": issue.status.value,
                    "reason": issue.reason,
                }
                for issue in matrix.issues
            ],
        }
