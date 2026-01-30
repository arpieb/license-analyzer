"""Confidence level scoring for license detection.

Calculates confidence levels (HIGH/MEDIUM/UNCERTAIN) based on:
- Number of agreeing sources
- License file modification status
- Source reliability hierarchy
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from license_analyzer.analysis.modified import ModifiedLicenseResult

# Threshold from Story 2.3 for modified license detection
MODIFIED_THRESHOLD = 0.50


class ConfidenceLevel(str, Enum):
    """Confidence levels for license detection (FR11)."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    UNCERTAIN = "UNCERTAIN"


class ConfidenceResult(BaseModel):
    """Result of confidence scoring."""

    level: ConfidenceLevel = Field(description="Confidence level")
    reasons: list[str] = Field(
        default_factory=list, description="Human-readable reasons for confidence level"
    )
    sources_used: list[str] = Field(
        default_factory=list, description="Sources that contributed to scoring"
    )
    no_license_found: bool = Field(
        default=False, description="True if no license found from any source (FR14)"
    )

    model_config = {"extra": "forbid"}


class ConfidenceScorer:
    """Calculates confidence levels for license detection results.

    Confidence Level Rules:
    - HIGH: Multiple sources agree, or LICENSE file matches template exactly
    - MEDIUM: Single reliable source (PyPI or unmodified LICENSE)
    - UNCERTAIN: Conflicts, README only, heavily modified, or no license found
    """

    def calculate(
        self,
        pypi_license: Optional[str] = None,
        github_license: Optional[str] = None,
        readme_license: Optional[str] = None,
        modification_result: Optional[ModifiedLicenseResult] = None,
    ) -> ConfidenceResult:
        """Calculate confidence level based on available sources.

        Args:
            pypi_license: License from PyPI metadata (e.g., "MIT").
            github_license: License identified from GitHub LICENSE file.
            readme_license: License mentioned in README.
            modification_result: Result from ModifiedLicenseDetector (optional).

        Returns:
            ConfidenceResult with level, reasons, and sources.
        """
        sources_used: list[str] = []
        licenses: list[str] = []

        # Collect available sources and their licenses
        # Note: Empty strings are explicitly filtered out (treated as no license)
        if pypi_license and pypi_license.strip():
            sources_used.append("PyPI")
            licenses.append(pypi_license.strip().upper())
        if github_license and github_license.strip():
            sources_used.append("LICENSE")
            licenses.append(github_license.strip().upper())
        if readme_license and readme_license.strip():
            sources_used.append("README")
            licenses.append(readme_license.strip().upper())

        # AC #4: No license found from any source (FR14)
        if not sources_used:
            return ConfidenceResult(
                level=ConfidenceLevel.UNCERTAIN,
                reasons=["No license information found from any source"],
                sources_used=[],
                no_license_found=True,
            )

        # AC #3: Check for conflicts (different licenses from different sources)
        unique_licenses = set(licenses)
        if len(unique_licenses) > 1:
            # Build detailed conflict message
            source_license_pairs = [
                f"{src}={lic}" for src, lic in zip(sources_used, licenses)
            ]
            return ConfidenceResult(
                level=ConfidenceLevel.UNCERTAIN,
                reasons=[f"Sources disagree: {', '.join(source_license_pairs)}"],
                sources_used=sources_used,
            )

        # AC #1: Multiple agreeing sources = HIGH confidence
        if len(sources_used) >= 2:
            return ConfidenceResult(
                level=ConfidenceLevel.HIGH,
                reasons=["Multiple sources agree on license"],
                sources_used=sources_used,
            )

        # Single source logic - check which source we have
        # AC #1: LICENSE file with modification detection
        if github_license and modification_result:
            if not modification_result.is_modified:
                # AC #1: Unmodified LICENSE file = HIGH
                return ConfidenceResult(
                    level=ConfidenceLevel.HIGH,
                    reasons=["LICENSE file matches known template exactly"],
                    sources_used=sources_used,
                )
            elif modification_result.similarity_score >= MODIFIED_THRESHOLD:
                # AC #4 (Task 4): Modified but identifiable = MEDIUM
                similarity_pct = f"{modification_result.similarity_score:.0%}"
                return ConfidenceResult(
                    level=ConfidenceLevel.MEDIUM,
                    reasons=[f"LICENSE file modified ({similarity_pct} similarity)"],
                    sources_used=sources_used,
                )
            else:
                # AC #3 (Task 5): Heavily modified = UNCERTAIN
                similarity_pct = f"{modification_result.similarity_score:.0%}"
                return ConfidenceResult(
                    level=ConfidenceLevel.UNCERTAIN,
                    reasons=[
                        f"LICENSE file heavily modified ({similarity_pct} similarity)"
                    ],
                    sources_used=sources_used,
                )

        # AC #1: LICENSE file without modification detection = HIGH
        # (Assume unmodified if no modification_result provided)
        if github_license and modification_result is None:
            return ConfidenceResult(
                level=ConfidenceLevel.HIGH,
                reasons=["LICENSE file identified"],
                sources_used=sources_used,
            )

        # AC #2: Single PyPI source = MEDIUM
        if pypi_license:
            return ConfidenceResult(
                level=ConfidenceLevel.MEDIUM,
                reasons=["Single source: PyPI metadata only"],
                sources_used=sources_used,
            )

        # AC #3: README only = UNCERTAIN
        if readme_license:
            return ConfidenceResult(
                level=ConfidenceLevel.UNCERTAIN,
                reasons=["README mention only - needs verification"],
                sources_used=sources_used,
            )

        # Fallback (should not reach here given logic above)
        return ConfidenceResult(
            level=ConfidenceLevel.UNCERTAIN,
            reasons=["Unable to determine confidence"],
            sources_used=sources_used,
        )
