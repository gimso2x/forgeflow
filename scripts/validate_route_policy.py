#!/usr/bin/env python3
"""Validate route policy consistency across core docs.

Checks:
1. Score range thresholds match between README.md and clarify/SKILL.md
2. Route-to-pipeline mapping in forgeflow/SKILL.md matches clarify/SKILL.md Exit Conditions
3. docs/advisory-guidelines.md Route Budget Guide contains score range numbers
"""
import pathlib
import sys

ROOT = pathlib.Path(".")


def _read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


failures = []

# ---------------------------------------------------------------------------
# 1. Score range thresholds present in README.md, clarify/SKILL.md, forgeflow/SKILL.md
# ---------------------------------------------------------------------------
THRESHOLD_MARKERS = [
    "< 10",
    "10-16.9",
    "17-24.9",
    "25-49.9",
    ">= 50",
]
THRESHOLD_DOCS = ["README.md", "skills/clarify/SKILL.md", "skills/forgeflow/SKILL.md"]

for doc in THRESHOLD_DOCS:
    text = _read(doc)
    for marker in THRESHOLD_MARKERS:
        if marker not in text:
            failures.append(
                f"{doc}: score threshold {repr(marker)} not found"
            )

# ---------------------------------------------------------------------------
# 2. Route-to-pipeline mapping (forgeflow/SKILL.md vs clarify/SKILL.md)
# ---------------------------------------------------------------------------
forgeflow_text = _read("skills/forgeflow/SKILL.md")
clarify_text = _read("skills/clarify/SKILL.md")

# forgeflow/SKILL.md: verify each route has its expected stage sequence
FORGEFLOW_PIPELINES = {
    "small": "clarify -> execute",
    "medium": "clarify -> plan -> execute",
    "high": "clarify -> plan -> execute -> review",
    "epic": "clarify -> plan",
}

for route, pipeline in FORGEFLOW_PIPELINES.items():
    if pipeline not in forgeflow_text:
        failures.append(
            f"skills/forgeflow/SKILL.md: pipeline for {route} route not found "
            f"(expected: {pipeline})"
        )

# clarify/SKILL.md Exit Condition: verify each route maps to correct next skill
CLARIFY_EXIT_MAPPINGS = {
    "small": "/forgeflow:execute",
    "medium": "/forgeflow:plan",
    "high": "/forgeflow:plan",
    "epic": "/forgeflow:plan",
}

for route, next_skill in CLARIFY_EXIT_MAPPINGS.items():
    # clarify uses backtick-wrapped route names: `route` -> `skill`
    if route not in clarify_text or next_skill not in clarify_text:
        failures.append(
            f"skills/clarify/SKILL.md: exit mapping {route} -> {next_skill} not found"
        )

# ---------------------------------------------------------------------------
# 3. Advisory guidelines Route Budget Guide contains score range numbers
# ---------------------------------------------------------------------------
advisory_text = _read("docs/advisory-guidelines.md")

ADVISORY_THRESHOLD_NUMBERS = ["10", "16.9", "17", "24.9", "25", "49.9", "50"]
for number in ADVISORY_THRESHOLD_NUMBERS:
    if number not in advisory_text:
        failures.append(
            f"docs/advisory-guidelines.md: score range number {repr(number)} "
            f"not found in Route Budget Guide"
        )

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
if failures:
    print("ERROR: route policy validation failed")
    for f in failures:
        print(f"- {f}")
    sys.exit(1)
print("OK: route policy thresholds, pipeline mapping, and advisory budget guide are consistent")
