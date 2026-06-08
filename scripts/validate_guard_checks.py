#!/usr/bin/env python3
"""validate_guard_checks.py — TDD validator for forgeflow_guard_check.py

Builds temporary fixture task directories, runs the guard checker via
subprocess, and asserts exact exit codes and key output substrings.
Deletes temp fixtures after each run.

Usage:
    python3 scripts/validate_guard_checks.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GUARD_SCRIPT = os.path.join(SCRIPT_DIR, "forgeflow_guard_check.py")
PYTHON = sys.executable


def run_guard(args):
    """Run the guard checker with given args, return (exit_code, stdout, stderr)."""
    cmd = [PYTHON, GUARD_SCRIPT] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def make_valid_task_dir(tmp, stage="execute", status="in_progress"):
    """Create a valid task directory with checkpoint.md and run-state.json."""
    task_dir = os.path.join(tmp, "valid-task")
    os.makedirs(task_dir, exist_ok=True)

    checkpoint = f"""# Checkpoint

## Current Stage
{stage}

## Status
{status}

## Next Action
Run verification

## Blockers
none
"""
    with open(os.path.join(task_dir, "checkpoint.md"), "w") as f:
        f.write(checkpoint)

    run_state = {"task_id": "test-task", "project_slug": "test"}
    with open(os.path.join(task_dir, "run-state.json"), "w") as f:
        json.dump(run_state, f)

    return task_dir


def make_missing_checkpoint_dir(tmp):
    """Create a task directory with no checkpoint.md."""
    task_dir = os.path.join(tmp, "missing-checkpoint")
    os.makedirs(task_dir, exist_ok=True)
    return task_dir


def make_stage_mismatch_dir(tmp):
    """Create a task directory where checkpoint stage is 'plan'."""
    task_dir = os.path.join(tmp, "mismatch-task")
    os.makedirs(task_dir, exist_ok=True)
    checkpoint = f"""# Checkpoint

## Current Stage
plan

## Status
in_progress

## Next Action
Begin plan

## Blockers
none
"""
    with open(os.path.join(task_dir, "checkpoint.md"), "w") as f:
        f.write(checkpoint)
    return task_dir


def make_review_approved_with_blockers_dir(tmp):
    """Create a task directory with approved review but non-empty blockers."""
    task_dir = os.path.join(tmp, "review-blocked")
    os.makedirs(task_dir, exist_ok=True)

    review = """# Review Report

## Verdict
approved

## Open Blockers
- Critical bug in auth flow
- Missing error handling for edge case
"""
    with open(os.path.join(task_dir, "review-report.md"), "w") as f:
        f.write(review)

    checkpoint = """# Checkpoint

## Current Stage
review

## Status
completed

## Next Action
Ship

## Blockers
none
"""
    with open(os.path.join(task_dir, "checkpoint.md"), "w") as f:
        f.write(checkpoint)

    return task_dir


def make_review_approved_no_blockers_dir(tmp):
    """Create a task directory with approved review and empty blockers."""
    task_dir = os.path.join(tmp, "review-clean")
    os.makedirs(task_dir, exist_ok=True)

    review = """# Review Report

## Verdict
approved

## Open Blockers
none
"""
    with open(os.path.join(task_dir, "review-report.md"), "w") as f:
        f.write(review)

    return task_dir


def make_ship_valid_dir(tmp):
    """Create a valid ship directory with approved review and ship summary."""
    task_dir = os.path.join(tmp, "ship-valid")
    os.makedirs(task_dir, exist_ok=True)

    review = """# Review Report

## Verdict
approved

## Open Blockers
none
"""
    with open(os.path.join(task_dir, "review-report.md"), "w") as f:
        f.write(review)

    ship = """# Ship Summary

