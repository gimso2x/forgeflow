#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forgeflow_runtime.orchestrator import (  # noqa: E402
    RuntimeViolation,
    advance_to_next_stage,
    escalate_route,
    load_runtime_policy,
    resume_task,
    retry_stage,
    run_route,
    start_task,
    status_summary,
    step_back,
)


def _print_payload(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ForgeFlow minimal stage-machine orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="initialize a new task directory with route-owned artifacts")
    start_parser.add_argument("--task-dir", required=True)
    start_parser.add_argument("--route", required=True)

    run_parser = subparsers.add_parser("run", help="run an entire route end-to-end")
    run_parser.add_argument("--task-dir", required=True)
    run_parser.add_argument("--route", required=True)

    resume_parser = subparsers.add_parser("resume", help="reload task state from session-state and checkpoint artifacts")
    resume_parser.add_argument("--task-dir", required=True)
    resume_parser.add_argument("--route", required=True)

    status_parser = subparsers.add_parser("status", help="show current task status from canonical artifacts")
    status_parser.add_argument("--task-dir", required=True)
    status_parser.add_argument("--route", required=True)

    advance_parser = subparsers.add_parser("advance", help="advance one stage forward")
    advance_parser.add_argument("--task-dir", required=True)
    advance_parser.add_argument("--route", required=True)
    advance_parser.add_argument("--current-stage", required=True)

    retry_parser = subparsers.add_parser("retry", help="retry the current stage within budget")
    retry_parser.add_argument("--task-dir", required=True)
    retry_parser.add_argument("--stage", required=True)
    retry_parser.add_argument("--max-retries", type=int, default=2)

    step_back_parser = subparsers.add_parser("step-back", help="rewind to the previous stage")
    step_back_parser.add_argument("--task-dir", required=True)
    step_back_parser.add_argument("--route", required=True)
    step_back_parser.add_argument("--current-stage", required=True)

    escalate_parser = subparsers.add_parser("escalate", help="escalate a route to large_high_risk")
    escalate_parser.add_argument("--task-dir", required=True)
    escalate_parser.add_argument("--from-route", required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    task_dir = Path(getattr(args, "task_dir")).resolve()
    policy = load_runtime_policy(ROOT)

    try:
        if args.command == "start":
            _print_payload(start_task(task_dir=task_dir, policy=policy, route_name=args.route))
        elif args.command == "run":
            _print_payload(run_route(task_dir=task_dir, policy=policy, route_name=args.route))
        elif args.command == "resume":
            _print_payload(resume_task(task_dir=task_dir, policy=policy, route_name=args.route))
        elif args.command == "status":
            _print_payload(status_summary(task_dir=task_dir, policy=policy, route_name=args.route))
        elif args.command == "advance":
            _print_payload(
                {"next_stage": advance_to_next_stage(task_dir=task_dir, policy=policy, route_name=args.route, current_stage=args.current_stage).next_stage}
            )
        elif args.command == "retry":
            _print_payload(retry_stage(task_dir=task_dir, stage_name=args.stage, max_retries=args.max_retries))
        elif args.command == "step-back":
            _print_payload(
                step_back(task_dir=task_dir, policy=policy, route_name=args.route, current_stage=args.current_stage)
            )
        elif args.command == "escalate":
            _print_payload(escalate_route(task_dir=task_dir, from_route=args.from_route))
        else:
            parser.error(f"unknown command: {args.command}")
    except RuntimeViolation as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
