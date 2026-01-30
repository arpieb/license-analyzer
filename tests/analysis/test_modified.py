"""Tests for modified license detection."""
import pytest
from pydantic import ValidationError

from license_analyzer.analysis.modified import (
    EXACT_MATCH_THRESHOLD,
    LICENSE_TEMPLATES,
    MODIFIED_THRESHOLD,
    ModifiedLicenseDetector,
    ModifiedLicenseResult,
    _normalize_license_text,
)


class TestModifiedLicenseResult:
    """Tests for ModifiedLicenseResult model."""

    def test_create_result_with_required_fields(self) -> None:
        """Test creating a result with required fields."""
        result = ModifiedLicenseResult(
            is_modified=False,
            closest_license="MIT",
            similarity_score=0.99,
            modifications=[],
        )
        assert result.is_modified is False
        assert result.closest_license == "MIT"
        assert result.similarity_score == 0.99
        assert result.modifications == []

    def test_create_result_with_modifications(self) -> None:
        """Test creating a result with modifications list."""
        result = ModifiedLicenseResult(
            is_modified=True,
            closest_license="MIT",
            similarity_score=0.85,
            modifications=["Additional restriction detected: 'non-commercial'"],
        )
        assert result.is_modified is True
        assert len(result.modifications) == 1

    def test_result_forbids_extra_fields(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModifiedLicenseResult(
                is_modified=False,
                closest_license="MIT",
                similarity_score=0.99,
                modifications=[],
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_similarity_score_bounds(self) -> None:
        """Test similarity score validation (0.0-1.0)."""
        # Valid scores
        result = ModifiedLicenseResult(
            is_modified=False,
            closest_license="MIT",
            similarity_score=0.0,
            modifications=[],
        )
        assert result.similarity_score == 0.0

        result = ModifiedLicenseResult(
            is_modified=False,
            closest_license="MIT",
            similarity_score=1.0,
            modifications=[],
        )
        assert result.similarity_score == 1.0

    def test_similarity_score_rejects_invalid_values(self) -> None:
        """Test similarity score rejects values outside 0.0-1.0."""
        # Test negative value
        with pytest.raises(ValidationError):
            ModifiedLicenseResult(
                is_modified=False,
                closest_license="MIT",
                similarity_score=-0.1,
                modifications=[],
            )

        # Test value > 1.0
        with pytest.raises(ValidationError):
            ModifiedLicenseResult(
                is_modified=False,
                closest_license="MIT",
                similarity_score=1.5,
                modifications=[],
            )


class TestNormalizeLicenseText:
    """Tests for license text normalization."""

    def test_normalize_removes_years(self) -> None:
        """Test that years are normalized."""
        text = "Copyright (c) 2024 John Doe"
        normalized = _normalize_license_text(text)
        assert "[year]" in normalized
        assert "2024" not in normalized

    def test_normalize_removes_year_ranges(self) -> None:
        """Test that year ranges are normalized."""
        text = "Copyright 2020-2024 Jane Doe"
        normalized = _normalize_license_text(text)
        assert "2020" not in normalized
        assert "2024" not in normalized

    def test_normalize_collapses_whitespace(self) -> None:
        """Test that whitespace is collapsed."""
        text = "This   is\n\nsome   text"
        normalized = _normalize_license_text(text)
        assert "  " not in normalized
        assert "\n" not in normalized

    def test_normalize_converts_to_lowercase(self) -> None:
        """Test that text is lowercased."""
        text = "MIT License"
        normalized = _normalize_license_text(text)
        assert normalized == "mit license"

    def test_normalize_removes_email_addresses(self) -> None:
        """Test that email addresses are normalized."""
        text = "Contact <support@example.com> for help"
        normalized = _normalize_license_text(text)
        assert "support@example.com" not in normalized
        assert "[email]" in normalized


class TestModifiedLicenseDetector:
    """Tests for ModifiedLicenseDetector."""

    @pytest.fixture
    def detector(self) -> ModifiedLicenseDetector:
        """Create detector instance."""
        return ModifiedLicenseDetector()

    # ==========================================================================
    # AC #1: Exact match tests - license marked as unmodified
    # ==========================================================================

    def test_exact_mit_match_not_modified(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test exact MIT license match returns is_modified=False."""
        # Use the actual MIT template with a realistic copyright line
        mit_license = """MIT License

Copyright (c) 2024 Test Author

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

        result = detector.detect(mit_license)

        assert result.is_modified is False
        assert result.closest_license == "MIT"
        assert result.similarity_score >= EXACT_MATCH_THRESHOLD

    def test_exact_bsd3_match_not_modified(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test exact BSD-3-Clause license match returns is_modified=False."""
        bsd_license = """BSD 3-Clause License

Copyright (c) 2024, Acme Corp

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."""

        result = detector.detect(bsd_license)

        assert result.is_modified is False
        assert result.closest_license == "BSD-3-Clause"
        assert result.similarity_score >= EXACT_MATCH_THRESHOLD

    def test_exact_isc_match_not_modified(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test exact ISC license match returns is_modified=False."""
        isc_license = """ISC License

Copyright (c) 2024, Developer Name

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE."""

        result = detector.detect(isc_license)

        assert result.is_modified is False
        assert result.closest_license == "ISC"
        assert result.similarity_score >= EXACT_MATCH_THRESHOLD

    def test_exact_apache2_match_not_modified(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test exact Apache-2.0 license match returns is_modified=False."""
        # Use template directly - should match itself perfectly
        apache_license = LICENSE_TEMPLATES["Apache-2.0"]

        result = detector.detect(apache_license)

        assert result.is_modified is False
        assert result.closest_license == "Apache-2.0"
        assert result.similarity_score >= EXACT_MATCH_THRESHOLD

    def test_exact_gpl3_match_not_modified(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test exact GPL-3.0 license match returns is_modified=False."""
        gpl3_license = LICENSE_TEMPLATES["GPL-3.0"]

        result = detector.detect(gpl3_license)

        assert result.is_modified is False
        assert result.closest_license == "GPL-3.0"
        assert result.similarity_score >= EXACT_MATCH_THRESHOLD

    def test_exact_unlicense_match_not_modified(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test exact Unlicense match returns is_modified=False."""
        unlicense = LICENSE_TEMPLATES["Unlicense"]

        result = detector.detect(unlicense)

        assert result.is_modified is False
        assert result.closest_license == "Unlicense"
        assert result.similarity_score >= EXACT_MATCH_THRESHOLD

    # ==========================================================================
    # AC #2: Modified license tests - flagged as modified with closest match
    # ==========================================================================

    def test_modified_mit_with_restriction_detected(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test modified MIT with additional restriction is flagged (FR5)."""
        modified_mit = """MIT License

Copyright (c) 2024 Test Author

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

ADDITIONAL RESTRICTION: This software must not be used for commercial purposes
without explicit written permission from the copyright holder.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT."""

        result = detector.detect(modified_mit)

        assert result.is_modified is True
        assert result.closest_license == "MIT"
        assert result.similarity_score >= MODIFIED_THRESHOLD
        assert result.similarity_score < EXACT_MATCH_THRESHOLD
        # Should detect the "must not" restriction
        assert any("must not" in mod.lower() for mod in result.modifications)

    def test_modified_license_identifies_closest_match(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test modified license still identifies closest known license."""
        # MIT with some extra text added
        modified_license = """MIT License

Copyright (c) 2024 Example Corp

This software is provided under the MIT license with the following
additional terms for educational institutions:

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND."""

        result = detector.detect(modified_license)

        assert result.closest_license == "MIT"
        assert result.similarity_score >= MODIFIED_THRESHOLD

    def test_modified_license_highlights_differences(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test that significant differences are highlighted."""
        modified_mit = """MIT License

Copyright (c) 2024 Test Author

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software, with the exception of commercial entities which must obtain
a separate commercial license.

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND."""

        result = detector.detect(modified_mit)

        assert result.is_modified is True
        # Should detect exception clause
        assert len(result.modifications) > 0

    # ==========================================================================
    # AC #3: License mismatch tests - claimed vs actual discrepancy flagged
    # ==========================================================================

    def test_claimed_mit_but_content_is_apache_flagged(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test mismatch between claimed license and actual content (FR6)."""
        # Use Apache-2.0 content
        apache_content = LICENSE_TEMPLATES["Apache-2.0"]

        # Claim it's MIT
        result = detector.detect(apache_content, claimed_license="MIT")

        # Should flag the mismatch
        assert any("mismatch" in mod.lower() for mod in result.modifications)
        assert result.closest_license == "Apache-2.0"

    def test_claimed_matches_actual_no_mismatch(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test no mismatch flagged when claimed matches actual."""
        mit_license = LICENSE_TEMPLATES["MIT"]

        result = detector.detect(mit_license, claimed_license="MIT")

        # Should NOT have mismatch in modifications
        mismatch_mods = [m for m in result.modifications if "mismatch" in m.lower()]
        assert len(mismatch_mods) == 0

    # ==========================================================================
    # Edge cases
    # ==========================================================================

    def test_empty_content_returns_appropriate_result(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test empty content returns appropriate result."""
        result = detector.detect("")

        assert result.is_modified is False
        assert result.closest_license is None
        assert result.similarity_score == 0.0
        assert "empty" in result.modifications[0].lower()

    def test_whitespace_only_content(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test whitespace-only content returns appropriate result."""
        result = detector.detect("   \n\n   ")

        assert result.closest_license is None
        assert result.similarity_score == 0.0

    def test_unknown_license_low_similarity(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test completely unknown license returns low similarity."""
        unknown = """
        PROPRIETARY LICENSE AGREEMENT

        This software is the exclusive property of Example Corp.
        Unauthorized copying, modification, or distribution is strictly
        prohibited and will be prosecuted to the fullest extent of the law.

        Contact legal@example.com for licensing inquiries.
        """

        result = detector.detect(unknown)

        assert result.similarity_score < MODIFIED_THRESHOLD
        # closest_license should be None for very low similarity
        assert result.closest_license is None

    def test_whitespace_differences_ignored(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test that whitespace differences don't affect matching."""
        # MIT with different whitespace
        mit_different_whitespace = """MIT License

Copyright (c)   2024    Test Author

Permission is hereby granted,  free of charge,  to any person obtaining a copy
of this software and associated documentation files  (the "Software"),  to deal
in the Software without restriction,  including without limitation the rights
to use, copy, modify, merge, publish,  distribute,  sublicense, and/or sell
copies of the Software,  and to permit persons to whom the Software is
furnished to do so,  subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED  "AS IS",  WITHOUT WARRANTY OF ANY KIND,  EXPRESS OR
IMPLIED,  INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

        result = detector.detect(mit_different_whitespace)

        assert result.closest_license == "MIT"
        # Should still have high similarity despite whitespace differences
        assert result.similarity_score >= 0.90

    def test_different_copyright_holder_still_matches(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test different copyright holder doesn't affect matching."""
        mit_different_author = LICENSE_TEMPLATES["MIT"].replace(
            "[year] [fullname]", "2020 Very Long Company Name LLC"
        )

        result = detector.detect(mit_different_author)

        assert result.closest_license == "MIT"
        assert result.similarity_score >= EXACT_MATCH_THRESHOLD

    # ==========================================================================
    # Restriction phrase detection
    # ==========================================================================

    def test_non_commercial_restriction_detected(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test non-commercial restriction is detected."""
        license_with_restriction = """MIT License

Copyright (c) 2024 Test Author

Permission is hereby granted for non-commercial use only.

THE SOFTWARE IS PROVIDED "AS IS"."""

        result = detector.detect(license_with_restriction)

        assert result.is_modified is True
        assert any("non-commercial" in mod.lower() for mod in result.modifications)

    def test_prohibited_phrase_detected(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test 'prohibited' phrase is detected as restriction."""
        license_with_restriction = """MIT License

Copyright (c) 2024 Test Author

Permission is hereby granted. Use in military applications is prohibited.

THE SOFTWARE IS PROVIDED "AS IS"."""

        result = detector.detect(license_with_restriction)

        assert result.is_modified is True
        assert any("prohibited" in mod.lower() for mod in result.modifications)

    def test_standard_gpl3_no_false_positive_restrictions(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test standard GPL-3.0 doesn't trigger false positive restrictions."""
        gpl3_license = LICENSE_TEMPLATES["GPL-3.0"]

        result = detector.detect(gpl3_license)

        # Standard GPL should not have restriction phrases detected
        restriction_mods = [
            m for m in result.modifications if "restriction" in m.lower()
        ]
        assert len(restriction_mods) == 0, f"False positives: {restriction_mods}"

    def test_standard_apache_no_false_positive_restrictions(
        self, detector: ModifiedLicenseDetector
    ) -> None:
        """Test standard Apache-2.0 doesn't trigger false positive restrictions."""
        apache_license = LICENSE_TEMPLATES["Apache-2.0"]

        result = detector.detect(apache_license)

        # Standard Apache should not have restriction phrases detected
        restriction_mods = [
            m for m in result.modifications if "restriction" in m.lower()
        ]
        assert len(restriction_mods) == 0, f"False positives: {restriction_mods}"


class TestLicenseTemplates:
    """Tests for license template coverage."""

    def test_common_licenses_have_templates(self) -> None:
        """Test that common licenses have templates (NFR12)."""
        required_licenses = [
            "MIT",
            "Apache-2.0",
            "GPL-3.0",
            "GPL-2.0",
            "BSD-3-Clause",
            "BSD-2-Clause",
            "ISC",
        ]
        for license_id in required_licenses:
            assert license_id in LICENSE_TEMPLATES, f"Missing template for {license_id}"

    def test_templates_are_non_empty(self) -> None:
        """Test that all templates have content."""
        for license_id, template in LICENSE_TEMPLATES.items():
            assert len(template.strip()) > 100, f"Template for {license_id} too short"


class TestThresholds:
    """Tests for threshold constants."""

    def test_exact_match_threshold_is_reasonable(self) -> None:
        """Test exact match threshold is between 0.9 and 1.0."""
        assert 0.90 <= EXACT_MATCH_THRESHOLD <= 1.0

    def test_modified_threshold_is_reasonable(self) -> None:
        """Test modified threshold is between 0.5 and 0.9."""
        assert 0.50 <= MODIFIED_THRESHOLD <= 0.90

    def test_exact_threshold_higher_than_modified(self) -> None:
        """Test exact match threshold is higher than modified threshold."""
        assert EXACT_MATCH_THRESHOLD > MODIFIED_THRESHOLD
