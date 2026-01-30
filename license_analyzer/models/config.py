"""Configuration Pydantic models for license-analyzer."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class LicenseOverride(BaseModel):
    """Manual license override for a package.

    Used when automatic detection fails or needs correction.
    """

    model_config = {"extra": "forbid"}

    license: str = Field(description="SPDX license identifier to use")
    reason: str = Field(description="Reason for the override")


class AnalyzerConfig(BaseModel):
    """Configuration for license-analyzer.

    All fields are optional with None defaults to allow partial configuration.
    Story 6.2, 6.3, 6.4 will implement the logic that uses these fields.
    """

    model_config = {"extra": "forbid"}

    allowed_licenses: Optional[List[str]] = Field(
        default=None,
        description="List of allowed SPDX license identifiers. "
        "Packages with other licenses will be flagged.",
    )
    ignored_packages: Optional[List[str]] = Field(
        default=None,
        description="List of package names to skip during scanning.",
    )
    overrides: Optional[Dict[str, LicenseOverride]] = Field(
        default=None,
        description="Manual license overrides by package name.",
    )
