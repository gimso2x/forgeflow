"""CI/CD gate check module for ForgeFlow.

Provides artifact existence checks, JSON schema validation,
and GitHub Actions workflow generation.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GateCheckResult:
    """Result of a CI gate check run."""

    passed: bool
    gate_name: str
    message: str
    required_artifacts: list[str]
    missing_artifacts: list[str]
    errors: list[str]


@dataclass(frozen=True)
class CIGateConfig:
    """Configuration for CI gate checks."""

    required_artifacts: list[str] = field(default_factory=lambda: ["review-report.json"])
    artifact_dirs: list[str] = field(default_factory=lambda: [".forgeflow/artifacts"])
    fail_on_missing: bool = True
    check_schema: bool = True


def check_artifact_exists(path: str) -> bool:
    """Return True if *path* points to an existing regular file."""
    return os.path.isfile(path)


def scan_artifacts(config: CIGateConfig) -> list[str]:
    """Scan *artifact_dirs* and return basenames of all found files."""
    found: list[str] = []
    for directory in config.artifact_dirs:
        if not os.path.isdir(directory):
            continue
        for entry in os.listdir(directory):
            full = os.path.join(directory, entry)
            if os.path.isfile(full):
                found.append(entry)
    return found


def run_gate_check(config: CIGateConfig) -> GateCheckResult:
    """Execute the CI gate check against *config*."""
    found = scan_artifacts(config)
    missing = [a for a in config.required_artifacts if a not in found]
    passed = len(missing) == 0

    errors: list[str] = []
    if config.check_schema:
        for directory in config.artifact_dirs:
            if not os.path.isdir(directory):
                continue
            for name in config.required_artifacts:
                if name not in found:
                    continue
                fpath = os.path.join(directory, name)
                try:
                    with open(fpath, encoding="utf-8") as fh:
                        json.load(fh)
                except (json.JSONDecodeError, OSError) as exc:
                    errors.append(f"Schema error in {name}: {exc}")

    if errors:
        passed = False

    status = "PASS" if passed else "FAIL"
    parts: list[str] = [f"Gate check {status}"]
    if missing:
        parts.append(f"Missing: {', '.join(missing)}")
    if errors:
        parts.append(f"Errors: {'; '.join(errors)}")
    message = ". ".join(parts)

    return GateCheckResult(
        passed=passed,
        gate_name="ci-gate",
        message=message,
        required_artifacts=list(config.required_artifacts),
        missing_artifacts=missing,
        errors=errors,
    )


def format_gate_result(result: GateCheckResult) -> str:
    """Return a human-readable summary of a gate check result."""
    status = "PASS" if result.passed else "FAIL"
    lines = [f"[{status}] {result.gate_name}: {result.message}"]
    if result.missing_artifacts:
        lines.append(f"  Missing artifacts: {', '.join(result.missing_artifacts)}")
    if result.errors:
        lines.append("  Errors:")
        for err in result.errors:
            lines.append(f"    - {err}")
    return "\n".join(lines)


def generate_github_actions_workflow(config: CIGateConfig) -> str:
    """Return a GitHub Actions workflow YAML string for the gate check."""
    return (
        "name: ForgeFlow Gate Check\n"
        "on: [pull_request]\n"
        "jobs:\n"
        "  gate-check:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - uses: actions/setup-python@v5\n"
        "        with:\n"
        "          python-version: '3.11'\n"
        "      - run: pip install -e .\n"
        "      - name: ForgeFlow Gate Check\n"
        "        run: python -m forgeflow_runtime.ci_gate --check\n"
    )


def generate_pr_template(required_stages: list[str]) -> str:
    """Return a PR template markdown with a stage checklist."""
    items = "\n".join(f"- [ ] {stage}" for stage in required_stages)
    return (
        "# Pull Request\n\n"
        "## Checklist\n\n"
        f"{items}\n"
    )


if __name__ == "__main__":
    import sys

    cfg = CIGateConfig()
    result = run_gate_check(cfg)
    print(format_gate_result(result))
    sys.exit(0 if result.passed else 1)
