#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from forgeflow_platform import configure_utf8_stdio

configure_utf8_stdio()

SCRIPT_DIR: Final = Path(__file__).resolve().parent
GUARD_SCRIPT: Final = SCRIPT_DIR / "forgeflow_guard_check.py"


@dataclass(frozen=True, slots=True)
class GuardResult:
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True)
class TestResult:
    name: str
    passed: bool
    detail: str


def write_file(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def run_guard(args: list[str]) -> GuardResult:
    result = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return GuardResult(
        exit_code=result.returncode,
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
    )


def make_plan_dir(root: Path, *, include_steps: bool) -> Path:
    task_dir = root / ("plan-valid" if include_steps else "plan-missing-steps")
    task_dir.mkdir()
    plan = """# Plan

## 실행 준비도 (Plan Readiness)
- **Goal**: Add guardrails
- **Requirements**: R1
- **Implementation Steps**: T1
- **Verification**: make validate

## 요구사항 (Requirements)
- R1: Guard accepts valid artifacts

## 작업 목록 (Tasks)

### Task 1: Guard
- **Objective**: Add guard
- **Files**: scripts/forgeflow_guard_check.py
- **Depends on**: none
- **Expected output**: guard check
- **Verification**: python scripts/validate_stage_guard_checks.py
- **Fulfills**: R1

## 검증 계획 (Verification Plan)

### Check 1: R1
- **Type**: artifact
- **Gates**: validator
"""
    if not include_steps:
        plan = plan.replace("- **Implementation Steps**: T1\n", "")
    write_file(task_dir / "plan.md", plan)
    return task_dir


def make_execute_dir(root: Path, *, done_has_evidence: bool) -> Path:
    task_dir = root / ("execute-valid" if done_has_evidence else "execute-no-evidence")
    task_dir.mkdir()
    write_file(
        task_dir / "implementation-notes.md",
        """# Implementation Notes

## 현재 단계 (Current Stage)
execute

## 상태 (Status)
completed

## 증거 (Evidence)
- verification:PASS gate=test command="python scripts/validate_stage_guard_checks.py"

## Evidence Index
- evidence_index: task=Task 1 evidence=E-1 command="python scripts/validate_stage_guard_checks.py" exit=0 result=PASS artifact=inline

## 차단 요소 (Blocked By)
none
""",
    )
    evidence = "verification:PASS gate=test" if done_has_evidence else ""
    write_file(
        task_dir / "ledger.md",
        f"""---
schema: ledger/v1
task_id: guardrails
route: medium
total_items: 1
---

# Ledger

## Execution Tracking

### Task 1: Guardrails
- **Plan Step**: Task 1
- **Status**: done
- **Assignee**: worker
- **Claim Marker**: none
- **Evidence Refs**: {evidence}
- **Blocker**: none
- **Retry Count**: 0

## Gate Results

| Gate | Target | Result | Evidence |
|------|--------|--------|----------|
| test | guard | pass | E-1 |

## Completion Summary

- **Total Tasks**: 1
- **Completed**: 1
- **Blocked**: 0
- **Discarded**: 0
- **All Done**: yes
""",
    )
    write_file(
        task_dir / "checkpoint.md",
        """# Checkpoint

## Current Stage
execute

## Status
completed

## Active Task
none

## Resume Pointer
ledger.md#task-1 status=done retry=0 owner=worker next_update=none

## Next Action
invoke /forgeflow:ff-review

## Last Verified Evidence
evidence_index:task=Task 1 command="python scripts/validate_stage_guard_checks.py" exit=0 artifact=implementation-notes.md#Evidence

## Blockers
none
""",
    )
    return task_dir


def make_review_missing_human_gate_dir(root: Path) -> Path:
    task_dir = root / "review-missing-human-gate"
    task_dir.mkdir()
    write_file(
        task_dir / "review-report.md",
        """# Review Report

## 판정 (Verdict)
approved

## Safe for Next Stage
yes

## Open Blockers
none
""",
    )
    return task_dir


def make_empty_dir(root: Path, name: str) -> Path:
    task_dir = root / name
    task_dir.mkdir()
    return task_dir


def make_execute_missing_artifact_dir(root: Path, *, missing: str) -> Path:
    task_dir = root / f"execute-missing-{missing}"
    task_dir.mkdir()
    if missing != "notes":
        write_file(
            task_dir / "implementation-notes.md",
            """## Status
in_progress

## Current Stage
execute

## Blocked By
none
""",
        )
    if missing != "ledger":
        write_file(
            task_dir / "ledger.md",
            """### Task 1
- **Status**: done
- **Evidence Refs**: verification:PASS gate=test
""",
        )
    if missing != "checkpoint":
        write_file(
            task_dir / "checkpoint.md",
            """## Current Stage
execute

## Status
in_progress

## Next Action
continue

## Resume Pointer
Task 1 in progress

## Blockers
none
""",
        )
    return task_dir


def make_execute_completed_no_evidence_index_dir(root: Path) -> Path:
    task_dir = root / "execute-completed-no-eidx"
    task_dir.mkdir()
    write_file(
        task_dir / "implementation-notes.md",
        """## Status
completed

## Current Stage
execute

## Blocked By
none

## Evidence
- verification:PASS gate=test
""",
    )
    write_file(
        task_dir / "ledger.md",
        """### Task 1
- **Status**: done
- **Evidence Refs**: E-1

## All Done
- **All Done**: yes
""",
    )
    write_file(
        task_dir / "checkpoint.md",
        """## Resume Pointer
Task 1 done

## Current Stage
review

## Status
completed

## Next Action
review

## Blockers
none
""",
    )
    return task_dir


def make_ship_no_review_no_selfverify_dir(root: Path) -> Path:
    task_dir = root / "ship-no-review-no-selfverify"
    task_dir.mkdir()
    write_file(
        task_dir / "ship-summary.md",
        """## Evidence Manifest
- verification:PASS gate=lint command="pnpm lint"
""",
    )
    return task_dir


def make_ship_review_not_approved_dir(root: Path) -> Path:
    task_dir = root / "ship-review-not-approved"
    task_dir.mkdir()
    write_file(
        task_dir / "ship-summary.md",
        """## Evidence Manifest
- verification:PASS gate=lint command="pnpm lint"
""",
    )
    write_file(
        task_dir / "review-report.md",
        """## Verdict
changes_requested

## Open Blockers
- Critical bug found
""",
    )
    return task_dir


def make_ship_placeholder_manifest_dir(root: Path) -> Path:
    task_dir = root / "ship-placeholder-manifest"
    task_dir.mkdir()
    write_file(
        task_dir / "ship-summary.md",
        """# Ship Summary

## Evidence Manifest

| Gate | Command | Result | Evidence |
|------|---------|--------|----------|
| <!-- build/lint/type_check/test --> | <!-- actual command run --> | <!-- PASS --> | <!-- output --> |

small route self-verify
""",
    )
    return task_dir


def expect(name: str, result: GuardResult, expected_code: int, stderr_fragment: str | None = None) -> TestResult:
    fragment_ok = stderr_fragment is None or stderr_fragment.lower() in result.stderr.lower()
    passed = result.exit_code == expected_code and fragment_ok
    detail = f"exit={result.exit_code} stdout={result.stdout!r} stderr={result.stderr!r}"
    return TestResult(name=name, passed=passed, detail=detail)


def run_tests() -> list[TestResult]:
    with tempfile.TemporaryDirectory(prefix="forgeflow_stage_guard_") as tmp:
        root = Path(tmp)
        return [
            # ── check-plan ──
            expect("test_check_plan_valid_passes", run_guard(["check-plan", "--task-dir", str(make_plan_dir(root, include_steps=True))]), 0),
            expect(
                "test_check_plan_missing_implementation_steps_blocks",
                run_guard(["check-plan", "--task-dir", str(make_plan_dir(root, include_steps=False))]),
                2,
                "Implementation Steps",
            ),
            expect(
                "test_check_plan_missing_file_blocks",
                run_guard(["check-plan", "--task-dir", str(make_empty_dir(root, "plan-no-file"))]),
                2,
                "plan.md missing",
            ),
            # ── check-execute ──
            expect("test_check_execute_valid_passes", run_guard(["check-execute", "--task-dir", str(make_execute_dir(root, done_has_evidence=True))]), 0),
            expect(
                "test_check_execute_done_without_evidence_blocks",
                run_guard(["check-execute", "--task-dir", str(make_execute_dir(root, done_has_evidence=False))]),
                2,
                "Evidence Refs",
            ),
            expect(
                "test_check_execute_missing_notes_blocks",
                run_guard(["check-execute", "--task-dir", str(make_execute_missing_artifact_dir(root, missing="notes"))]),
                2,
                "implementation-notes.md missing",
            ),
            expect(
                "test_check_execute_missing_ledger_blocks",
                run_guard(["check-execute", "--task-dir", str(make_execute_missing_artifact_dir(root, missing="ledger"))]),
                2,
                "ledger.md missing",
            ),
            expect(
                "test_check_execute_missing_checkpoint_blocks",
                run_guard(["check-execute", "--task-dir", str(make_execute_missing_artifact_dir(root, missing="checkpoint"))]),
                2,
                "checkpoint.md missing",
            ),
            expect(
                "test_check_execute_completed_no_evidence_index_blocks",
                run_guard(["check-execute", "--task-dir", str(make_execute_completed_no_evidence_index_dir(root))]),
                2,
                "Evidence Index",
            ),
            # ── check-review ──
            expect(
                "test_check_review_missing_human_gate_blocks",
                run_guard(["check-review", "--task-dir", str(make_review_missing_human_gate_dir(root))]),
                2,
                "Human Review Gate",
            ),
            expect(
                "test_check_review_missing_file_blocks",
                run_guard(["check-review", "--task-dir", str(make_empty_dir(root, "review-no-file"))]),
                2,
                "review-report.md missing",
            ),
            # ── check-ship ──
            expect(
                "test_check_ship_empty_evidence_manifest_blocks",
                run_guard(["check-ship", "--task-dir", str(make_ship_placeholder_manifest_dir(root))]),
                2,
                "Evidence Manifest",
            ),
            expect(
                "test_check_ship_missing_file_blocks",
                run_guard(["check-ship", "--task-dir", str(make_empty_dir(root, "ship-no-file"))]),
                2,
                "ship-summary.md missing",
            ),
            expect(
                "test_check_ship_no_review_no_selfverify_blocks",
                run_guard(["check-ship", "--task-dir", str(make_ship_no_review_no_selfverify_dir(root))]),
                2,
                "no review-report.md and does not record small route",
            ),
            expect(
                "test_check_ship_review_not_approved_blocks",
                run_guard(["check-ship", "--task-dir", str(make_ship_review_not_approved_dir(root))]),
                2,
                "not approved",
            ),
        ]


def main() -> int:
    results = run_tests()
    passed = sum(1 for result in results if result.passed)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {result.name}")
        if not result.passed:
            print(f"         {result.detail}")
    failed = len(results) - passed
    print(f"\n{passed}/{len(results)} tests passed, {failed} failed")
    if failed:
        return 1
    print("\nOK: stage guard checks validate stage-specific invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
