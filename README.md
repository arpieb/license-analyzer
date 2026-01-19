# Python License Analyzer

Scan Python dependencies for license information with confidence levels, compatibility checking, and clear reporting.

## Installation

```bash
# Using pip
pip install license-analyzer

# Using uv (recommended)
uv add license-analyzer
```

## Quick Start

```bash
# Scan current project
license-analyzer scan

# Generate markdown report
license-analyzer scan --format markdown --output report.md

# Generate JSON for CI/CD
license-analyzer scan --format json
```

## Features

- **Multi-source detection**: PyPI metadata, LICENSE files, README mentions
- **Confidence levels**: HIGH/MEDIUM/UNCERTAIN for each detection
- **Compatibility matrix**: Visual showing which licenses work together
- **Conflict detection**: Flags when sources disagree
- **Offline support**: Cache for air-gapped environments

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - no license issues found |
| 1 | Issues found - license conflicts or warnings |
| 2 | Error - scan failed |

## Configuration

Create `.license-analyzer.yaml` in your project root:

```yaml
allowed_licenses:
  - MIT
  - Apache-2.0
  - BSD-3-Clause

ignored_packages:
  - internal-package
```

## License

MIT

---

**Disclaimer:** This tool provides license detection, not legal advice.
