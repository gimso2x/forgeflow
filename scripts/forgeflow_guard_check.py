#!/usr/bin/env python3
"""forgeflow_guard_check.py — Thin Guard artifact invariant checker.

Opt-in CLI that inspects ForgeFlow task directories and reports contract
violations. Does NOT mutate artifacts, execute stages, or repair files.

Uses Python standard library only — no external dependencies.

Exit codes:
    0 = PASS (all invariants satisfied)
    2 = BLOCK (contract violation found)
    1 = invalid invocation or internal error

Usage:
    forgeflow_guard_check.py check-task --task-dir <path> [--stage <stage>]
    forgeflow_guard_check.py check-clarify --task-dir <path>
    forgeflow_guard_check.py check-review --task-dir <path>
    forgeflow_guard_check.py check-ship --task-dir <path>
"""

import argparse
import json
import os
import re
import sys

from forgeflow_platform import configure_utf8_stdio

configure_utf8_stdio()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_text(path):
    """Read file text, return None if missing or unreadable."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def section_text(markdown, heading):
    """Extract the text under a ## heading until the next ## heading.

    Returns the text content (stripped) or empty string if heading not found.
    """
    if not markdown:
        return ""
    pattern = rf"^##\s+{re.escape(heading)}\s*$"
    lines = markdown.splitlines()
    capture = False
    collected = []
    for line in lines:
        if capture:
            if line.startswith("## "):
                break
            collected.append(line)
        elif re.match(pattern, line, re.IGNORECASE):
            capture = True
    return "\n".join(collected).strip()


def checkpoint_field(markdown, heading):
    """Extract a single-value checkpoint field under ## <heading>."""
    return section_text(markdown, heading)


BLOCK_MESSAGES = []


def emit_block(message):
    """Record a blocking violation message."""
    BLOCK_MESSAGES.append(message)
    print(f"BLOCK: {message}", file=sys.stderr)


def exit_for_blocks():
    """Exit with code 2 if any blocks were recorded, else exit 0."""
    if BLOCK_MESSAGES:
        return 2
    print("PASS")
    return 0


# ---------------------------------------------------------------------------
# check-task
# ---------------------------------------------------------------------------

VALID_STATUSES = {"in_progress", "completed", "blocked"}


def check_task(task_dir, expected_stage=None):
    """Validate task directory artifact invariants."""
    # checkpoint.md must exist and be non-empty
    cp_path = os.path.join(task_dir, "checkpoint.md")
    cp_text = read_text(cp_path)
    if cp_text is None:
        emit_block("checkpoint.md missing")
        return
    if not cp_text.strip():
        emit_block("checkpoint.md is empty")

    # run-state.json must parse as JSON if present
    rs_path = os.path.join(task_dir, "run-state.json")
    if os.path.exists(rs_path):
        rs_text = read_text(rs_path)
        if rs_text is not None:
            try:
                json.loads(rs_text)
            except json.JSONDecodeError:
                emit_block("run-state.json is not valid JSON")

    # Required sections in checkpoint.md
    current_stage = checkpoint_field(cp_text, "Current Stage")
    status = checkpoint_field(cp_text, "Status")
    next_action = checkpoint_field(cp_text, "Next Action")
    blockers = checkpoint_field(cp_text, "Blockers")

    if not current_stage:
        emit_block("checkpoint.md missing 'Current Stage' section")
    if not status:
        emit_block("checkpoint.md missing 'Status' section")
    if not next_action:
        emit_block("checkpoint.md missing 'Next Action' section")
    if blockers is None or blockers == "":
        # Blockers section must exist (even if "none")
        emit_block("checkpoint.md missing 'Blockers' section")

    # Status must be valid
    if status and status.lower() not in VALID_STATUSES:
        emit_block(f"invalid status '{status}', expected one of {VALID_STATUSES}")

    # Stage match if --stage provided
    if expected_stage and current_stage:
        if expected_stage.lower() != current_stage.lower().strip():
            emit_block(
                f"current stage '{current_stage.strip()}' does not match "
                f"expected '{expected_stage}'"
            )

    # Blocked status must have non-empty blockers
    if status and status.lower() == "blocked":
        if blockers and blockers.lower() == "none":
            emit_block("status is 'blocked' but blockers is 'none'")

    # Completed status must have non-empty next action
    if status and status.lower() == "completed":
        if not next_action:
            emit_block("status is 'completed' but 'Next Action' is empty")


