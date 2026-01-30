"""Tests for source conflict detection (FR12)."""
import pytest
from pydantic import ValidationError

from license_analyzer.analysis.conflicts import (
    ConflictDetector,
    SourceConflict,
)


class TestSourceConflict:
    """Tests for SourceConflict model."""

    def test_has_conflict_true_when_multiple_licenses(self) -> None:
        """Test has_conflict is True when sources disagree."""
        conflict = SourceConflict(
            sources={"PyPI": "MIT", "LICENSE": "APACHE-2.0"},
            detected_licenses=["MIT", "APACHE-2.0"],
        )
        assert conflict.has_conflict is True

    def test_has_conflict_false_when_single_license(self) -> None:
        """Test has_conflict is False when sources agree."""
        conflict = SourceConflict(
            sources={"PyPI": "MIT", "LICENSE": "MIT"},
            detected_licenses=["MIT"],
            primary_license="MIT",
        )
        assert conflict.has_conflict is False

    def test_has_conflict_false_when_empty(self) -> None:
        """Test has_conflict is False when no licenses detected."""
        conflict = SourceConflict(
            sources={},
            detected_licenses=[],
        )
        assert conflict.has_conflict is False

    def test_model_forbids_extra_fields(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            SourceConflict(
                sources={},
                detected_licenses=[],
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        conflict = SourceConflict()
        assert conflict.sources == {}
        assert conflict.detected_licenses == []
        assert conflict.primary_license is None
        assert conflict.has_conflict is False

    def test_model_dump_includes_computed_field(self) -> None:
        """Test that has_conflict computed field is included in model_dump()."""
        conflict = SourceConflict(
            sources={"PyPI": "MIT", "LICENSE": "APACHE-2.0"},
            detected_licenses=["APACHE-2.0", "MIT"],
        )
        dumped = conflict.model_dump()

        assert "has_conflict" in dumped
        assert dumped["has_conflict"] is True
        assert dumped["sources"] == {"PyPI": "MIT", "LICENSE": "APACHE-2.0"}
        assert dumped["detected_licenses"] == ["APACHE-2.0", "MIT"]

    def test_model_serialization_roundtrip(self) -> None:
        """Test that model can be serialized and deserialized correctly."""
        original = SourceConflict(
            sources={"PyPI": "MIT"},
            detected_licenses=["MIT"],
            primary_license="MIT",
        )

        # Serialize to dict (excluding computed fields for reconstruction)
        data = original.model_dump(exclude={"has_conflict"})

        # Reconstruct from dict
        reconstructed = SourceConflict(**data)

        assert reconstructed.sources == original.sources
        assert reconstructed.detected_licenses == original.detected_licenses
        assert reconstructed.primary_license == original.primary_license
        assert reconstructed.has_conflict == original.has_conflict


class TestConflictDetector:
    """Tests for ConflictDetector."""

    @pytest.fixture
    def detector(self) -> ConflictDetector:
        """Create detector instance."""
        return ConflictDetector()

    # ==========================================================================
    # AC #1: Conflict detection tests (FR12)
    # ==========================================================================

    def test_detects_pypi_vs_license_conflict(
        self, detector: ConflictDetector
    ) -> None:
        """Test conflict when PyPI says MIT but LICENSE says Apache-2.0 (AC #1)."""
        result = detector.detect(
            pypi_license="MIT",
            github_license="Apache-2.0",
        )

        assert result.has_conflict is True
        assert "PyPI" in result.sources
        assert "LICENSE" in result.sources
        assert result.sources["PyPI"] == "MIT"
        assert result.sources["LICENSE"] == "APACHE-2.0"
        assert len(result.detected_licenses) == 2
        assert result.primary_license is None

    def test_detects_three_way_conflict(
        self, detector: ConflictDetector
    ) -> None:
        """Test conflict with three different licenses."""
        result = detector.detect(
            pypi_license="MIT",
            github_license="Apache-2.0",
            readme_license="GPL-3.0",
        )

        assert result.has_conflict is True
        assert len(result.sources) == 3
        assert len(result.detected_licenses) == 3
        assert result.primary_license is None

    def test_detects_partial_conflict(
        self, detector: ConflictDetector
    ) -> None:
        """Test conflict when two sources agree but one disagrees."""
        result = detector.detect(
            pypi_license="MIT",
            github_license="MIT",
            readme_license="Apache-2.0",
        )

        assert result.has_conflict is True
        assert len(result.detected_licenses) == 2
        assert "MIT" in result.detected_licenses
        assert "APACHE-2.0" in result.detected_licenses

    # ==========================================================================
    # AC #2: No conflict tests
    # ==========================================================================

    def test_no_conflict_when_sources_agree(
        self, detector: ConflictDetector
    ) -> None:
        """Test no conflict when all sources agree (AC #2)."""
        result = detector.detect(
            pypi_license="MIT",
            github_license="MIT",
        )

        assert result.has_conflict is False
        assert result.primary_license == "MIT"
        assert len(result.detected_licenses) == 1

    def test_no_conflict_all_three_sources_agree(
        self, detector: ConflictDetector
    ) -> None:
        """Test no conflict when all three sources agree."""
        result = detector.detect(
            pypi_license="Apache-2.0",
            github_license="Apache-2.0",
            readme_license="Apache-2.0",
        )

        assert result.has_conflict is False
        assert result.primary_license == "APACHE-2.0"
        assert len(result.sources) == 3

    def test_no_conflict_single_source(
        self, detector: ConflictDetector
    ) -> None:
        """Test no conflict with single source."""
        result = detector.detect(pypi_license="MIT")

        assert result.has_conflict is False
        assert result.primary_license == "MIT"
        assert len(result.sources) == 1
        assert result.sources["PyPI"] == "MIT"

    def test_no_sources_returns_empty_result(
        self, detector: ConflictDetector
    ) -> None:
        """Test empty result when no sources provided."""
        result = detector.detect()

        assert result.has_conflict is False
        assert result.sources == {}
        assert result.detected_licenses == []
        assert result.primary_license is None

    # ==========================================================================
    # Case-insensitive comparison tests
    # ==========================================================================

    def test_case_insensitive_comparison_detects_agreement(
        self, detector: ConflictDetector
    ) -> None:
        """Test that 'mit' and 'MIT' are treated as the same license."""
        result = detector.detect(
            pypi_license="mit",
            github_license="MIT",
        )

        assert result.has_conflict is False
        assert result.primary_license == "MIT"
        # Both normalized to uppercase
        assert result.sources["PyPI"] == "MIT"
        assert result.sources["LICENSE"] == "MIT"

    def test_case_insensitive_comparison_mixed_case(
        self, detector: ConflictDetector
    ) -> None:
        """Test mixed case licenses are normalized."""
        result = detector.detect(
            pypi_license="Apache-2.0",
            github_license="apache-2.0",
            readme_license="APACHE-2.0",
        )

        assert result.has_conflict is False
        assert len(result.detected_licenses) == 1

    # ==========================================================================
    # Empty string and whitespace handling tests
    # ==========================================================================

    def test_empty_string_treated_as_no_source(
        self, detector: ConflictDetector
    ) -> None:
        """Test that empty string is treated as no source."""
        result = detector.detect(
            pypi_license="MIT",
            github_license="",
        )

        assert result.has_conflict is False
        assert "PyPI" in result.sources
        assert "LICENSE" not in result.sources
        assert len(result.sources) == 1

    def test_whitespace_only_treated_as_no_source(
        self, detector: ConflictDetector
    ) -> None:
        """Test that whitespace-only string is treated as no source."""
        result = detector.detect(
            pypi_license="MIT",
            github_license="   ",
            readme_license="\t\n",
        )

        assert result.has_conflict is False
        assert len(result.sources) == 1
        assert "PyPI" in result.sources

    def test_none_values_treated_as_no_source(
        self, detector: ConflictDetector
    ) -> None:
        """Test that None values are treated as no source."""
        result = detector.detect(
            pypi_license="MIT",
            github_license=None,
            readme_license=None,
        )

        assert result.has_conflict is False
        assert len(result.sources) == 1

    # ==========================================================================
    # Edge cases
    # ==========================================================================

    def test_license_with_leading_trailing_whitespace(
        self, detector: ConflictDetector
    ) -> None:
        """Test that whitespace is stripped from license names."""
        result = detector.detect(
            pypi_license="  MIT  ",
            github_license="MIT",
        )

        assert result.has_conflict is False
        assert result.sources["PyPI"] == "MIT"

    def test_sources_dict_contains_all_valid_sources(
        self, detector: ConflictDetector
    ) -> None:
        """Test that sources dict includes all provided valid sources."""
        result = detector.detect(
            pypi_license="MIT",
            github_license="MIT",
            readme_license="MIT",
        )

        assert "PyPI" in result.sources
        assert "LICENSE" in result.sources
        assert "README" in result.sources


class TestConflictDetectorConsistencyWithConfidenceScorer:
    """Tests verifying ConflictDetector is consistent with ConfidenceScorer."""

    @pytest.fixture
    def detector(self) -> ConflictDetector:
        """Create detector instance."""
        return ConflictDetector()

    def test_conflict_detection_matches_confidence_scorer_behavior(
        self, detector: ConflictDetector
    ) -> None:
        """Verify ConflictDetector detects same conflicts as ConfidenceScorer.

        ConfidenceScorer returns UNCERTAIN when sources disagree.
        ConflictDetector should return has_conflict=True for same inputs.
        """
        from license_analyzer.analysis.confidence import (
            ConfidenceLevel,
            ConfidenceScorer,
        )

        scorer = ConfidenceScorer()

        # Test with same inputs
        conflict_result = detector.detect(
            pypi_license="MIT",
            github_license="Apache-2.0",
        )
        confidence_result = scorer.calculate(
            pypi_license="MIT",
            github_license="Apache-2.0",
        )

        # ConflictDetector should flag this as a conflict
        assert conflict_result.has_conflict is True
        # ConfidenceScorer should return UNCERTAIN for conflicts
        assert confidence_result.level == ConfidenceLevel.UNCERTAIN
        # Both should identify the same sources
        assert conflict_result.sources["PyPI"] == "MIT"
        assert conflict_result.sources["LICENSE"] == "APACHE-2.0"

    def test_agreement_detection_matches_confidence_scorer_behavior(
        self, detector: ConflictDetector
    ) -> None:
        """Verify ConflictDetector agrees with ConfidenceScorer on no-conflict.

        ConfidenceScorer returns HIGH when multiple sources agree.
        ConflictDetector should return has_conflict=False for same inputs.
        """
        from license_analyzer.analysis.confidence import (
            ConfidenceLevel,
            ConfidenceScorer,
        )

        scorer = ConfidenceScorer()

        # Test with same inputs
        conflict_result = detector.detect(
            pypi_license="MIT",
            github_license="MIT",
        )
        confidence_result = scorer.calculate(
            pypi_license="MIT",
            github_license="MIT",
        )

        # ConflictDetector should not flag this as a conflict
        assert conflict_result.has_conflict is False
        assert conflict_result.primary_license == "MIT"
        # ConfidenceScorer should return HIGH for agreement
        assert confidence_result.level == ConfidenceLevel.HIGH
