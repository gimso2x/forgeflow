#!/usr/bin/env python3
"""Render lightweight ForgeFlow planning artifacts as Mermaid/Markdown diagrams."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"artifact not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"artifact must be a JSON object: {path}")
    return payload


def _node_text(value: Any, fallback: str = "unknown") -> str:
    text = str(value if value not in (None, "") else fallback)
    return text.replace("\\", "\\\\").replace('"', "'").replace("\n", " ")


def _node_id(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_") or "node"


def render_clarify_mermaid(brief: dict[str, Any]) -> str:
    goal = _node_text(brief.get("goal") or brief.get("objective") or brief.get("title"), "unspecified")
    route = _node_text(brief.get("route") or brief.get("risk_level"), "unrouted")
    criteria = brief.get("acceptance_criteria") or []
    constraints = brief.get("constraints") or []
    if not isinstance(criteria, list):
        criteria = [criteria]
    if not isinstance(constraints, list):
        constraints = [constraints]

    lines = [
        "flowchart TD",
        f"  Goal[Goal: {goal}]",
        f"  Route[Route: {route}]",
        "  Goal --> Route",
    ]
    for index, criterion in enumerate(criteria, start=1):
        lines.append(f"  AC{index}[AC{index}: {_node_text(criterion)}]")
        lines.append(f"  Goal --> AC{index}")
    for index, constraint in enumerate(constraints, start=1):
        lines.append(f"  C{index}[Constraint {index}: {_node_text(constraint)}]")
        lines.append(f"  C{index} -.-> Goal")
    return "\n".join(lines) + "\n"


def render_plan_mermaid(plan: dict[str, Any]) -> str:
    steps = plan.get("steps") or []
    if not isinstance(steps, list):
        raise ValueError("plan steps must be a list")
    lines = ["flowchart TD"]
    ids: dict[str, str] = {}
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or f"step-{index}")
        node_id = _node_id(step_id)
        ids[step_id] = node_id
        label = _node_text(f"{step_id}: {step.get('objective') or step.get('expected_output') or 'unspecified'}")
        lines.append(f"  {node_id}[{label}]")
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or "")
        node_id = ids.get(step_id)
        for dependency in step.get("dependencies") or []:
            dep_id = ids.get(str(dependency))
            if dep_id and node_id:
                lines.append(f"  {dep_id} --> {node_id}")
    return "\n".join(lines) + "\n"


def render_plan_markdown(plan: dict[str, Any]) -> str:
    lines = ["## ForgeFlow Plan Diagram", "", "```mermaid", render_plan_mermaid(plan).rstrip(), "```", "", "### Verification"]
    verify_plan = plan.get("verify_plan") or []
    if isinstance(verify_plan, list) and verify_plan:
        for item in verify_plan:
            if not isinstance(item, dict):
                continue
            gates = item.get("gates") or []
            gate_text = ", ".join(str(gate) for gate in gates) if isinstance(gates, list) else str(gates)
            lines.append(f"- {_node_text(item.get('target'))}: {gate_text}")
    else:
        lines.append("- No verification gates recorded.")
    return "\n".join(lines) + "\n"


def render_review_mermaid(report: dict[str, Any]) -> str:
    verdict = _node_text(report.get("verdict"), "unknown")
    review_type = _node_text(report.get("review_type"), "review")
    blockers = report.get("open_blockers") or []
    findings = report.get("findings") or []
    lines = ["flowchart TD", f"  Review[Review: {review_type}]", f"  Verdict[Verdict: {verdict}]", "  Review --> Verdict"]
    for index, finding in enumerate(findings if isinstance(findings, list) else [findings], start=1):
        lines.append(f"  F{index}[Finding {index}: {_node_text(finding)}]")
        lines.append(f"  Review --> F{index}")
    for index, blocker in enumerate(blockers if isinstance(blockers, list) else [blockers], start=1):
        lines.append(f"  B{index}[Blocker {index}: {_node_text(blocker)}]")
        lines.append(f"  B{index} --> Verdict")
    return "\n".join(lines) + "\n"


def _render(stage: str, payload: dict[str, Any], output_format: str) -> str:
    if stage == "clarify":
        mermaid = render_clarify_mermaid(payload)
        title = "ForgeFlow Clarify Diagram"
    elif stage == "plan":
        if output_format == "markdown":
            return render_plan_markdown(payload)
        mermaid = render_plan_mermaid(payload)
        title = "ForgeFlow Plan Diagram"
    else:
        mermaid = render_review_mermaid(payload)
        title = "ForgeFlow Review Diagram"

    if output_format == "markdown":
        return f"## {title}\n\n```mermaid\n{mermaid.rstrip()}\n```\n"
    return mermaid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["clarify", "plan", "review"])
    parser.add_argument("artifact", type=Path, help="brief.json, plan.json, or review-report.json")
    parser.add_argument("--format", choices=["mermaid", "markdown"], default="mermaid")
    args = parser.parse_args(argv)

    try:
        payload = _load_json(args.artifact)
        sys.stdout.write(_render(args.stage, payload, args.format))
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