## Evidence Manifest
- make validate-guard-checks: PASS
- scope_boundary_check: PASS
"""
    with open(os.path.join(task_dir, "ship-summary.md"), "w") as f:
        f.write(ship)

    return task_dir


def make_ship_blocked_review_dir(tmp):
    """Create a ship directory with non-approved review."""
    task_dir = os.path.join(tmp, "ship-blocked-review")
    os.makedirs(task_dir, exist_ok=True)

    review = """# Review Report

## Verdict
changes_requested

## Open Blockers
- Fix auth flow
"""
    with open(os.path.join(task_dir, "review-report.md"), "w") as f:
        f.write(review)

    ship = """# Ship Summary

## Evidence Manifest
- make validate: FAIL
"""
    with open(os.path.join(task_dir, "ship-summary.md"), "w") as f:
        f.write(ship)

    return task_dir


def make_checkpoint_blocked_with_blockers_dir(tmp):
    """Create a task directory with blocked status and non-empty blockers."""
    task_dir = os.path.join(tmp, "blocked-with-reason")
    os.makedirs(task_dir, exist_ok=True)

    checkpoint = """# Checkpoint

## Current Stage
execute

## Status
blocked

## Next Action
Resolve dependency

## Blockers
- External API rate limit exceeded
"""
    with open(os.path.join(task_dir, "checkpoint.md"), "w") as f:
        f.write(checkpoint)

    return task_dir


def make_checkpoint_blocked_empty_blockers_dir(tmp):
    """Create a task directory with blocked status but empty blockers."""
    task_dir = os.path.join(tmp, "blocked-empty")
    os.makedirs(task_dir, exist_ok=True)

    checkpoint = """# Checkpoint

## Current Stage
execute

## Status
blocked

## Next Action
Resolve issue

