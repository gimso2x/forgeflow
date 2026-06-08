from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Final

VALID_STATUSES: Final = {"in_progress", "completed", "blocked"}
VALID_ROUTES: Final = {"small", "medium", "high", "epic"}
VALID_VERDICTS: Final = {"approved", "changes_requested", "blocked"}
VALID_LEDGER_STATUSES: Final = {"pending", "in_progress", "blocked", "done", "discarded"}

BLOCK_MESSAGES: list[str] = []


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def heading_matches(line: str, heading: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("## "):
        return False
    title = stripped.lstrip("#").strip().lower()
    target = heading.lower()
    return title == target or f"({target})" in title or target in title


def section_text(markdown: str | None, heading: str) -> str:
    if not markdown:
        return ""
    capture = False
    collected: list[str] = []
    for line in markdown.splitlines():
        if capture:
            if line.startswith("## "):
                break
            collected.append(line)
        elif heading_matches(line, heading):
            capture = True
    return "\n".join(collected).strip()


def emit_block(message: str) -> None:
    BLOCK_MESSAGES.append(message)
    print(f"BLOCK: {message}", file=sys.stderr)


def exit_for_blocks() -> int:
    if BLOCK_MESSAGES:
        return 2
    print("PASS")
    return 0


def has_placeholder(text: str) -> bool:
    return "<!--" in text or bool(re.search(r"<[^>\n]+>", text))


def has_real_evidence(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--") or stripped.startswith("|---"):
            continue
        if has_placeholder(stripped):
            continue
        if re.search(r"\b(PASS|FAIL|SKIPPED|pass|fail|skip|approved|blocked)\b", stripped):
            return True
    return False


def _validate_checkpoint_fields(cp_text: str, expected_stage: str | None) -> None:
    current_stage = section_text(cp_text, "Current Stage")
    status = section_text(cp_text, "Status")
    next_action = section_text(cp_text, "Next Action")
    blockers = section_text(cp_text, "Blockers")

    if not current_stage:
        emit_block("checkpoint.md missing 'Current Stage' section")
    if not status:
        emit_block("checkpoint.md missing 'Status' section")
    if not next_action:
        emit_block("checkpoint.md missing 'Next Action' section")
    if not blockers:
        emit_block("checkpoint.md missing 'Blockers' section")
    if status and status.lower() not in VALID_STATUSES:
        emit_block(f"invalid status '{status}', expected one of {VALID_STATUSES}")
    if expected_stage and current_stage and expected_stage.lower() != current_stage.lower().strip():
        emit_block(f"current stage '{current_stage.strip()}' does not match expected '{expected_stage}'")
    if status and status.lower() == "blocked" and blockers and blockers.lower() == "none":
        emit_block("status is 'blocked' but blockers is 'none'")
    if status and status.lower() == "completed" and not next_action:
        emit_block("status is 'completed' but 'Next Action' is empty")


def check_task(task_dir: Path, expected_stage: str | None = None) -> None:
    cp_text = read_text(task_dir / "checkpoint.md")
    if cp_text is None:
        emit_block("checkpoint.md missing")
        return
    if not cp_text.strip():
        emit_block("checkpoint.md is empty")

    rs_path = task_dir / "run-state.json"
    if rs_path.exists():
        rs_text = read_text(rs_path)
        if rs_text is not None:
            try:
                json.loads(rs_text)
            except json.JSONDecodeError:
                emit_block("run-state.json is not valid JSON")

    _validate_checkpoint_fields(cp_text, expected_stage)


def _validate_brief_route(brief_text: str) -> None:
    route_found = False
    if brief_text.startswith("---"):
        fm_end = brief_text.find("---", 3)
        if fm_end >= 0:
            for line in brief_text[3:fm_end].splitlines():
                stripped = line.strip()
                if stripped.startswith("route:"):
                    route_val = stripped.split(":", 1)[1].strip().strip("\"'")
                    if route_val in VALID_ROUTES:
                        route_found = True
                    else:
                        emit_block(f"brief.md has invalid route '{route_val}', expected one of {VALID_ROUTES}")
                    break
    if not route_found:
        route_section = section_text(brief_text, "Route")
        if route_section:
            route_found = any(route in route_section.lower() for route in VALID_ROUTES)
            if not route_found:
                emit_block(f"brief.md Route section has no valid route, expected one of {VALID_ROUTES}")
        else:
            emit_block("brief.md missing route selection (frontmatter or Route section)")


def check_clarify(task_dir: Path) -> None:
    rs_text = read_text(task_dir / "run-state.json")
    if rs_text is None:
        emit_block("run-state.json missing - clarify must bootstrap task workspace")
        return
    try:
        json.loads(rs_text)
    except json.JSONDecodeError:
        emit_block("run-state.json is not valid JSON")

    brief_text = read_text(task_dir / "brief.md")
    if brief_text is None:
        emit_block("brief.md missing - clarify must produce a brief")
        return
    if not brief_text.strip():
        emit_block("brief.md is empty")
        return

    _validate_brief_route(brief_text)

    if not section_text(brief_text, "Objective"):
        emit_block("brief.md missing 'Objective' section")
    if not section_text(brief_text, "Goal Contract"):
        emit_block("brief.md missing 'Goal Contract' section")


def check_plan(task_dir: Path) -> None:
    plan_text = read_text(task_dir / "plan.md")
    if plan_text is None:
        emit_block("plan.md missing")
        return
    readiness = section_text(plan_text, "Plan Readiness")
    for field in ("Goal", "Requirements", "Implementation Steps", "Verification"):
        if field not in readiness:
            emit_block(f"plan.md Plan Readiness missing '{field}'")
    if not section_text(plan_text, "Tasks"):
        emit_block("plan.md missing 'Tasks' section")
    if not section_text(plan_text, "Verification Plan"):
        emit_block("plan.md missing 'Verification Plan' section")
    if has_placeholder(readiness):
        emit_block("plan.md Plan Readiness contains unresolved placeholders")


def ledger_done_tasks_missing_evidence(ledger_text: str) -> list[str]:
    missing: list[str] = []
    current_task = ""
    current_status = ""
    current_evidence = ""
    for line in [*ledger_text.splitlines(), "### END"]:
        if line.startswith("### "):
            if current_task and current_status == "done" and not current_evidence:
                missing.append(current_task)
            current_task = line.removeprefix("### ").strip()
            current_status = ""
            current_evidence = ""
            continue
        stripped = line.strip()
        if stripped.startswith("- **Status**:"):
            current_status = stripped.split(":", 1)[1].strip()
            if current_status and current_status not in VALID_LEDGER_STATUSES:
                emit_block(f"ledger.md invalid status '{current_status}'")
        if stripped.startswith("- **Evidence Refs**:"):
            current_evidence = stripped.split(":", 1)[1].strip()
    return missing


def check_execute(task_dir: Path) -> None:
    notes_text = read_text(task_dir / "implementation-notes.md")
    if notes_text is None:
        emit_block("implementation-notes.md missing")
        return
    ledger_text = read_text(task_dir / "ledger.md")
    if ledger_text is None:
        emit_block("ledger.md missing")
        return
    checkpoint_text = read_text(task_dir / "checkpoint.md")
    if checkpoint_text is None:
        emit_block("checkpoint.md missing")
        return

    status = section_text(notes_text, "Status").lower()
    if status and status not in VALID_STATUSES:
        emit_block(f"implementation-notes.md invalid status '{status}'")
    if not section_text(notes_text, "Current Stage"):
        emit_block("implementation-notes.md missing 'Current Stage' section")
    if status == "completed" and not section_text(notes_text, "Evidence Index"):
        emit_block("implementation-notes.md completed without Evidence Index")
    if not section_text(notes_text, "Blocked By"):
        emit_block("implementation-notes.md missing 'Blocked By' section")
    for task in ledger_done_tasks_missing_evidence(ledger_text):
        emit_block(f"ledger.md done task '{task}' missing Evidence Refs")
    if "All Done" in ledger_text and "All Done**: yes" in ledger_text and not has_real_evidence(section_text(notes_text, "Evidence")):
        emit_block("implementation-notes.md Evidence has no real completed gate")
    if not section_text(checkpoint_text, "Resume Pointer"):
        emit_block("checkpoint.md missing 'Resume Pointer' section")


def check_review(task_dir: Path) -> None:
    rr_text = read_text(task_dir / "review-report.md")
    if rr_text is None:
        emit_block("review-report.md missing")
        return
    verdict = section_text(rr_text, "Verdict").lower().strip()
    if not verdict:
        emit_block("review-report.md missing 'Verdict' section")
    elif verdict not in VALID_VERDICTS:
        emit_block(f"review-report.md invalid verdict '{verdict}'")
    if verdict == "approved":
        open_blockers = section_text(rr_text, "Open Blockers")
        if open_blockers and open_blockers.lower().strip() != "none":
            emit_block("approved review has open blockers")
        safe_next = section_text(rr_text, "Safe for Next Stage")
        if safe_next and "yes" in safe_next.lower() and not section_text(rr_text, "Human Review Gate"):
            emit_block("approved review missing 'Human Review Gate' section")


def check_ship(task_dir: Path) -> None:
    ss_text = read_text(task_dir / "ship-summary.md")
    if ss_text is None:
        emit_block("ship-summary.md missing")
        return
    evidence = section_text(ss_text, "Evidence Manifest")
    if not evidence:
        emit_block("ship-summary.md missing 'Evidence Manifest' section")
    elif has_placeholder(evidence) or not has_real_evidence(evidence):
        emit_block("ship-summary.md Evidence Manifest has no real gate evidence")

    rr_text = read_text(task_dir / "review-report.md")
    if rr_text is None:
        ss_lower = ss_text.lower()
        if "self-verify" not in ss_lower and "small route" not in ss_lower:
            emit_block("ship-summary.md has no review-report.md and does not record small route self-verify")
        return
    verdict = section_text(rr_text, "Verdict")
    verdict_lower = verdict.lower().strip()
    if verdict_lower and "approved" not in verdict_lower:
        emit_block(f"cannot ship: review verdict is '{verdict.strip()}', not approved")
    if "approved" in verdict_lower:
        open_blockers = section_text(rr_text, "Open Blockers")
        if open_blockers and open_blockers.lower().strip() != "none":
            emit_block("cannot ship: approved review has open blockers")
