#!/usr/bin/env python3
"""Validate that large ForgeFlow skill docs stay modularized through references."""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(".")
SKILLS_ROOT = ROOT / "skills"

# These are intentionally the currently large, high-churn workflow skills named in
# the maintainer backlog. The guard does not ban long contracts; it requires that
# long contracts externalize operational policy and adapter detail into linked refs.
LARGE_SKILLS = {
    "clarify": {
        "max_inline_bytes": 34_000,
        "required_dependencies": [
            "skills/_shared/discipline.md",
            "skills/_shared/isolation.md",
            "skills/_shared/context-resume.md",
        ],
        "required_references": ["references/scope-grounding.md"],
    },
    "ff-plan": {
        "max_inline_bytes": 30_000,
        "required_dependencies": [
            "skills/_shared/discipline.md",
            "skills/_shared/isolation.md",
            "skills/_shared/automation.md",
            "skills/_shared/context-resume.md",
        ],
        "required_references": ["references/epic-decomposition.md"],
    },
    "execute": {
        "max_inline_bytes": 40_000,
        "required_dependencies": [
            "skills/_shared/preflight.md",
            "skills/_shared/discipline.md",
            "skills/_shared/automation.md",
            "skills/_shared/context-resume.md",
        ],
        "required_references": [
            "references/testing-discipline.md",
            "references/agent-delegation.md",
            "references/adapter-output-and-metrics.md",
        ],
    },
    "ff-review": {
        "max_inline_bytes": 40_000,
        "required_dependencies": [
            "skills/_shared/discipline.md",
            "skills/_shared/isolation.md",
            "skills/_shared/preflight.md",
            "skills/_shared/automation.md",
            "skills/_shared/context-resume.md",
        ],
        "required_references": [
            "references/standalone-mode.md",
            "references/input-normalization.md",
            "references/role-checklists.md",
            "references/pipeline-procedure.md",
        ],
    },
    "ship": {
        "max_inline_bytes": 45_000,
        "required_dependencies": [
            "skills/_shared/discipline.md",
            "skills/_shared/automation.md",
            "skills/_shared/isolation.md",
            "skills/_shared/context-resume.md",
            "skills/_shared/preflight.md",
        ],
        "required_references": [
            "references/branch-disposition.md",
            "references/evolution-extraction.md",
        ],
    },
}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def frontmatter(text: str, path: pathlib.Path) -> str:
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise AssertionError(f"{path}: missing YAML frontmatter")
    return match.group(1)


def bullets_under_heading(text: str, heading: str) -> list[str]:
    marker = f"## {heading}"
    start = text.find(marker)
    if start == -1:
        return []
    next_heading = text.find("\n## ", start + len(marker))
    section = text[start : next_heading if next_heading != -1 else len(text)]
    return [line.strip()[2:].strip() for line in section.splitlines() if line.strip().startswith("- ")]


def validate() -> list[str]:
    failures: list[str] = []
    policy_doc = ROOT / "docs" / "skill-modularization.md"
    if not policy_doc.is_file():
        failures.append("docs/skill-modularization.md: missing modularization policy")
    else:
        policy_text = policy_doc.read_text(encoding="utf-8")
        for fragment in [
            "Keep SKILL.md focused on stage contracts",
            "Move repeated policy into skills/_shared/",
            "Move adapter-specific behavior into references/",
            "validate-skill-modularity",
        ]:
            if fragment not in policy_text:
                failures.append(f"docs/skill-modularization.md: missing {fragment!r}")

    for skill, cfg in LARGE_SKILLS.items():
        skill_path = SKILLS_ROOT / skill / "SKILL.md"
        if not skill_path.is_file():
            failures.append(f"{skill_path}: missing")
            continue
        text = skill_path.read_text(encoding="utf-8")
        fm = frontmatter(text, skill_path)
        size = len(text.encode("utf-8"))
        if size > cfg["max_inline_bytes"]:
            failures.append(
                f"{skill_path}: {size} bytes exceeds modularity budget {cfg['max_inline_bytes']} bytes"
            )
        for dep in cfg["required_dependencies"]:
            if dep not in fm:
                failures.append(f"{skill_path}: frontmatter dependencies missing {dep}")
        refs = bullets_under_heading(text, "Reference inventory")
        if not refs:
            failures.append(f"{skill_path}: missing '## Reference inventory' section")
        for rel_ref in cfg["required_references"]:
            ref_path = SKILLS_ROOT / skill / rel_ref
            if not ref_path.is_file():
                failures.append(f"{ref_path}: required reference missing")
            if rel_ref not in text:
                failures.append(f"{skill_path}: Reference inventory must link {rel_ref}")
        for line in refs:
            matches = re.findall(r"\(([^)]+\.md)\)", line)
            if not matches:
                failures.append(f"{skill_path}: Reference inventory row lacks markdown link: {line}")
                continue
            for target in matches:
                target_path = (skill_path.parent / target).resolve()
                try:
                    target_path.relative_to(ROOT.resolve())
                except ValueError:
                    failures.append(f"{skill_path}: reference escapes repo: {target}")
                    continue
                if not target_path.is_file():
                    failures.append(f"{skill_path}: linked reference does not exist: {target}")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("ERROR: skill modularity drift")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)
    print("OK: large workflow skills externalize policy into shared references")