# ---------------------------------------------------------------------------
# check-clarify
# ---------------------------------------------------------------------------

VALID_ROUTES = {"small", "medium", "high", "epic"}


def check_clarify(task_dir):
    """Validate clarify stage artifacts exist and contain required sections.

    This is the completion gate for the clarify stage. Every route (small,
    medium, high, epic) must produce these artifacts before proceeding.
    """
    # 1. run-state.json must exist and be valid JSON
    rs_path = os.path.join(task_dir, "run-state.json")
    rs_text = read_text(rs_path)
    if rs_text is None:
        emit_block("run-state.json missing — clarify must bootstrap task workspace")
        return
    try:
        json.loads(rs_text)
    except json.JSONDecodeError:
        emit_block("run-state.json is not valid JSON")

    # 2. brief.md must exist and be non-empty
    brief_path = os.path.join(task_dir, "brief.md")
    brief_text = read_text(brief_path)
    if brief_text is None:
        emit_block("brief.md missing — clarify must produce a brief")
        return
    if not brief_text.strip():
        emit_block("brief.md is empty")
        return

    # 3. brief.md must contain a route selection (in YAML frontmatter or body)
    route_found = False
    # Check YAML frontmatter for route: field
    if brief_text.startswith("---"):
        fm_end = brief_text.find("---", 3)
        if fm_end >= 0:
            frontmatter = brief_text[3:fm_end]
            for line in frontmatter.splitlines():
                stripped = line.strip()
                if stripped.startswith("route:"):
                    route_val = stripped.split(":", 1)[1].strip().strip("\"'")
                    if route_val in VALID_ROUTES:
                        route_found = True
                    else:
                        emit_block(
                            f"brief.md has invalid route '{route_val}', "
                            f"expected one of {VALID_ROUTES}"
                        )
                    break
    # Fallback: check body for Route section
    if not route_found:
        route_section = section_text(brief_text, "Route")
        if route_section:
            for route in VALID_ROUTES:
                if route in route_section.lower():
                    route_found = True
                    break
            if not route_found:
                emit_block(
                    f"brief.md Route section has no valid route, "
                    f"expected one of {VALID_ROUTES}"
                )
        elif not route_found:
            emit_block("brief.md missing route selection (frontmatter or Route section)")

    # 4. brief.md must contain Objective
    objective = section_text(brief_text, "Objective")
    if not objective:
        emit_block("brief.md missing 'Objective' section")

    # 5. brief.md must contain Goal Contract
    goal_contract = section_text(brief_text, "Goal Contract")
    if not goal_contract:
        emit_block("brief.md missing 'Goal Contract' section")


# ---------------------------------------------------------------------------
# check-review
# ---------------------------------------------------------------------------

def check_review(task_dir):
    """Validate review artifact invariants."""
    rr_path = os.path.join(task_dir, "review-report.md")
    rr_text = read_text(rr_path)
    if rr_text is None:
        emit_block("review-report.md missing")
        return

    # Check verdict
    verdict_line = section_text(rr_text, "Verdict")
    verdict_lower = verdict_line.lower().strip()

    if "approved" in verdict_lower:
        # Approved: open blockers must be empty
        open_blockers = section_text(rr_text, "Open Blockers")
        if open_blockers and open_blockers.lower().strip() != "none":
            # Check for actual blocker items (lines starting with -)
            blocker_lines = [
                line for line in open_blockers.splitlines()
                if line.strip().startswith("-") and line.strip() != "-"
            ]
            if blocker_lines:
                emit_block("approved review has open blockers")
            elif open_blockers.strip() and open_blockers.lower().strip() != "none":
                emit_block("approved review has open blockers")


