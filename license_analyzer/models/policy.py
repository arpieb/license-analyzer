"""Policy-related Pydantic models for license-analyzer."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PolicyViolation(BaseModel):
    """A license policy violation for a package.

    Represents a package that violates the allowed licenses policy
    configured in the project's configuration file.
    """

    model_config = {"extra": "forbid"}

    package_name: str = Field(description="Name of the package with violation")
    package_version: str = Field(description="Version of the package")
    detected_license: Optional[str] = Field(
        default=None,
        description="The license that was detected (None if unknown)",
    )
    reason: str = Field(description="Why this is a violation")
