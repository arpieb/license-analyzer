"""Tests for confidence level scoring."""
import pytest
from pydantic import ValidationError

from license_analyzer.analysis.confidence import (
    ConfidenceLevel,
    ConfidenceResult,
    ConfidenceScorer,
)
from license_analyzer.analysis.modified import ModifiedLicenseResult


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_confidence_level_values(self) -> None:
        """Test that all confidence levels have expected values."""
        assert ConfidenceLevel.HIGH == "HIGH"
        assert ConfidenceLevel.MEDIUM == "MEDIUM"
        assert ConfidenceLevel.UNCERTAIN == "UNCERTAIN"

    def test_confidence_level_is_string_enum(self) -> None:
        """Test that ConfidenceLevel is JSON serializable."""
        # str, Enum makes it JSON serializable
        assert isinstance(ConfidenceLevel.HIGH.value, str)
        assert ConfidenceLevel.HIGH.value == "HIGH"


class TestConfidenceResult:
    """Tests for ConfidenceResult model."""

    def test_create_result_with_required_fields(self) -> None:
        """Test creating a result with required fields."""
        result = ConfidenceResult(
            level=ConfidenceLevel.HIGH,
            reasons=["Test reason"],
            sources_used=["PyPI", "LICENSE"],
        )
        assert result.level == ConfidenceLevel.HIGH
        assert result.reasons == ["Test reason"]
        assert result.sources_used == ["PyPI", "LICENSE"]
        assert result.no_license_found is False

    def test_create_result_with_no_license_found(self) -> None:
        """Test creating a result with no_license_found flag."""
        result = ConfidenceResult(
            level=ConfidenceLevel.UNCERTAIN,
            reasons=["No license found"],
            sources_used=[],
            no_license_found=True,
        )
        assert result.no_license_found is True

    def test_result_forbids_extra_fields(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ConfidenceResult(
                level=ConfidenceLevel.HIGH,
                reasons=[],
                sources_used=[],
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_result_default_values(self) -> None:
        """Test default values for optional fields."""
        result = ConfidenceResult(level=ConfidenceLevel.MEDIUM)
        assert result.reasons == []
        assert result.sources_used == []
        assert result.no_license_found is False


class TestConfidenceScorer:
    """Tests for ConfidenceScorer."""

    @pytest.fixture
    def scorer(self) -> ConfidenceScorer:
        """Create scorer instance."""
        return ConfidenceScorer()

    # ==========================================================================
    # AC #1: HIGH confidence tests
    # ==========================================================================

    def test_high_confidence_multiple_agreeing_sources_pypi_license(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test HIGH when PyPI and LICENSE file agree."""
        result = scorer.calculate(
            pypi_license="MIT",
            github_license="MIT",
        )

        assert result.level == ConfidenceLevel.HIGH
        assert "PyPI" in result.sources_used
        assert "LICENSE" in result.sources_used
        assert "Multiple sources agree" in result.reasons[0]

    def test_high_confidence_multiple_agreeing_sources_all_three(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test HIGH when all three sources agree."""
        result = scorer.calculate(
            pypi_license="Apache-2.0",
            github_license="Apache-2.0",
            readme_license="Apache-2.0",
        )

        assert result.level == ConfidenceLevel.HIGH
        assert len(result.sources_used) == 3

    def test_high_confidence_pypi_readme_agree(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test HIGH when PyPI and README agree."""
        result = scorer.calculate(
            pypi_license="BSD-3-Clause",
            readme_license="BSD-3-Clause",
        )

        assert result.level == ConfidenceLevel.HIGH
        assert "PyPI" in result.sources_used
        assert "README" in result.sources_used

    def test_high_confidence_unmodified_license_file(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test HIGH when LICENSE file is unmodified (AC #1)."""
        mod_result = ModifiedLicenseResult(
            is_modified=False,
            closest_license="MIT",
            similarity_score=0.95,
            modifications=[],
        )

        result = scorer.calculate(
            github_license="MIT",
            modification_result=mod_result,
        )

        assert result.level == ConfidenceLevel.HIGH
        assert "LICENSE file matches known template exactly" in result.reasons[0]

    def test_high_confidence_license_file_without_modification_check(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test HIGH when LICENSE file identified without modification check."""
        result = scorer.calculate(github_license="GPL-3.0")

        assert result.level == ConfidenceLevel.HIGH
        assert "LICENSE" in result.sources_used

    # ==========================================================================
    # AC #2: MEDIUM confidence tests
    # ==========================================================================

    def test_medium_confidence_pypi_only(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test MEDIUM when only PyPI metadata available (AC #2)."""
        result = scorer.calculate(pypi_license="MIT")

        assert result.level == ConfidenceLevel.MEDIUM
        assert "PyPI" in result.sources_used
        assert len(result.sources_used) == 1
        assert "PyPI metadata only" in result.reasons[0]

    def test_medium_confidence_modified_license_identifiable(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test MEDIUM when LICENSE file modified but identifiable."""
        mod_result = ModifiedLicenseResult(
            is_modified=True,
            closest_license="MIT",
            similarity_score=0.75,
            modifications=["Additional restriction detected"],
        )

        result = scorer.calculate(
            github_license="MIT",
            modification_result=mod_result,
        )

        assert result.level == ConfidenceLevel.MEDIUM
        assert "modified" in result.reasons[0].lower()
        assert "75%" in result.reasons[0]

    def test_medium_confidence_modified_at_threshold(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test MEDIUM when LICENSE file at exact modification threshold."""
        mod_result = ModifiedLicenseResult(
            is_modified=True,
            closest_license="Apache-2.0",
            similarity_score=0.50,  # Exactly at threshold
            modifications=[],
        )

        result = scorer.calculate(
            github_license="Apache-2.0",
            modification_result=mod_result,
        )

        assert result.level == ConfidenceLevel.MEDIUM

    # ==========================================================================
    # AC #3: UNCERTAIN confidence tests - conflicts and README only
    # ==========================================================================

    def test_uncertain_confidence_conflicting_sources(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test UNCERTAIN when sources conflict (AC #3)."""
        result = scorer.calculate(
            pypi_license="MIT",
            github_license="Apache-2.0",
        )

        assert result.level == ConfidenceLevel.UNCERTAIN
        assert any("disagree" in r.lower() for r in result.reasons)
        assert "PyPI" in result.sources_used
        assert "LICENSE" in result.sources_used

    def test_uncertain_confidence_three_way_conflict(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test UNCERTAIN with three different licenses."""
        result = scorer.calculate(
            pypi_license="MIT",
            github_license="Apache-2.0",
            readme_license="GPL-3.0",
        )

        assert result.level == ConfidenceLevel.UNCERTAIN
        assert len(result.sources_used) == 3

    def test_uncertain_confidence_readme_only(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test UNCERTAIN when only README mention available (AC #3)."""
        result = scorer.calculate(readme_license="MIT")

        assert result.level == ConfidenceLevel.UNCERTAIN
        assert "README" in result.sources_used
        assert len(result.sources_used) == 1
        assert "README mention only" in result.reasons[0]

    def test_uncertain_confidence_heavily_modified_license(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test UNCERTAIN when LICENSE file heavily modified (AC #3)."""
        mod_result = ModifiedLicenseResult(
            is_modified=True,
            closest_license=None,
            similarity_score=0.30,
            modifications=["Could not identify license type"],
        )

        result = scorer.calculate(
            github_license="UNKNOWN",
            modification_result=mod_result,
        )

        assert result.level == ConfidenceLevel.UNCERTAIN
        assert "heavily modified" in result.reasons[0].lower()

    def test_uncertain_confidence_just_below_threshold(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test UNCERTAIN when just below modification threshold."""
        mod_result = ModifiedLicenseResult(
            is_modified=True,
            closest_license="MIT",
            similarity_score=0.49,  # Just below 0.50 threshold
            modifications=[],
        )

        result = scorer.calculate(
            github_license="MIT",
            modification_result=mod_result,
        )

        assert result.level == ConfidenceLevel.UNCERTAIN

    # ==========================================================================
    # AC #4: No license found tests (FR14)
    # ==========================================================================

    def test_uncertain_no_license_found(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test UNCERTAIN when no license found from any source (FR14)."""
        result = scorer.calculate()

        assert result.level == ConfidenceLevel.UNCERTAIN
        assert result.no_license_found is True
        assert len(result.sources_used) == 0
        assert any("no license" in r.lower() for r in result.reasons)

    def test_no_license_found_flag_only_when_no_sources(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test no_license_found is False when any source provides info."""
        result = scorer.calculate(pypi_license="MIT")

        assert result.no_license_found is False

    # ==========================================================================
    # Integration with ModifiedLicenseResult
    # ==========================================================================

    def test_integration_with_modification_result_unmodified(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test integration with unmodified ModifiedLicenseResult."""
        mod_result = ModifiedLicenseResult(
            is_modified=False,
            closest_license="MIT",
            similarity_score=0.98,
            modifications=[],
        )

        result = scorer.calculate(
            github_license="MIT",
            modification_result=mod_result,
        )

        assert result.level == ConfidenceLevel.HIGH

    def test_integration_with_modification_result_modified(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test integration with modified ModifiedLicenseResult."""
        mod_result = ModifiedLicenseResult(
            is_modified=True,
            closest_license="MIT",
            similarity_score=0.85,
            modifications=["Additional restriction detected: 'non-commercial'"],
        )

        result = scorer.calculate(
            github_license="MIT",
            modification_result=mod_result,
        )

        assert result.level == ConfidenceLevel.MEDIUM
        assert "85%" in result.reasons[0]

    # ==========================================================================
    # Edge cases
    # ==========================================================================

    def test_none_license_treated_as_no_license(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test that None license values result in no license found."""
        result = scorer.calculate(pypi_license=None, github_license=None)

        assert result.level == ConfidenceLevel.UNCERTAIN
        assert result.no_license_found is True

    def test_empty_string_license_treated_as_no_license(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test that empty string license is treated as no license."""
        result = scorer.calculate(pypi_license="", github_license="  ")

        assert result.level == ConfidenceLevel.UNCERTAIN
        assert result.no_license_found is True

    def test_conflict_message_includes_all_sources(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test conflict message lists all source-license pairs."""
        result = scorer.calculate(
            pypi_license="MIT",
            github_license="Apache-2.0",
        )

        reason = result.reasons[0]
        assert "PyPI=MIT" in reason
        assert "LICENSE=APACHE-2.0" in reason

    def test_case_insensitive_license_comparison(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test that license comparison is case-insensitive."""
        result = scorer.calculate(
            pypi_license="mit",
            github_license="MIT",
        )

        # Should be HIGH because they match (case-insensitive)
        assert result.level == ConfidenceLevel.HIGH
        assert "Multiple sources agree" in result.reasons[0]

    def test_is_modified_true_with_high_similarity(
        self, scorer: ConfidenceScorer
    ) -> None:
        """Test edge case: is_modified=True but similarity >= 0.90."""
        # This could happen if detector marks as modified for other reasons
        mod_result = ModifiedLicenseResult(
            is_modified=True,
            closest_license="MIT",
            similarity_score=0.92,
            modifications=["Minor formatting change"],
        )

        result = scorer.calculate(
            github_license="MIT",
            modification_result=mod_result,
        )

        # Should be MEDIUM because is_modified=True, even with high similarity
        assert result.level == ConfidenceLevel.MEDIUM


class TestConfidenceScorerSourcePriority:
    """Tests verifying source priority behavior."""

    @pytest.fixture
    def scorer(self) -> ConfidenceScorer:
        """Create scorer instance."""
        return ConfidenceScorer()

    def test_license_file_higher_priority_than_readme(
        self, scorer: ConfidenceScorer
    ) -> None:
        """LICENSE file alone gives HIGH, README alone gives UNCERTAIN."""
        license_result = scorer.calculate(github_license="MIT")
        readme_result = scorer.calculate(readme_license="MIT")

        assert license_result.level == ConfidenceLevel.HIGH
        assert readme_result.level == ConfidenceLevel.UNCERTAIN

    def test_pypi_higher_priority_than_readme(
        self, scorer: ConfidenceScorer
    ) -> None:
        """PyPI alone gives MEDIUM, README alone gives UNCERTAIN."""
        pypi_result = scorer.calculate(pypi_license="MIT")
        readme_result = scorer.calculate(readme_license="MIT")

        assert pypi_result.level == ConfidenceLevel.MEDIUM
        assert readme_result.level == ConfidenceLevel.UNCERTAIN
