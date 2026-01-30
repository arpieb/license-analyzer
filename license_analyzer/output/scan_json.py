"""JSON output formatter for license scan results."""
import json
from datetime import datetime, timezone
from typing import Any

from license_analyzer import __version__
from license_analyzer.constants import LEGAL_DISCLAIMER
from license_analyzer.models.scan import ScanResult


class ScanJsonFormatter:
    """Format scan results as JSON output.

    Provides structured JSON representation of license scan results
    for programmatic processing and CI/CD integration (FR17).
    """

    def format_scan_result(self, result: ScanResult) -> str:
        """Format scan result as JSON string.

        Args:
            result: The scan result to format.

        Returns:
            JSON string representation of the scan result.
        """
        output = self._build_output(result)
        return json.dumps(output, indent=2)

    def _build_output(self, result: ScanResult) -> dict[str, Any]:
        """Build the output dictionary structure.

        Args:
            result: The scan result to convert.

        Returns:
            Dictionary ready for JSON serialization.
        """
        return {
            "scan_metadata": self._build_scan_metadata(),
            "summary": self._build_summary(result),
            "packages": self._build_packages(result),
            "issues": self._build_issues(result),
            "policy_violations": self._build_policy_violations(result),
        }

    def _build_scan_metadata(self) -> dict[str, Any]:
        """Build scan metadata section.

        Returns:
            Dictionary with scan metadata including legal disclaimer (FR19).
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "generated_at": timestamp,
            "tool_version": __version__,
            "disclaimer": LEGAL_DISCLAIMER,
            "disclaimer_type": "informational",
        }

    def _build_summary(self, result: ScanResult) -> dict[str, Any]:
        """Build summary section.

        Args:
            result: The scan result.

        Returns:
            Dictionary with summary statistics including executive summary fields.
        """
        licenses_found = result.total_packages - result.issues_found
        status = "issues_found" if result.has_issues else "pass"
        total_issues = result.issues_found + len(result.policy_violations)

        # Executive summary fields (FR18)
        if result.total_packages == 0:
            overall_status = "PASS"
            status_message = "No packages scanned"
        elif result.has_issues:
            overall_status = "ISSUES_FOUND"
            status_message = f"{total_issues} issue(s) require attention"
        else:
            overall_status = "PASS"
            status_message = "All packages compatible"

        # Build ignored packages summary (FR24)
        ignored_packages = None
        if result.ignored_packages_summary and result.ignored_packages_summary.ignored_count > 0:
            ignored_packages = {
                "count": result.ignored_packages_summary.ignored_count,
                "names": result.ignored_packages_summary.ignored_names or [],
            }

        return {
            "total_packages": result.total_packages,
            "licenses_found": licenses_found,
            "issues_found": result.issues_found,
            "policy_violations_count": len(result.policy_violations),
            "ignored_packages": ignored_packages,
            "overrides_applied": sum(1 for pkg in result.packages if pkg.is_overridden),
            "status": status,
            "has_issues": result.has_issues,
            "overall_status": overall_status,
            "status_message": status_message,
        }

    def _build_packages(self, result: ScanResult) -> list[dict[str, Any]]:
        """Build packages array.

        Args:
            result: The scan result.

        Returns:
            List of package dictionaries sorted alphabetically.
        """
        sorted_packages = sorted(result.packages, key=lambda p: p.name.lower())

        return [
            {
                "name": pkg.name,
                "version": pkg.version,
                "license": pkg.license,
                "has_license": bool(pkg.license),
                "original_license": pkg.original_license,
                "override_reason": pkg.override_reason,
                "is_overridden": pkg.is_overridden,
            }
            for pkg in sorted_packages
        ]

    def _build_issues(self, result: ScanResult) -> list[dict[str, Any]]:
        """Build issues array.

        Args:
            result: The scan result.

        Returns:
            List of issue dictionaries.
        """
        packages_with_issues = [pkg for pkg in result.packages if not pkg.license]
        sorted_issues = sorted(packages_with_issues, key=lambda p: p.name.lower())

        return [
            {
                "package": pkg.name,
                "version": pkg.version,
                "issue_type": "no_license",
                "suggestion": "Check package documentation or PyPI page",
            }
            for pkg in sorted_issues
        ]

    def _build_policy_violations(self, result: ScanResult) -> list[dict[str, Any]]:
        """Build policy violations array.

        Args:
            result: The scan result.

        Returns:
            List of policy violation dictionaries.
        """
        sorted_violations = sorted(
            result.policy_violations, key=lambda v: v.package_name.lower()
        )

        return [
            {
                "package_name": violation.package_name,
                "package_version": violation.package_version,
                "detected_license": violation.detected_license,
                "reason": violation.reason,
            }
            for violation in sorted_violations
        ]
