"""Modified license detection.

Detects when LICENSE file content differs from known standard templates
using fuzzy matching (difflib.SequenceMatcher).
"""

import re
from difflib import SequenceMatcher
from typing import Optional

from pydantic import BaseModel, Field

# Thresholds for classification
# >90% = exact match (account for year/name variations)
EXACT_MATCH_THRESHOLD = 0.90
# 50-90% = modified version (lowered to catch partial matches)
MODIFIED_THRESHOLD = 0.50
# <50% = likely different license or highly customized

# Additional restriction phrases that indicate modifications
# Note: "shall not" excluded - appears in standard GPL/LGPL text
# Note: "non-commercial" excluded - appears in permissive Unlicense text
#       Use "non-commercial use" variants instead for actual restrictions
RESTRICTION_PHRASES = [
    "must not",
    "prohibited",
    "forbidden",
    "restricted to",
    "not permitted",
    "only for",
    "for non-commercial use",
    "non-commercial use only",
    "no commercial use",
    "personal use only",
    "educational use only",
    "internal use only",
]


class ModifiedLicenseResult(BaseModel):
    """Result of modified license detection."""

    is_modified: bool = Field(description="Whether license is modified from template")
    closest_license: Optional[str] = Field(
        description="SPDX identifier of closest matching license"
    )
    similarity_score: float = Field(
        ge=0.0, le=1.0, description="Similarity score (0.0-1.0)"
    )
    modifications: list[str] = Field(
        default_factory=list, description="List of detected modifications"
    )

    model_config = {"extra": "forbid"}


# Known license templates - canonical versions of common licenses
# These are trimmed versions focusing on the unique identifying text
LICENSE_TEMPLATES: dict[str, str] = {
    "MIT": """MIT License

Copyright (c) [year] [fullname]

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
SOFTWARE.""",
    "Apache-2.0": """Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

1. Definitions.

"License" shall mean the terms and conditions for use, reproduction,
and distribution as defined by Sections 1 through 9 of this document.

"Licensor" shall mean the copyright owner or entity authorized by
the copyright owner that is granting the License.

"Legal Entity" shall mean the union of the acting entity and all
other entities that control, are controlled by, or are under common
control with that entity. For the purposes of this definition,
"control" means (i) the power, direct or indirect, to cause the
direction or management of such entity, whether by contract or
otherwise, or (ii) ownership of fifty percent (50%) or more of the
outstanding shares, or (iii) beneficial ownership of such entity.

"You" (or "Your") shall mean an individual or Legal Entity
exercising permissions granted by this License.""",
    "GPL-3.0": """GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.

Preamble

The GNU General Public License is a free, copyleft license for
software and other kinds of works.

The licenses for most software and other practical works are designed
to take away your freedom to share and change the works.  By contrast,
the GNU General Public License is intended to guarantee your freedom to
share and change all versions of a program--to make sure it remains free
software for all its users.""",
    "GPL-2.0": """GNU GENERAL PUBLIC LICENSE
Version 2, June 1991

Copyright (C) 1989, 1991 Free Software Foundation, Inc.
51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.

Preamble

The licenses for most software are designed to take away your
freedom to share and change it.  By contrast, the GNU General Public
License is intended to guarantee your freedom to share and change free
software--to make sure the software is free for all its users.""",
    "BSD-3-Clause": """BSD 3-Clause License

Copyright (c) [year], [fullname]

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
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.""",
    "BSD-2-Clause": """BSD 2-Clause License

Copyright (c) [year], [fullname]

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.""",
    "ISC": """ISC License

Copyright (c) [year], [fullname]

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.""",
    "Unlicense": """This is free and unencumbered software released into the public \
domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <https://unlicense.org>""",
    "MPL-2.0": """Mozilla Public License Version 2.0

1. Definitions

1.1. "Contributor"
    means each individual or legal entity that creates, contributes to
    the creation of, or owns Covered Software.

1.2. "Contributor Version"
    means the combination of the Contributions of others (if any) used
    by a Contributor and that particular Contributor's Contribution.

1.3. "Contribution"
    means Covered Software of a particular Contributor.

1.4. "Covered Software"
    means Source Code Form to which the initial Contributor has attached
    the notice in Exhibit A, the Executable Form of such Source Code
    Form, and Modifications of such Source Code Form, in each case
    including portions thereof.""",
    "LGPL-3.0": """GNU LESSER GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.

This version of the GNU Lesser General Public License incorporates
the terms and conditions of version 3 of the GNU General Public
License, supplemented by the additional permissions listed below.""",
    "LGPL-2.1": """GNU LESSER GENERAL PUBLIC LICENSE
Version 2.1, February 1999

Copyright (C) 1991, 1999 Free Software Foundation, Inc.
51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.

This is the first released version of the Lesser GPL.  It also counts
as the successor of the GNU Library Public License, version 2, hence
the version number 2.1.""",
}


