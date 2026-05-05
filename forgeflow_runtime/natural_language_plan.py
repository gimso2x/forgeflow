"""Natural-language brief to ForgeFlow plan conversion.

This module is intentionally heuristic and stdlib-only.  It turns a brief,
issue body, or copied requirement text into a schema-valid ``plan.json`` draft
that agents can refine during the plan stage.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Iterable

from .complexity import assess_complexity
from .ears_parser import Requirement, parse_ears

_TEMPLATE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("bugfix", ("bug", "fix", "error", "failure", "regression", "broken", "버그", "실패", "수정", "오류")),
    ("refactor", ("refactor", "cleanup", "simplify", "split", "migrate", "리팩터", "정리", "분리", "마이그레이션")),
    ("new_feature", ("add", "create", "implement", "feature", "support", "추가", "구현", "생성", "지원")),
)

_VERIFICATION_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("test", "Run the focused test suite covering this requirement."),
    ("lint", "Run lint or static analysis for touched files."),
    ("build", "Run the project build or compile check."),
    ("docs", "Inspect rendered or generated documentation output."),
    ("문서", "Inspect rendered or generated documentation output."),
)


@dataclass(frozen=True)
class PlanDraft:
    """A generated plan draft plus quality signals."""

    plan: dict[str, Any]
    route: str
    template: str
    quality: dict[str, Any]


def _sentences(text: str) -> list[str]:
    items: list[str] = []
    for raw in re.split(r"[\n.;]+", text):
        cleaned = re.sub(r"^[-*\d.)\s]+", "", raw).strip()
        if cleaned:
            items.append(cleaned)
    return items


def _requirements_from_text(text: str) -> list[Requirement]:
    parsed = parse_ears(text)
    if parsed:
        return parsed
    from .ears_parser import EARSType

    return [Requirement(id=f"REQ-{idx:03d}", ears_type=EARSType.UNKNOWN, description=item, raw_line=item) for idx, item in enumerate(_sentences(text), start=1)]


def _select_template(text: str) -> str:
    lower = text.lower()
    scores = {name: sum(1 for keyword in keywords if keyword.lower() in lower) for name, keywords in _TEMPLATE_KEYWORDS}
    return max(scores, key=lambda name: (scores[name], name)) if any(scores.values()) else "new_feature"


def _verification_for(requirement: Requirement, template: str) -> str:
    lower = requirement.description.lower()
    if template == "bugfix":
        return "Reproduce or cover the failing path, then run the focused regression test."
    for keyword, verification in _VERIFICATION_KEYWORDS:
        if keyword in lower:
            return verification
    if template == "refactor":
        return "Run existing tests for the refactored surface and confirm behavior is unchanged."
    return "Run the smallest available focused verification for the implemented change."


def _step_objective(requirement: Requirement, template: str) -> str:
    prefix = {
        "bugfix": "Fix",
        "refactor": "Refactor",
        "new_feature": "Implement",
    }.get(template, "Implement")
    return f"{prefix}: {requirement.description}"


def _dedupe_requirements(requirements: Iterable[Requirement]) -> list[Requirement]:
    seen: set[str] = set()
    unique: list[Requirement] = []
    for req in requirements:
        key = re.sub(r"\s+", " ", req.description.strip().lower())
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(req)
    return unique


def github_issue_text(issue_number: int | str, *, repo: str | None = None) -> tuple[str, list[str]]:
    """Collect GitHub issue title/body text via ``gh issue view``.

    Returns ``(text, refs)`` where refs contains a traceable ``#N`` token.  The
    function is isolated so callers/tests can avoid shelling out when they
    already have issue text.
    """
    issue = str(issue_number).lstrip("#")
    cmd = ["gh", "issue", "view", issue, "--json", "number,title,body"]
    if repo:
        cmd.extend(["--repo", repo])
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    payload = json.loads(proc.stdout)
    number = payload.get("number", issue)
    title = payload.get("title") or ""
    body = payload.get("body") or ""
    return f"{title}\n\n{body}".strip(), [f"#{number}"]


def generate_plan_from_issue(task_id: str, issue_number: int | str, *, repo: str | None = None) -> PlanDraft:
    """Generate a plan draft directly from a GitHub issue collected by gh CLI."""
    text, refs = github_issue_text(issue_number, repo=repo)
    return generate_plan_from_text(task_id, text, issue_refs=refs)


def generate_plan_from_text(task_id: str, text: str, *, issue_refs: Iterable[str] = ()) -> PlanDraft:
    """Generate a schema-valid ForgeFlow plan draft from natural language.

    The output is deterministic, stdlib-only, and deliberately conservative:
    every extracted requirement maps to at least one step and one verify_plan
    entry.  ``issue_refs`` can include GitHub issue/PR identifiers that should
    be preserved in step outputs for traceability.
    """
    if not task_id.strip():
        raise ValueError("task_id is required")
    if not text.strip():
        raise ValueError("text is required")

    requirements = _dedupe_requirements(_requirements_from_text(text))
    if not requirements:
        raise ValueError("text did not contain any plannable requirements")

    template = _select_template(text)
    complexity = assess_complexity(text)
    route = complexity.route_name
    refs = list(issue_refs)

    steps: list[dict[str, Any]] = []
    for idx, req in enumerate(requirements, start=1):
        step_id = f"step-{idx}"
        expected = f"Requirement {req.id} is implemented with evidence."
        if refs:
            expected += f" Trace refs: {', '.join(refs)}."
        step: dict[str, Any] = {
            "id": step_id,
            "objective": _step_objective(req, template),
            "dependencies": [f"step-{idx - 1}"] if idx > 1 else [],
            "expected_output": expected,
            "verification": _verification_for(req, template),
            "fulfills": [req.id],
            "status": "pending",
        }
        steps.append(step)

    verify_plan = [
        {"target": req.id, "type": "sub_req", "gates": [step["id"]]}
        for req, step in zip(requirements, steps)
    ]
    verify_plan.append({"target": "end-to-end", "type": "journey", "gates": [step["id"] for step in steps]})

    plan = {
        "schema_version": "0.1",
        "task_id": task_id,
        "steps": steps,
        "verify_plan": verify_plan,
    }
    quality = validate_plan_draft(plan, requirement_ids=[req.id for req in requirements])
    return PlanDraft(plan=plan, route=route, template=template, quality=quality)


def validate_plan_draft(plan: dict[str, Any], *, requirement_ids: Iterable[str]) -> dict[str, Any]:
    """Return lightweight completeness/goodness signals for a generated plan."""
    steps = plan.get("steps", []) if isinstance(plan, dict) else []
    verify_plan = plan.get("verify_plan", []) if isinstance(plan, dict) else []
    required = set(requirement_ids)
    fulfilled = {item for step in steps for item in step.get("fulfills", [])}
    verify_targets = {entry.get("target") for entry in verify_plan if isinstance(entry, dict)}
    missing_requirements = sorted(required - fulfilled)
    missing_verification = sorted(required - verify_targets)
    dependency_ids = {dep for step in steps for dep in step.get("dependencies", [])}
    step_ids = {step.get("id") for step in steps}
    unknown_dependencies = sorted(dep for dep in dependency_ids if dep not in step_ids)
    ok = bool(steps) and not missing_requirements and not missing_verification and not unknown_dependencies
    return {
        "ok": ok,
        "step_count": len(steps),
        "missing_requirements": missing_requirements,
        "missing_verification": missing_verification,
        "unknown_dependencies": unknown_dependencies,
    }