# ---------------------------------------------------------------------------
# check-ship
# ---------------------------------------------------------------------------

def check_ship(task_dir):
    """Validate ship artifact invariants."""
    ss_path = os.path.join(task_dir, "ship-summary.md")
    ss_text = read_text(ss_path)
    if ss_text is None:
        emit_block("ship-summary.md missing")
        return

    # Evidence Manifest section must exist
    evidence = section_text(ss_text, "Evidence Manifest")
    if not evidence:
        emit_block("ship-summary.md missing 'Evidence Manifest' section")

    # review-report.md should exist
    rr_path = os.path.join(task_dir, "review-report.md")
    rr_text = read_text(rr_path)

    if rr_text is not None:
        # If review exists, check verdict
        verdict_line = section_text(rr_text, "Verdict")
        verdict_lower = verdict_line.lower().strip()

        if verdict_lower and "approved" not in verdict_lower:
            emit_block(
                f"cannot ship: review verdict is '{verdict_line.strip()}', not approved"
            )

        # If approved, check open blockers
        if "approved" in verdict_lower:
            open_blockers = section_text(rr_text, "Open Blockers")
            if open_blockers and open_blockers.lower().strip() != "none":
                blocker_lines = [
                    line for line in open_blockers.splitlines()
                    if line.strip().startswith("-") and line.strip() != "-"
                ]
                if blocker_lines:
                    emit_block("cannot ship: approved review has open blockers")
    else:
        # No review-report — only OK for small route self-verify
        # Check if ship summary mentions self-verify or small route
        ss_lower = ss_text.lower()
        if "self-verify" not in ss_lower and "small route" not in ss_lower:
            emit_block(
                "ship-summary.md has no review-report.md and does not record "
                "small route self-verify"
            )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class GuardArgumentParser(argparse.ArgumentParser):
    """Override argparse to exit 1 instead of 2 for usage errors."""

    def error(self, message):
        self.print_help(sys.stderr)
        print(f"\nError: {message}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = GuardArgumentParser(
        description="Thin Guard - ForgeFlow artifact invariant checker"
    )
    subparsers = parser.add_subparsers(dest="command")

    # check-task
    p_task = subparsers.add_parser("check-task", help="Check task directory invariants")
    p_task.add_argument("--task-dir", required=True, help="Path to task directory")
    p_task.add_argument("--stage", default=None, help="Expected current stage")

    # check-clarify
    p_clarify = subparsers.add_parser("check-clarify", help="Check clarify stage artifacts")
    p_clarify.add_argument("--task-dir", required=True, help="Path to task directory")

    # check-review
    p_review = subparsers.add_parser("check-review", help="Check review artifacts")
    p_review.add_argument("--task-dir", required=True, help="Path to task directory")

    # check-ship
    p_ship = subparsers.add_parser("check-ship", help="Check ship artifacts")
    p_ship.add_argument("--task-dir", required=True, help="Path to task directory")

    args = parser.parse_args()

    if not args.command:
        parser.print_help(sys.stderr)
        return 1

    # Validate task-dir exists
    if not os.path.isdir(args.task_dir):
        print(f"BLOCK: task-dir does not exist: {args.task_dir}", file=sys.stderr)
        return 1

    if args.command == "check-task":
        check_task(args.task_dir, args.stage)
    elif args.command == "check-clarify":
        check_clarify(args.task_dir)
    elif args.command == "check-review":
        check_review(args.task_dir)
    elif args.command == "check-ship":
        check_ship(args.task_dir)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1

    return exit_for_blocks()


if __name__ == "__main__":
    sys.exit(main())
