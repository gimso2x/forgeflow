#!/usr/bin/env python3
"""Fail fast when current ForgeFlow surfaces drift to old route/schema vocabulary."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CURRENT_ROUTE_FILES = [
    "README.md",
    "INSTALL.md",
    "SKILL.md",
    "AGENTS.md",
    "docs/runtime-adapters.md",
    "docs/architecture.md",
    "docs/artifact-model.md",
    "docs/checkpoint-model.md",
    "docs/workflow.md",
    "docs/concepts/route-model.md",
    "docs/concepts/review-model.md",
    ".claude-plugin/skills/clarify.md",
    "skills/execute/SKILL.md",
    "skills/plan/SKILL.md",
    "prompts/canonical/coordinator.md",
    "adapters/targets/claude/agents/forgeflow-coordinator.md",
    "adapters/targets/codex/agents/forgeflow-coordinator.md",
    "adapters/targets/gemini/agents/forgeflow-coordinator.md",
]

FORBIDDEN_CURRENT_PHRASES = [
    "large_high_risk",
    "route=large",
    "medium/large route",
    "medium/large routes",
    "small/medium/large",
    "clarify → run",
    "plan → run",
    "run → review",
    "run → finish",
    "schema_version exactly 0.1",
    "schema_version: \"0.1\"",
]

FORBIDDEN_ROUTE_PHRASE_EXCEPTIONS = {
    "large_high_risk": {"README.md", "INSTALL.md"},
}

REQUIRED_CURRENT_PHRASES = {
    "prompts/canonical/coordinator.md": "ForgeFlow route labels are exactly `small`, `medium`, `high`, and `epic`",
    "adapters/targets/gemini/agents/forgeflow-coordinator.md": "ForgeFlow route labels are exactly `small`, `medium`, `high`, and `epic`",
    "docs/concepts/route-model.md": "네 가지 Route",
    "docs/concepts/review-model.md": "execute",
    "docs/architecture.md": "Current version: `0.2`, minimum supported: `0.1`.",
}

LEGACY_EXAMPLE_FILES = [
    "docs/legacy/skills/01-clarify.md",
    "docs/legacy/skills/03-plan.md",
    "docs/spec-kit-borrow-handoff.md",
]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def main() -> int:
    errors: list[str] = []

    for rel in CURRENT_ROUTE_FILES:
        text = _read(rel)
        for phrase in FORBIDDEN_CURRENT_PHRASES:
            if phrase in text and rel not in FORBIDDEN_ROUTE_PHRASE_EXCEPTIONS.get(phrase, set()):
                errors.append(f"{rel}: stale current vocabulary: {phrase}")

    for rel, phrase in REQUIRED_CURRENT_PHRASES.items():
        if phrase not in _read(rel):
            errors.append(f"{rel}: missing required current vocabulary: {phrase}")

    # schema_version 0.1 is allowed only as migration input or legacy/example material.
    for rel in LEGACY_EXAMPLE_FILES:
        text = _read(rel)
        if "0.1" in text and "legacy/example" not in text:
            errors.append(f"{rel}: schema_version 0.1 example must be marked legacy/example")

    if errors:
        print("VOCABULARY DRIFT: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("VOCABULARY DRIFT: PASS")
    print(f"- current surfaces checked: {len(CURRENT_ROUTE_FILES)}")
    print("- schema_version 0.1 legacy/example boundaries checked")
    print("- stale run/medium-large route vocabulary checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