def _normalize_license_text(text: str) -> str:
    """Normalize license text for comparison.

    - Remove copyright holder names and years
    - Normalize whitespace
    - Convert to lowercase

    Args:
        text: Raw license text.

    Returns:
        Normalized text for comparison.
    """
    # Replace year patterns: 2024, 2020-2024, (c) 2024, etc.
    text = re.sub(r"\d{4}(-\d{4})?", "[YEAR]", text)
    # Replace common placeholder patterns
    text = re.sub(r"\[year\]", "[YEAR]", text, flags=re.IGNORECASE)
    text = re.sub(r"\[fullname\]", "[HOLDER]", text, flags=re.IGNORECASE)
    # Replace email addresses
    text = re.sub(r"<[^>]+@[^>]+>", "[EMAIL]", text)
    # Replace URLs
    text = re.sub(r"https?://[^\s]+", "[URL]", text)
    # Normalize copyright lines - remove everything after year until newline
    # This handles: "Copyright (c) 2024 John Doe" -> "Copyright (c) [YEAR]"
    # and "Copyright (c) 2024, Acme Corp" -> "Copyright (c) [YEAR]"
    text = re.sub(
        r"(copyright\s*(?:\(c\))?\s*\[YEAR\])[,\s]+[^\n]+",
        r"\1 [HOLDER]",
        text,
        flags=re.IGNORECASE,
    )
    # Normalize whitespace (collapse multiple spaces/newlines to single space)
    text = " ".join(text.split())
    return text.lower()


class ModifiedLicenseDetector:
    """Detects modified or customized licenses by comparing against templates."""

    def __init__(self) -> None:
        """Initialize with pre-normalized license templates."""
        self._templates: dict[str, str] = {}
        for license_id, template in LICENSE_TEMPLATES.items():
            self._templates[license_id] = _normalize_license_text(template)

    def detect(
        self, content: str, claimed_license: Optional[str] = None
    ) -> ModifiedLicenseResult:
        """Detect if license content is modified from known templates.

        Args:
            content: The LICENSE file content to analyze.
            claimed_license: Optional claimed license (e.g., from PyPI metadata).

        Returns:
            ModifiedLicenseResult with detection findings.
        """
        if not content or not content.strip():
            return ModifiedLicenseResult(
                is_modified=False,
                closest_license=None,
                similarity_score=0.0,
                modifications=["Empty or missing license content"],
            )

        # Find closest match
        closest, score = self._find_closest_match(content)
        modifications: list[str] = []

        # Always check for restriction phrases (regardless of similarity score)
        restriction_mods = self._detect_restriction_phrases(content)
        modifications.extend(restriction_mods)

        # Determine if modified
        if score >= EXACT_MATCH_THRESHOLD:
            is_modified = len(restriction_mods) > 0  # Modified if restrictions found
        elif score >= MODIFIED_THRESHOLD:
            is_modified = True
            # Detect what was modified (patterns beyond restriction phrases)
            pattern_mods = self._detect_modification_patterns(content, closest)
            modifications.extend(pattern_mods)
        else:
            # Score too low - might be different license entirely
            is_modified = True
            if closest:
                modifications.append(
                    f"Low similarity ({score:.1%}) - may be heavily modified or "
                    f"different license than {closest}"
                )
            else:
                modifications.append("Could not identify license type")

        # Check for claim mismatch
        if claimed_license and closest and claimed_license != closest:
            modifications.append(
                f"License mismatch: claimed '{claimed_license}' but content "
                f"matches '{closest}' ({score:.1%} similarity)"
            )

        return ModifiedLicenseResult(
            is_modified=is_modified,
            closest_license=closest if score >= MODIFIED_THRESHOLD else None,
            similarity_score=score,
            modifications=modifications,
        )

    def _find_closest_match(self, content: str) -> tuple[Optional[str], float]:
        """Find the closest matching license template.

        Args:
            content: License content to match.

        Returns:
            Tuple of (license_id, similarity_ratio).
        """
        normalized = _normalize_license_text(content)
        best_match: Optional[str] = None
        best_ratio = 0.0

        for license_id, template in self._templates.items():
            ratio = SequenceMatcher(None, normalized, template).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = license_id

        return (best_match, best_ratio)

    def _detect_restriction_phrases(self, content: str) -> list[str]:
        """Detect restriction phrases in the license content.

        This method runs regardless of similarity score to catch
        added restrictions even in partial license texts.

        Args:
            content: The license content.

        Returns:
            List of detected restriction phrases.
        """
        modifications: list[str] = []
        content_lower = content.lower()

        # Check for additional restriction phrases
        # These are phrases that typically indicate non-standard restrictions
        for phrase in RESTRICTION_PHRASES:
            if phrase in content_lower:
                modifications.append(f"Additional restriction detected: '{phrase}'")

        return modifications

    def _detect_modification_patterns(
        self, content: str, closest_license: Optional[str]
    ) -> list[str]:
        """Detect modification patterns by comparing against templates.

        Args:
            content: The license content.
            closest_license: The closest matching license ID.

        Returns:
            List of human-readable modification descriptions.
        """
        modifications: list[str] = []
        content_lower = content.lower()

        # Check for common modification patterns
        modification_patterns = [
            (r"additional\s+(?:terms?|conditions?|restrictions?)", "Additional terms"),
            (r"(?:this|the)\s+following\s+(?:additional|extra)", "Extra conditions"),
            (r"with\s+the\s+exception", "Exception clause"),
            (r"notwithstanding", "Notwithstanding clause"),
            (r"amendment", "Amendment"),
        ]

        for pattern, description in modification_patterns:
            if (
                re.search(pattern, content_lower)
                and closest_license
                and closest_license in LICENSE_TEMPLATES
            ):
                template_lower = LICENSE_TEMPLATES[closest_license].lower()
                if not re.search(pattern, template_lower):
                    modifications.append(f"{description} added to license")

        return modifications
