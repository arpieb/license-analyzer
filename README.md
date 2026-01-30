# Python License Analyzer

Scan Python dependencies for license information with multi-source detection, dependency tree visualization, compatibility checking, and policy enforcement.

## Installation

```bash
# Using pip
pip install license-analyzer

# Using uv (recommended)
uv add license-analyzer

# From source (for development)
git clone https://github.com/your-org/license-analyzer.git
cd license-analyzer
uv sync
```

## Quick Start

```bash
# Scan current project for licenses
license-analyzer scan

# View dependency tree with licenses
license-analyzer tree

# Check license compatibility matrix
license-analyzer matrix
```

## Commands

### `scan` - License Scanning

Discovers all installed packages and retrieves their license information.

```bash
# Basic scan (terminal output)
license-analyzer scan

# Generate markdown report
license-analyzer scan --format markdown --output report.md

# Generate JSON for CI/CD integration
license-analyzer scan --format json

# Verbose output with detection details
license-analyzer scan --verbose

# Quiet mode (status and issues only)
license-analyzer scan --quiet

# Use custom config file
license-analyzer scan --config path/to/config.yaml
```

### `tree` - Dependency Tree

Displays a hierarchical view of dependencies with license information.

```bash
# Full dependency tree
license-analyzer tree

# Tree for specific packages
license-analyzer tree requests click

# Limit depth
license-analyzer tree --max-depth 2

# Output formats
license-analyzer tree --format json
license-analyzer tree --format markdown --output tree.md
```

### `matrix` - Compatibility Matrix

Shows license compatibility relationships between all licenses in your dependencies.

```bash
# View compatibility matrix
license-analyzer matrix

# For specific packages
license-analyzer matrix requests numpy pandas

# Output formats
license-analyzer matrix --format json
license-analyzer matrix --format markdown --output matrix.md
```

## Output Formats

| Format | Description | Use Case |
|--------|-------------|----------|
| `terminal` | Rich formatted tables (default) | Interactive use |
| `json` | Structured JSON | CI/CD pipelines, automation |
| `markdown` | Formatted markdown | Documentation, reports |

All commands support `--output FILE` to write to a file instead of stdout.

## Configuration

Create `.license-analyzer.yaml` in your project root, or add `[tool.license-analyzer]` to `pyproject.toml`.

### Configuration File Example

```yaml
# .license-analyzer.yaml

# Only allow these licenses (policy enforcement)
allowed_licenses:
  - MIT
  - Apache-2.0
  - BSD-2-Clause
  - BSD-3-Clause
  - ISC
  - Python-2.0
  - PSF-2.0

# Packages to exclude from scanning
ignored_packages:
  - my-internal-package
  - legacy-tool

# Manual license overrides (when auto-detection is wrong)
overrides:
  some-package:
    license: MIT
    reason: "Verified from LICENSE file in repository"
  another-package:
    license: Apache-2.0
    reason: "Confirmed with maintainer"
```

### Configuration in pyproject.toml

```toml
[tool.license-analyzer]
allowed_licenses = ["MIT", "Apache-2.0", "BSD-3-Clause"]
ignored_packages = ["internal-package"]

[tool.license-analyzer.overrides.some-package]
license = "MIT"
reason = "Verified from LICENSE file"
```

### Configuration Options

| Option | Type | Description |
|--------|------|-------------|
| `allowed_licenses` | list | Licenses permitted in your project. Packages with other licenses trigger policy violations. |
| `ignored_packages` | list | Package names to skip during scanning. |
| `overrides` | dict | Manual license corrections when auto-detection fails. |

## Features

### Multi-Source License Detection

Licenses are detected from multiple sources:
- **Package metadata** - `METADATA` files in installed packages
- **Classifiers** - PyPI trove classifiers
- **GitHub LICENSE files** - Direct repository inspection
- **README analysis** - License mentions in documentation

### Policy Enforcement

Define allowed licenses to enforce compliance:
- Packages with disallowed licenses are flagged as policy violations
- Unknown licenses (detection failed) are also flagged
- Manual overrides let you correct false positives

### Dependency Tree Analysis

Understand how dependencies enter your project:
- Visual tree showing direct and transitive dependencies
- License information at each level
- Circular dependency detection
- Problematic license warnings (GPL, AGPL, etc.)

### Compatibility Checking

Identify license conflicts:
- Matrix view of license compatibility
- Incompatible pairs highlighted
- Helps prevent legal issues from conflicting licenses

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - no issues found |
| 1 | Issues found - missing licenses, policy violations, or compatibility problems |
| 2 | Error - scan failed (configuration error, network issue, etc.) |

Use exit codes in CI/CD to gate deployments:

```yaml
# GitHub Actions example
- name: Check licenses
  run: license-analyzer scan --format json --output licenses.json

- name: Fail on license issues
  run: license-analyzer scan --quiet
```

## CLI Reference

### Global Options

```
--version    Show version and exit
--help       Show help message
```

### Scan Options

```
--format     Output format: terminal, json, markdown (default: terminal)
--output     Write to file instead of stdout
--verbose    Show detailed detection information
--quiet      Show only status and issues
--config     Path to configuration file
```

### Tree Options

```
--format     Output format: terminal, json, markdown (default: terminal)
--output     Write to file instead of stdout
--max-depth  Maximum depth to traverse (default: unlimited)
--verbose    Show detailed license source information
--quiet      Show only summary and problematic licenses
--config     Path to configuration file
```

### Matrix Options

```
--format     Output format: terminal, json, markdown (default: terminal)
--output     Write to file instead of stdout
--max-depth  Maximum depth for dependency analysis
--verbose    Show detailed compatibility reasoning
--quiet      Show only incompatibility summary
--config     Path to configuration file
```

## Examples

### CI/CD Integration

```bash
#!/bin/bash
# ci-license-check.sh

# Generate detailed report
license-analyzer scan --format markdown --output license-report.md

# Fail pipeline if issues found
license-analyzer scan --quiet
exit_code=$?

if [ $exit_code -eq 1 ]; then
    echo "License issues detected! Review license-report.md"
    exit 1
fi
```

### Finding Problematic Licenses

```bash
# Quick check for GPL/AGPL licenses in dependencies
license-analyzer tree --quiet
```

### Generating Compliance Reports

```bash
# Full compliance report
license-analyzer scan --format markdown --output compliance-report.md

# Include dependency tree
license-analyzer tree --format markdown --output dependency-tree.md

# Include compatibility analysis
license-analyzer matrix --format markdown --output compatibility-matrix.md
```

## Development

```bash
# Clone and setup
git clone https://github.com/your-org/license-analyzer.git
cd license-analyzer
uv sync

# Run tests
uv run pytest

# Run linting
uv run ruff check

# Run type checking
uv run mypy license_analyzer
```

## License

MIT

---

**Disclaimer:** This tool provides automated license detection to assist with compliance efforts. It is not legal advice. Always consult with legal counsel for license compliance decisions.