## Blockers
none
"""
    with open(os.path.join(task_dir, "checkpoint.md"), "w") as f:
        f.write(checkpoint)

    return task_dir


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

class TestResult:
    def __init__(self, name, passed, detail=""):
        self.name = name
        self.passed = passed
        self.detail = detail


def run_tests():
    """Run all guard check tests. Returns list of TestResult."""
    results = []

    # Verify guard script exists
    if not os.path.exists(GUARD_SCRIPT):
        print(f"RED: guard script not found at {GUARD_SCRIPT}")
        results.append(TestResult(
            "guard_script_exists", False,
            f"forgeflow_guard_check.py not found at {GUARD_SCRIPT}"
        ))
        return results

    tmp = tempfile.mkdtemp(prefix="forgeflow_guard_test_")
    try:
        # Test 1: check-task valid fixture passes
        valid_dir = make_valid_task_dir(tmp)
        code, stdout, stderr = run_guard(
            ["check-task", "--task-dir", valid_dir, "--stage", "execute"]
        )
        results.append(TestResult(
            "test_check_task_valid_fixture_passes",
            code == 0 and "PASS" in stdout,
            f"exit={code} stdout={stdout!r} stderr={stderr!r}"
        ))

        # Test 2: check-task missing checkpoint blocks
        missing_dir = make_missing_checkpoint_dir(tmp)
        code, stdout, stderr = run_guard(
            ["check-task", "--task-dir", missing_dir, "--stage", "execute"]
        )
        results.append(TestResult(
            "test_check_task_missing_checkpoint_blocks",
            code == 2 and "BLOCK" in stderr and "checkpoint" in stderr.lower(),
            f"exit={code} stdout={stdout!r} stderr={stderr!r}"
        ))

        # Test 3: check-task stage mismatch blocks
        mismatch_dir = make_stage_mismatch_dir(tmp)
        code, stdout, stderr = run_guard(
            ["check-task", "--task-dir", mismatch_dir, "--stage", "execute"]
        )
        results.append(TestResult(
            "test_check_task_stage_mismatch_blocks",
            code == 2 and "BLOCK" in stderr and "stage" in stderr.lower(),
            f"exit={code} stdout={stdout!r} stderr={stderr!r}"
        ))

        # Test 4: check-review approved with blockers blocks
        review_blocked_dir = make_review_approved_with_blockers_dir(tmp)
        code, stdout, stderr = run_guard(
            ["check-review", "--task-dir", review_blocked_dir]
        )
        results.append(TestResult(
            "test_check_review_approved_with_blockers_blocks",
            code == 2 and "BLOCK" in stderr and "blocker" in stderr.lower(),
            f"exit={code} stdout={stdout!r} stderr={stderr!r}"
        ))

        # Test 5: check-review approved no blockers passes
        review_clean_dir = make_review_approved_no_blockers_dir(tmp)
        code, stdout, stderr = run_guard(
            ["check-review", "--task-dir", review_clean_dir]
        )
        results.append(TestResult(
            "test_check_review_approved_no_blockers_passes",
            code == 0 and "PASS" in stdout,
            f"exit={code} stdout={stdout!r} stderr={stderr!r}"
        ))

        # Test 6: check-ship valid passes
        ship_valid_dir = make_ship_valid_dir(tmp)
        code, stdout, stderr = run_guard(
            ["check-ship", "--task-dir", ship_valid_dir]
        )
        results.append(TestResult(
            "test_check_ship_valid_passes",
            code == 0 and "PASS" in stdout,
            f"exit={code} stdout={stdout!r} stderr={stderr!r}"
        ))

        # Test 7: check-ship blocked by non-approved review
        ship_blocked_dir = make_ship_blocked_review_dir(tmp)
        code, stdout, stderr = run_guard(
            ["check-ship", "--task-dir", ship_blocked_dir]
        )
        results.append(TestResult(
            "test_check_ship_blocked_review_blocks",
            code == 2 and "BLOCK" in stderr,
            f"exit={code} stdout={stdout!r} stderr={stderr!r}"
        ))

        # Test 8: check-task blocked status with empty blockers is invalid
        blocked_empty_dir = make_checkpoint_blocked_empty_blockers_dir(tmp)
        code, stdout, stderr = run_guard(
            ["check-task", "--task-dir", blocked_empty_dir]
        )
        results.append(TestResult(
            "test_check_task_blocked_empty_blockers_invalid",
            code == 2 and "BLOCK" in stderr,
            f"exit={code} stdout={stdout!r} stderr={stderr!r}"
        ))

        # Test 9: hook wrapper artifact guard invokes checker
        # (Tested via direct bash invocation in manual QA;
        #  here we verify the guard script accepts the same args)
        code, stdout, stderr = run_guard(
            ["check-task", "--task-dir", valid_dir, "--stage", "execute"]
        )
        results.append(TestResult(
            "test_hook_wrapper_args_compatible",
            code == 0,
            f"exit={code} stdout={stdout!r} stderr={stderr!r}"
        ))

        # Test 10: invalid subcommand returns exit 1
        code, stdout, stderr = run_guard(["invalid-cmd", "--task-dir", valid_dir])
        results.append(TestResult(
            "test_invalid_subcommand_exits_1",
            code == 1,
            f"exit={code} stdout={stdout!r} stderr={stderr!r}"
        ))

        # Test 11: missing --task-dir returns exit 1
        code, stdout, stderr = run_guard(["check-task"])
        results.append(TestResult(
            "test_missing_task_dir_exits_1",
            code == 1,
            f"exit={code} stdout={stdout!r} stderr={stderr!r}"
        ))

        code, stdout, stderr = run_guard(["--help"])
        results.append(TestResult(
            "test_help_output_is_ascii_safe",
            code == 0 and "Thin Guard - ForgeFlow artifact invariant checker" in stdout,
            f"exit={code} stdout={stdout!r} stderr={stderr!r}"
        ))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return results


def main():
    results = run_tests()
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.name}")
        if not r.passed:
            print(f"         {r.detail}")

    print(f"\n{passed}/{len(results)} tests passed, {failed} failed")

    if failed > 0:
        sys.exit(1)
    else:
        print("\nOK: guard checks validate artifact invariants")
        sys.exit(0)


if __name__ == "__main__":
    main()
