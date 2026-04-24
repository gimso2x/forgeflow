#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"pending", "in_progress", "completed", "failed", "blocked"}


def plan_path(task_dir: str) -> Path:
    return Path(task_dir).resolve() / "plan.json"


def load_plan(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"Error: plan.json not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_plan(path: Path, plan: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def schema_errors(plan: dict) -> list[str]:
    schema = json.loads((ROOT / "schemas/plan.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    return [format_schema_error(error) for error in sorted(validator.iter_errors(plan), key=lambda err: list(err.path))]


def format_schema_error(error) -> str:
    location = ".".join(str(part) for part in error.path)
    return f"{location or '<root>'}: {error.message}"


def traceability_errors(path: Path, plan: dict) -> list[str]:
    errors: list[str] = []
    steps = plan.get("steps", [])
    step_ids = {step.get("id") for step in steps}
    verify_plan = plan.get("verify_plan", [])
    verify_targets = {entry.get("target") for entry in verify_plan if entry.get("type") in {"sub_req", "step"}}
    journey_verify_targets = {entry.get("target") for entry in verify_plan if entry.get("type") == "journey"}
    journeys = plan.get("journeys", [])
    journey_ids = {journey.get("id") for journey in journeys}

    for step in steps:
        step_id = step.get("id")
        for dependency in step.get("dependencies", []) or []:
            if dependency not in step_ids:
                errors.append(f"step {step_id} depends on unknown step '{dependency}'")
        for fulfilled in step.get("fulfills", []) or []:
            if fulfilled not in verify_targets:
                errors.append(f"step {step_id} fulfills '{fulfilled}' has no verify_plan target")

    for journey in journeys:
        journey_id = journey.get("id")
        if journey_id not in journey_verify_targets:
            errors.append(f"journey {journey_id} has no verify_plan journey target")
        for composed in journey.get("composes", []) or []:
            if composed not in verify_targets:
                errors.append(f"journey {journey_id} composes '{composed}' has no verify_plan target")

    for journey_target in journey_verify_targets:
        if journey_target not in journey_ids:
            errors.append(f"verify_plan targets journey '{journey_target}' but no journey exists")

    contracts = plan.get("contracts") or {}
    artifact = contracts.get("artifact")
    if artifact is not None and not (path.parent / artifact).is_file():
        errors.append(f"contracts artifact {artifact} does not exist")

    return errors


def validate(path: Path) -> list[str]:
    plan = load_plan(path)
    return schema_errors(plan) + traceability_errors(path, plan)


def cmd_validate(args: argparse.Namespace) -> int:
    path = plan_path(args.task_dir)
    errors = validate(path)
    if errors:
        for error in errors:
            print(f"✗ {error}", file=sys.stderr)
        print(f"\n{len(errors)} error(s)", file=sys.stderr)
        return 1
    plan = load_plan(path)
    print(f"✓ plan.json valid — {len(plan.get('steps', []))} steps")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    path = plan_path(args.task_dir)
    errors = validate(path)
    if errors:
        for error in errors:
            print(f"✗ {error}", file=sys.stderr)
        return 1
    plan = load_plan(path)
    steps = plan.get("steps", [])
    if args.status:
        steps = [step for step in steps if step.get("status", "pending") == args.status]
    if args.json:
        print(json.dumps({"steps": steps, "filtered": len(steps), "total": len(plan.get("steps", []))}, ensure_ascii=False, indent=2))
        return 0
    if not steps:
        print(f"No steps" + (f" with status '{args.status}'" if args.status else ""))
        return 0
    print(f"{'ID':<16}{'STATUS':<14}OBJECTIVE")
    print("-" * 72)
    for step in steps:
        objective = step.get("objective", "")
        if len(objective) > 70:
            objective = objective[:67] + "..."
        print(f"{step.get('id',''):<16}{step.get('status','pending'):<14}{objective}")
    return 0


def cmd_task(args: argparse.Namespace) -> int:
    path = plan_path(args.task_dir)
    assignment = args.status
    if "=" not in assignment:
        print("Error: --status must be <step_id>=<status>", file=sys.stderr)
        return 1
    step_id, status = assignment.split("=", 1)
    if status not in STATUSES:
        print(f"Error: invalid status {status!r}; expected one of {sorted(STATUSES)}", file=sys.stderr)
        return 1
    plan = load_plan(path)
    steps = plan.get("steps", [])
    target = next((step for step in steps if step.get("id") == step_id), None)
    if target is None:
        print(f"Error: unknown step id {step_id!r}", file=sys.stderr)
        return 1
    current = target.get("status", "pending")
    if current == status:
        print(f"No change: {step_id} already {status}")
        return 0
    if current == "completed" and status != "completed":
        print(f"Error: completed step {step_id} cannot transition to {status}", file=sys.stderr)
        return 1
    target["status"] = status
    if args.summary:
        target["rollback_note"] = (target.get("rollback_note", "") + f"\nStatus note: {args.summary}").strip()
    errors = schema_errors(plan) + traceability_errors(path, plan)
    if errors:
        for error in errors:
            print(f"✗ {error}", file=sys.stderr)
        return 1
    write_plan(path, plan)
    print(f"Updated {step_id}: {current} -> {status}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ForgeFlow plan helper")
    sub = parser.add_subparsers(dest="command", required=True)
    p_validate = sub.add_parser("validate")
    p_validate.add_argument("task_dir")
    p_validate.set_defaults(func=cmd_validate)
    p_list = sub.add_parser("list")
    p_list.add_argument("task_dir")
    p_list.add_argument("--status", choices=sorted(STATUSES))
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)
    p_task = sub.add_parser("task")
    p_task.add_argument("task_dir")
    p_task.add_argument("--status", required=True)
    p_task.add_argument("--summary")
    p_task.set_defaults(func=cmd_task)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
