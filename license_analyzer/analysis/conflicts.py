"""Source conflict detection for license analysis.

Detects when multiple sources disagree about a package's license (FR12).
"""
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class SourceConflict(BaseModel):
    """Result of source conflict detection (FR12).

    Provides detailed information about license source conflicts,
    including which sources disagree and what licenses each reports.
    """

    sources: dict[str, str] = Field(
        default_factory=dict,
        description="Map of source name to detected license",
    )
    detected_licenses: list[str] = Field(
        default_factory=list,
        description="List of unique licenses detected across all sources",
    )
    primary_license: Optional[str] = Field(
        default=None,
        description="Resolved primary license (set when no conflict)",
    )

    model_config = {"extra": "forbid"}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_conflict(self) -> bool:
        """True if sources disagree about the license."""
        return len(self.detected_licenses) > 1


class ConflictDetector:
    """Detects conflicts between license sources.

    Implements FR12: System can detect conflicts when multiple sources
    disagree about a package's license.

    Uses the same normalization patterns as ConfidenceScorer (Story 2.4):
    - Case-insensitive comparison via uppercase normalization
    - Empty strings and whitespace-only strings treated as no source
    """

    def detect(
        self,
        pypi_license: Optional[str] = None,
        github_license: Optional[str] = None,
        readme_license: Optional[str] = None,
    ) -> SourceConflict:
        """Detect conflicts between license sources.

        Args:
            pypi_license: License from PyPI metadata.
            github_license: License from LICENSE file.
            readme_license: License mentioned in README.

        Returns:
            SourceConflict with conflict details including:
            - sources: Map of source name to normalized license
            - detected_licenses: Unique licenses across all sources
            - primary_license: Set only when no conflict
            - has_conflict: Computed property, True if sources disagree
        """
        sources: dict[str, str] = {}

        # Collect sources with normalized licenses (case-insensitive)
        # Empty strings and whitespace are treated as no source (per Story 2.4 pattern)
        if pypi_license and pypi_license.strip():
            sources["PyPI"] = pypi_license.strip().upper()
        if github_license and github_license.strip():
            sources["LICENSE"] = github_license.strip().upper()
        if readme_license and readme_license.strip():
            sources["README"] = readme_license.strip().upper()

        # Get unique licenses sorted for deterministic output
        unique_licenses = sorted(set(sources.values()))

        # Determine primary license (only if no conflict)
        primary_license: Optional[str] = None
        if len(unique_licenses) == 1:
            primary_license = unique_licenses[0]

        return SourceConflict(
            sources=sources,
            detected_licenses=unique_licenses,
            primary_license=primary_license,
        )
