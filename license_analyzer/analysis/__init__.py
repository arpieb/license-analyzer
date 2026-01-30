"""License analysis logic for license-analyzer."""
from license_analyzer.analysis.compatibility import (
    check_all_compatibility,
    check_license_compatibility,
)
from license_analyzer.analysis.confidence import (
    ConfidenceLevel,
    ConfidenceResult,
    ConfidenceScorer,
)
from license_analyzer.analysis.conflicts import (
    ConflictDetector,
    SourceConflict,
)
from license_analyzer.analysis.filtering import FilterResult, filter_ignored_packages
from license_analyzer.analysis.modified import (
    ModifiedLicenseDetector,
    ModifiedLicenseResult,
)
from license_analyzer.analysis.overrides import (
    apply_license_overrides,
    apply_overrides_to_tree,
)
from license_analyzer.analysis.policy import check_allowed_licenses
from license_analyzer.analysis.problematic import (
    PROBLEMATIC_LICENSES,
    LicenseCategory,
    get_license_category,
    is_problematic_license,
)

__all__ = [
    "ConfidenceLevel",
    "ConfidenceResult",
    "ConfidenceScorer",
    "ConflictDetector",
    "FilterResult",
    "LicenseCategory",
    "ModifiedLicenseDetector",
    "ModifiedLicenseResult",
    "PROBLEMATIC_LICENSES",
    "SourceConflict",
    "apply_license_overrides",
    "apply_overrides_to_tree",
    "check_all_compatibility",
    "check_allowed_licenses",
    "check_license_compatibility",
    "filter_ignored_packages",
    "get_license_category",
    "is_problematic_license",
]
