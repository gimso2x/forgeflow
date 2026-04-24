#!/usr/bin/env python3
"""Summarize local ForgeFlow task artifacts without mutating them."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ARTIFACTS = ("run-state.json", "review-report.json", "eval-record.json", "decision-log.json")


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"{path.name}: {exc.msg}"
    if not isinstance(data, dict):
        return None, f"{path.name}: expected object"
    return data, None


def discover_tasks(tasks_root: Path, recent: int) -> list[Path]:
    if not tasks_root.exists() or not tasks_root.is_dir():
        return []
    task_dirs = [path for path in tasks_root.iterdir() if path.is_dir()]
    task_dirs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    if recent > 0:
        return task_dirs[:recent]
    return task_dirs


def _first_string(*values: Any, default: str = "unknown") -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return default


def _review_status(review: dict[str, Any] | None) -> str:
    if not review:
        return "missing"
    if review.get("approved") is True or review.get("status") in {"approved", "pass", "passed"}:
        return "approved"
    if review.get("approved") is False or review.get("status") in {"rejected", "fail", "failed"}:
        return "rejected"
    return "unknown"


def _finding_messages(review: dict[str, Any] | None) -> list[str]:
    if not review:
        return []
    messages: list[str] = []
    for finding in review.get("findings", []) or []:
        if isinstance(finding, dict):
            message = _first_string(finding.get("message"), finding.get("summary"), finding.get("title"), default="")
        else:
            message = str(finding)
        if message:
            messages.append(message)
    return messages


def summarize_task(task_dir: Path) -> dict[str, Any]:
    artifacts: dict[str, dict[str, Any] | None] = {}
    errors: list[str] = []
    for name in ARTIFACTS:
        data, error = load_json(task_dir / name)
        artifacts[name] = data
        if error:
            errors.append(error)

    run_state = artifacts["run-state.json"] or {}
    review = artifacts["review-report.json"]
    eval_record = artifacts["eval-record.json"] or {}
    decision_log = artifacts["decision-log.json"] or {}

    task_id = _first_string(run_state.get("task_id"), run_state.get("id"), task_dir.name)
    route = _first_string(run_state.get("route"), run_state.get("complexity_route"))
    stage = _first_string(run_state.get("current_stage"), run_state.get("stage"))
    status = _first_string(run_state.get("status"))
    review_status = _review_status(review)
    eval_status = _first_string(eval_record.get("status"), eval_record.get("verdict"), default="missing")

    failure_messages: list[str] = []
    for key in ("blocked_reason", "error_message", "failure_reason"):
        value = run_state.get(key)
        if isinstance(value, str) and value:
            failure_messages.append(value)
    for key in ("reason", "decision", "summary"):
        value = decision_log.get(key)
        if isinstance(value, str) and value and status in {"blocked", "error", "failed"}:
            failure_messages.append(value)
    if review_status == "rejected":
        failure_messages.extend(_finding_messages(review))

    return {
        "task_id": task_id,
        "path": str(task_dir),
        "route": route,
        "current_stage": stage,
        "status": status,
        "review_status": review_status,
        "eval_status": eval_status,
        "failure_messages": failure_messages,
        "artifact_errors": errors,
    }


def build_report(task_dirs: list[Path]) -> dict[str, Any]:
    tasks = [summarize_task(path) for path in task_dirs]
    summary = {
        "total_tasks": len(tasks),
        "completed": sum(1 for task in tasks if task["status"] == "completed"),
        "blocked": sum(1 for task in tasks if task["status"] == "blocked"),
        "error": sum(1 for task in tasks if task["status"] in {"error", "failed"}),
        "unknown": sum(1 for task in tasks if task["status"] == "unknown"),
        "review_rejected": sum(1 for task in tasks if task["review_status"] == "rejected"),
        "review_approved": sum(1 for task in tasks if task["review_status"] == "approved"),
        "artifact_errors": sum(len(task["artifact_errors"]) for task in tasks),
    }
    patterns = Counter(message for task in tasks for message in task["failure_messages"])
    return {
        "summary": summary,
        "top_failure_patterns": [
            {"message": message, "count": count} for message, count in patterns.most_common(10)
        ],
        "tasks": tasks,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# ForgeFlow monitor summary",
        "",
        f"Total tasks: {summary['total_tasks']}",
        f"Completed: {summary['completed']}",
        f"Blocked: {summary['blocked']}",
        f"Error: {summary['error']}",
        f"Review rejected: {summary['review_rejected']}",
        f"Artifact errors: {summary['artifact_errors']}",
        "",
        "## Top failure patterns",
        "",
    ]
    patterns = report["top_failure_patterns"]
    if patterns:
        lines.extend(f"- {item['message']} ({item['count']})" for item in patterns)
    else:
        lines.append("- None")
    lines.extend([
        "",
        "## Tasks",
        "",
        "| task | route | stage | status | review |",
        "|---|---|---|---|---|",
    ])
    for task in report["tasks"]:
        lines.append(
            f"| {task['task_id']} | {task['route']} | {task['current_stage']} | {task['status']} | {task['review_status']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default=".forgeflow/tasks", help="Path to the ForgeFlow tasks directory")
    parser.add_argument("--recent", type=int, default=10, help="Number of most recently modified task directories to inspect; <=0 means all")
    parser.add_argument("--format", choices=["md", "json"], default="md")
    parser.add_argument("--output", help="Optional file path to write the report")
    args = parser.parse_args(argv)

    task_dirs = discover_tasks(Path(args.tasks), args.recent)
    report = build_report(task_dirs)
    if args.format == "json":
        content = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    else:
        content = render_markdown(report)

    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
