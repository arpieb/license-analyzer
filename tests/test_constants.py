"""Tests for constants module."""
from license_analyzer.constants import EXIT_ERROR, EXIT_ISSUES, EXIT_SUCCESS


class TestExitCodes:
    """Tests for exit code constants."""

    def test_exit_success_is_zero(self) -> None:
        """Test that EXIT_SUCCESS equals 0."""
        assert EXIT_SUCCESS == 0

    def test_exit_issues_is_one(self) -> None:
        """Test that EXIT_ISSUES equals 1."""
        assert EXIT_ISSUES == 1

    def test_exit_error_is_two(self) -> None:
        """Test that EXIT_ERROR equals 2."""
        assert EXIT_ERROR == 2

    def test_exit_codes_are_distinct(self) -> None:
        """Test that all exit codes are distinct values."""
        codes = [EXIT_SUCCESS, EXIT_ISSUES, EXIT_ERROR]
        assert len(codes) == len(set(codes))
