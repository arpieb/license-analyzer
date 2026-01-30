"""Markdown output formatter for license scan results."""

from datetime import datetime, timezone

from license_analyzer.constants import LEGAL_DISCLAIMER
from license_analyzer.models.scan import PackageLicense, ScanResult


class ScanMarkdownFormatter:
    """Format scan results as Markdown output.

    Provides formatted Markdown representation of license scan results
    suitable for legal review and documentation (FR16).
    """

    def format_scan_result(self, result: ScanResult) -> str:
        """Format scan result as Markdown string.

        Args:
            result: The scan result to format.

        Returns:
            Markdown string representation of the scan result.
        """
        lines: list[str] = []

        # Title
        lines.append("# License Scan Report")
        lines.append("")

        # Timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        lines.append(f"*Generated: {timestamp}*")
        lines.append("")

        if result.total_packages == 0:
            # Still show disclaimer even for empty results (FR19)
            lines.extend(self._format_disclaimer())
            lines.append("")
            lines.append("*No packages found.*")
            return "\n".join(lines)

        # Executive summary (FR18 - appears at top of reports)
        lines.extend(self._format_executive_summary(result))
        lines.append("")

        # Legal disclaimer (FR19)
        lines.extend(self._format_disclaimer())
        lines.append("")

        # Status badge
        lines.extend(self._format_status_badge(result))
        lines.append("")

        # Issues section (prominently placed after executive summary)
        if result.issues_found > 0:
            lines.extend(self._format_issues(result))
            lines.append("")

        # Policy violations section (FR23)
        if result.policy_violations:
            lines.extend(self._format_policy_violations(result))
            lines.append("")

        # Packages table
        lines.extend(self._format_packages(result))
        lines.append("")

        # Overrides Applied section (FR25)
        overridden_packages = [pkg for pkg in result.packages if pkg.is_overridden]
        if overridden_packages:
            lines.extend(self._format_overrides(overridden_packages))
            lines.append("")

        return "\n".join(lines)

    def _format_executive_summary(self, result: ScanResult) -> list[str]:
        """Format executive summary section.

        Provides a quick overview at the top of the report with key metrics
        and overall status (FR18).

        Args:
            result: The scan result.

        Returns:
            List of Markdown lines for executive summary.
        """
        licenses_found = result.total_packages - result.issues_found
        total_issues = result.issues_found + len(result.policy_violations)

        # Determine status and message with severity highlighting (AC #3)
        if result.has_issues:
            status = "⚠️ ISSUES FOUND"
            message = (
                f"**{total_issues} issue(s) require attention** - "
                "review Issues/Violations sections below"
            )
        else:
            status = "✅ PASS"
            message = "All packages compatible"

        lines = [
            "## Executive Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Packages | {result.total_packages} |",
            f"| Licenses Found | {licenses_found} |",
            f"| Issues | {result.issues_found} |",
        ]

        # Add policy violations row if any exist
        if result.policy_violations:
            lines.append(f"| Policy Violations | {len(result.policy_violations)} |")

        # Add ignored packages row if any were ignored (FR24)
        ignored = result.ignored_packages_summary
        if ignored and ignored.ignored_count > 0:
            lines.append(f"| Packages Ignored | {ignored.ignored_count} |")

        # Add overrides count if any were applied (FR25)
        overrides_count = sum(1 for pkg in result.packages if pkg.is_overridden)
        if overrides_count > 0:
            lines.append(f"| Overrides Applied | {overrides_count} |")

        lines.extend(
            [
                f"| **Status** | **{status}** |",
                "",
                f"> {message}",
            ]
        )

        # Add ignored packages note if any were ignored (FR24)
        if ignored and ignored.ignored_count > 0 and ignored.ignored_names:
            names_str = ", ".join(ignored.ignored_names)
            lines.extend(
                [
                    "",
                    f"> *{ignored.ignored_count} packages ignored: {names_str}*",
                ]
            )

        return lines

    def _format_disclaimer(self) -> list[str]:
        """Format legal disclaimer section.

        Provides a prominent disclaimer that this is not legal advice (FR19).

        Returns:
            List of Markdown lines for disclaimer.
        """
        return [
            "> **NOT LEGAL ADVICE**",
            ">",
            f"> {LEGAL_DISCLAIMER}",
        ]

    def _format_status_badge(self, result: ScanResult) -> list[str]:
        """Format status badge section.

        Args:
            result: The scan result.

        Returns:
            List of Markdown lines for status badge.
        """
        if result.has_issues:
            status = "failing"
            color = "red"
        else:
            status = "passing"
            color = "green"

        badge_url = f"https://img.shields.io/badge/License%20Scan-{status}-{color}"
        return [f"![Status]({badge_url})"]

    def _format_packages(self, result: ScanResult) -> list[str]:
        """Format packages table section.

        Args:
            result: The scan result.

        Returns:
            List of Markdown lines for packages table.
        """
        # Check if any packages have overrides to determine column structure
        has_overrides = any(pkg.is_overridden for pkg in result.packages)

        if has_overrides:
            lines = [
                "## Packages",
                "",
                "| Package | Version | License | Notes |",
                "|---------|---------|---------|-------|",
            ]
        else:
            lines = [
                "## Packages",
                "",
                "| Package | Version | License |",
                "|---------|---------|---------|",
            ]

        # Sort packages alphabetically by name
        sorted_packages = sorted(result.packages, key=lambda p: p.name.lower())

        for pkg in sorted_packages:
            license_display = pkg.license if pkg.license else "⚠️ Unknown"
            if has_overrides:
                if pkg.is_overridden:
                    original = pkg.original_license or "Unknown"
                    notes = f"Override (was: {original})"
                else:
                    notes = ""
                lines.append(
                    f"| {pkg.name} | {pkg.version} | {license_display} | {notes} |"
                )
            else:
                lines.append(f"| {pkg.name} | {pkg.version} | {license_display} |")

        return lines

    def _format_issues(self, result: ScanResult) -> list[str]:
        """Format issues section.

        Args:
            result: The scan result.

        Returns:
            List of Markdown lines for issues section.
        """
        lines = [
            "## Issues",
            "",
            f"> **{result.issues_found} package(s) require attention**",
            "",
            "| Package | Version | Issue | Suggestion |",
            "|---------|---------|-------|------------|",
        ]

        # Find packages with issues (no license)
        packages_with_issues = [pkg for pkg in result.packages if not pkg.license]

        # Sort alphabetically
        sorted_issues = sorted(packages_with_issues, key=lambda p: p.name.lower())

        for pkg in sorted_issues:
            suggestion = "Check package documentation or PyPI page"
            lines.append(
                f"| {pkg.name} | {pkg.version} | No license found | {suggestion} |"
            )

        return lines

    def _format_policy_violations(self, result: ScanResult) -> list[str]:
        """Format policy violations section.

        Args:
            result: The scan result.

        Returns:
            List of Markdown lines for policy violations section.
        """
        lines = [
            "## Policy Violations",
            "",
            f"> **{len(result.policy_violations)} package(s) violate license policy**",
            "",
            "| Package | Version | License | Reason |",
            "|---------|---------|---------|--------|",
        ]

        # Sort violations alphabetically by package name
        sorted_violations = sorted(
            result.policy_violations, key=lambda v: v.package_name.lower()
        )

        for violation in sorted_violations:
            license_display = violation.detected_license or "Unknown"
            lines.append(
                f"| {violation.package_name} | {violation.package_version} | "
                f"{license_display} | {violation.reason} |"
            )

        return lines

    def _format_overrides(self, overridden_packages: list[PackageLicense]) -> list[str]:
        """Format overrides applied section.

        Args:
            overridden_packages: List of packages with overrides applied.

        Returns:
            List of Markdown lines for overrides section.
        """

        count = len(overridden_packages)
        lines = [
            "## Overrides Applied",
            "",
            f"> **{count} package(s) have manual license overrides**",
            "",
            "| Package | Original | Override | Reason |",
            "|---------|----------|----------|--------|",
        ]

        # Sort by package name
        sorted_overrides = sorted(overridden_packages, key=lambda p: p.name.lower())

        for pkg in sorted_overrides:
            original = pkg.original_license or "Unknown"
            override_license = pkg.license or "Unknown"
            reason = pkg.override_reason or ""
            lines.append(f"| {pkg.name} | {original} | {override_license} | {reason} |")

        return lines
