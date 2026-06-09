#!/usr/bin/env python3
"""Validate context refresh/resume wiring across skills, checkpoint, automation, and README."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(".")

CORE_SKILLS = [
    ROOT / "skills" / "forgeflow" / "SKILL.md",
    ROOT / "skills" / "clarify" / "SKILL.md",
    ROOT / "skills" / "ff-plan" / "SKILL.md",
    ROOT / "skills" / "execute" / "SKILL.md",
    ROOT / "skills" / "ff-review" / "SKILL.md",
    ROOT / "skills" / "ship" / "SKILL.md",
]

STAGES = ["clarify", "plan", "execute", "review", "ship"]


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []

    # 1. README references _shared/context-resume.md
    readme = _read(ROOT / "README.md")
    if "skills/_shared/context-resume.md" not in readme:
        failures.append("README must document context refresh/resume rules")

    # 2. Each core skill references _shared/context-resume.md
    for skill_path in CORE_SKILLS:
        text = _read(skill_path)
        if "_shared/context-resume.md" not in text:
            failures.append(f"{skill_path} must reference shared context refresh/resume rules")

    # 3. context-resume.md has 'Checkpoint-first'
    cr = _read(ROOT / "skills" / "_shared" / "context-resume.md")
    if "Checkpoint-first" not in cr:
        failures.append("context-resume rules must keep checkpoint-first guidance")

    # 4. context-resume.md has 'No default full re-read'
    if "No default full re-read" not in cr:
        failures.append("context-resume rules must guard against full artifact rereads")

    # 5. checkpoint.md has 'Minimum Read Set'
    ckpt = _read(ROOT / "templates" / "checkpoint.md")
    if "Minimum Read Set" not in ckpt:
        failures.append("checkpoint template must expose a Minimum Read Set for context refresh resume")

    # 6. checkpoint.md has 'Handoff Boundary'
    if "Handoff Boundary" not in ckpt:
        failures.append("checkpoint template must expose stage handoff boundary ownership")

    # 7. automation.md has 'Handoff Boundary'
    auto = _read(ROOT / "skills" / "_shared" / "automation.md")
    if "Handoff Boundary" not in auto:
        failures.append("automation rules must require checkpoint handoff boundary ownership")

    # 8. Per-stage ownership line in automation.md
    for stage in STAGES:
        needle = f"- **{stage}** — owns"
        if needle not in auto:
            failures.append(f"automation stage catalog must define owned artifacts for {stage}")

    # 9. automation.md has Allowed posture / Forbidden / forbidden-action handoff
    if "Allowed posture:" not in auto:
        failures.append("automation stage catalog must define allowed tool posture")
    if "Forbidden:" not in auto:
        failures.append("automation stage catalog must define forbidden tool posture")
    if "If a stage needs an action listed as forbidden" not in auto:
        failures.append("automation stage catalog must define forbidden-action handoff behavior")

    # 10. README has 'forbidden-action delegation'
    if "forbidden-action delegation" not in readme:
        failures.append("README context refresh docs must mention checkpoint handoff boundary ownership")

    if failures:
        for f in failures:
            print(f"ERROR: {f}")
        return 1

    print("OK: Context refresh/resume guidance is wired into core skills, checkpoint template, and stage boundary catalog")
    return 0


if __name__ == "__main__":
    sys.exit(main())
