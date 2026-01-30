"""Tests for constants module."""
from license_analyzer.constants import LEGAL_DISCLAIMER, LEGAL_DISCLAIMER_SHORT


class TestLegalDisclaimer:
    """Tests for LEGAL_DISCLAIMER constant."""

    def test_disclaimer_exists(self) -> None:
        """Test LEGAL_DISCLAIMER constant exists."""
        assert LEGAL_DISCLAIMER is not None

    def test_disclaimer_is_non_empty(self) -> None:
        """Test LEGAL_DISCLAIMER is a non-empty string."""
        assert isinstance(LEGAL_DISCLAIMER, str)
        assert len(LEGAL_DISCLAIMER) > 0

    def test_disclaimer_contains_not_legal_advice(self) -> None:
        """Test LEGAL_DISCLAIMER contains 'not' and 'legal advice'."""
        disclaimer_lower = LEGAL_DISCLAIMER.lower()
        assert "not" in disclaimer_lower
        assert "legal advice" in disclaimer_lower

    def test_disclaimer_contains_informational(self) -> None:
        """Test LEGAL_DISCLAIMER contains 'informational'."""
        assert "informational" in LEGAL_DISCLAIMER.lower()


class TestLegalDisclaimerShort:
    """Tests for LEGAL_DISCLAIMER_SHORT constant (terminal version)."""

    def test_short_disclaimer_exists(self) -> None:
        """Test LEGAL_DISCLAIMER_SHORT constant exists."""
        assert LEGAL_DISCLAIMER_SHORT is not None

    def test_short_disclaimer_is_non_empty(self) -> None:
        """Test LEGAL_DISCLAIMER_SHORT is a non-empty string."""
        assert isinstance(LEGAL_DISCLAIMER_SHORT, str)
        assert len(LEGAL_DISCLAIMER_SHORT) > 0

    def test_short_disclaimer_is_shorter(self) -> None:
        """Test LEGAL_DISCLAIMER_SHORT is shorter than full version."""
        assert len(LEGAL_DISCLAIMER_SHORT) < len(LEGAL_DISCLAIMER)

    def test_short_disclaimer_contains_key_phrases(self) -> None:
        """Test LEGAL_DISCLAIMER_SHORT contains key phrases."""
        disclaimer_lower = LEGAL_DISCLAIMER_SHORT.lower()
        assert "informational" in disclaimer_lower
        assert "not" in disclaimer_lower
        assert "legal advice" in disclaimer_lower
