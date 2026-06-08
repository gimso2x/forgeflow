#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NoReturn

from forgeflow_guard_core import (
    check_clarify,
    check_execute,
    check_plan,
    check_review,
    check_ship,
    check_task,
    exit_for_blocks,
)
from forgeflow_platform import configure_utf8_stdio

configure_utf8_stdio()


class GuardArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_help(sys.stderr)
        print(f"\nError: {message}", file=sys.stderr)
        raise SystemExit(1)


def main() -> int:
    parser = GuardArgumentParser(description="Thin Guard - ForgeFlow artifact invariant checker")
    subparsers = parser.add_subparsers(dest="command")

    p_task = subparsers.add_parser("check-task", help="Check task directory invariants")
    p_task.add_argument("--task-dir", required=True, help="Path to task directory")
    p_task.add_argument("--stage", default=None, help="Expected current stage")
    p_clarify = subparsers.add_parser("check-clarify", help="Check clarify stage artifacts")
    p_clarify.add_argument("--task-dir", required=True, help="Path to task directory")
    p_plan = subparsers.add_parser("check-plan", help="Check plan stage artifacts")
    p_plan.add_argument("--task-dir", required=True, help="Path to task directory")
    p_execute = subparsers.add_parser("check-execute", help="Check execute stage artifacts")
    p_execute.add_argument("--task-dir", required=True, help="Path to task directory")
    p_review = subparsers.add_parser("check-review", help="Check review artifacts")
    p_review.add_argument("--task-dir", required=True, help="Path to task directory")
    p_ship = subparsers.add_parser("check-ship", help="Check ship artifacts")
    p_ship.add_argument("--task-dir", required=True, help="Path to task directory")

    args = parser.parse_args()
    if not args.command:
        parser.print_help(sys.stderr)
        return 1

    task_dir = Path(args.task_dir)
    if not task_dir.is_dir():
        print(f"BLOCK: task-dir does not exist: {task_dir}", file=sys.stderr)
        return 1

    if args.command == "check-task":
        check_task(task_dir, args.stage)
    elif args.command == "check-clarify":
        check_clarify(task_dir)
    elif args.command == "check-plan":
        check_plan(task_dir)
    elif args.command == "check-execute":
        check_execute(task_dir)
    elif args.command == "check-review":
        check_review(task_dir)
    elif args.command == "check-ship":
        check_ship(task_dir)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1
    return exit_for_blocks()


if __name__ == "__main__":
    raise SystemExit(main())
