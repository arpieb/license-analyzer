"""Constants for license-analyzer."""

# Exit codes per FR35-FR37
EXIT_SUCCESS = 0  # No issues found
EXIT_ISSUES = 1  # License issues found
EXIT_ERROR = 2  # Scan failed due to error

# Legal disclaimer (FR19)
LEGAL_DISCLAIMER = (
    "This tool provides license information for informational purposes only. "
    "It does not constitute legal advice. Consult a qualified attorney for "
    "legal guidance on license compliance."
)

# Short disclaimer for terminal display (concise for readability)
LEGAL_DISCLAIMER_SHORT = (
    "This tool provides license information for informational purposes only. "
    "It does not constitute legal advice."
)
