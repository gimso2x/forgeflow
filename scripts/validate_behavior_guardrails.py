#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CHECKS = {
    "docs/advisory-guidelines.md": ["Think Before Coding", "Simplicity First", "Surgical Changes", "Goal-Driven Execution"],
    "skills/_shared/discipline.md": ["docs/advisory-guidelines.md", "Behavioral Guardrails"],
    "templates/brief.md": ["Assumptions and Interpretation", "Selected interpretation", "Open ambiguity"],
    "templates/plan.md": ["Simplicity Check", "Rejected abstraction/flexibility"],
    "skills/ff-review/references/role-checklists.md": ["Behavioral Guardrail Review", "overengineering", "speculative"],
    "templates/review-report.md": ["assumption-risk", "drive-by-refactor"],
    "README.md": ["coding agent behavior guardrails", "make validate-behavior-guardrails"],
}
errors=[]
for rel, needles in CHECKS.items():
    text=(ROOT/rel).read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text: errors.append(f"{rel}: missing {needle!r}")
if errors:
    print("ERROR: behavior guardrail validation failed")
    print("\n".join(f"- {e}" for e in errors))
    raise SystemExit(1)
print("OK: behavior guardrails are wired across docs, templates, skills, and README")
