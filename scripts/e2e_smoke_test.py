#!/usr/bin/env python3
"""E2E smoke test — validates ForgeFlow runtime can handle a full task lifecycle.

This script exercises the runtime library end-to-end:
1. Create a task directory with brief
2. Auto-route based on risk
3. Create plan-ledger (medium route)
4. Write run-state with progress
5. Write review-report
6. Validate all artifacts against schema
7. Enforce stage gates

Exit 0 = all smoke checks pass. Non-zero = failure.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Ensure forgeflow_runtime is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def smoke_lifecycle() -> tuple[list[str], list[str]]:
    """Run full task lifecycle and return (checks, errors)."""
    from forgeflow_runtime.artifact_validation import (
        validate_artifact_payload,
        SCHEMA_BY_ARTIFACT,
    )
    from forgeflow_runtime.operator_routing import auto_route_for_task_dir
    from forgeflow_runtime.gate_evaluation import enforce_stage_gate
    from forgeflow_runtime.policy_loader import load_runtime_policy

    checks: list[str] = []
    errors: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp)
        task_id = "smoke-001"

        # 1. Create brief (use risk_level key — that's what auto_route reads)
        brief = {
            "schema_version": "0.1",
            "task_id": task_id,
            "objective": "Smoke test — verify runtime lifecycle",
            "in_scope": ["module imports", "artifact validation", "gate enforcement"],
            "out_of_scope": ["performance benchmarks"],
            "constraints": ["no external dependencies"],
            "acceptance_criteria": ["all checks pass"],
            "risk_level": "medium",
        }
        brief_path = task_dir / "brief.json"
        _write_json(brief_path, brief)
        try:
            validate_artifact_payload(artifact_name="brief", payload=brief, source_name="smoke")
            checks.append("PASS: brief.json validated")
        except Exception as e:
            errors.append(f"FAIL: brief validation: {e}")

        # 2. Auto-route
        try:
            route = auto_route_for_task_dir(task_dir)
            assert route == "medium", f"expected medium, got {route}"
            checks.append(f"PASS: auto-route → {route}")
        except Exception as e:
            errors.append(f"FAIL: auto-route: {e}")

        # 3. Create plan-ledger (with route field so auto_route can read it)
        plan = {
            "schema_version": "0.1",
            "task_id": task_id,
            "route": "medium",
            "tasks": [
                {
                    "id": "t1",
                    "description": "Verify imports",
                    "acceptance_criteria": ["all modules import"],
                    "dependencies": [],
                    "status": "pending",
                    "complexity": "low",
                }
            ],
            "status": "planned",
        }
        plan_path = task_dir / "plan-ledger.json"
        _write_json(plan_path, plan)
        try:
            loaded = _read_json(plan_path)
            assert loaded["task_id"] == task_id
            # Verify auto_route can pick up route from plan-ledger
            route2 = auto_route_for_task_dir(task_dir)
            assert route2 == "medium", f"expected medium from plan, got {route2}"
            checks.append("PASS: plan-ledger write/read + route pickup")
        except Exception as e:
            errors.append(f"FAIL: plan-ledger: {e}")

        # 4. Write run-state
        run_state = {
            "schema_version": "0.1",
            "task_id": task_id,
            "current_stage": "quality-review",
            "status": "completed",
            "completed_gates": ["clarify", "plan", "execute", "spec-review", "quality-review"],
            "failed_gates": [],
            "retries": {},
            "spec_review_approved": True,
            "quality_review_approved": True,
            "progress": {
                "total_tasks": 1,
                "done": 1,
                "in_progress": 0,
                "pending": 0,
                "blocked": 0,
                "cancelled": 0,
                "percent": 100,
            },
        }
        run_path = task_dir / "run-state.json"
        _write_json(run_path, run_state)
        try:
            validate_artifact_payload(artifact_name="run-state", payload=run_state, source_name="smoke")
            checks.append("PASS: run-state.json validated")
        except Exception as e:
            errors.append(f"FAIL: run-state validation: {e}")

        # 5. Write review-report (approved requires approved_by + next_action, no extra props)
        review = {
            "schema_version": "0.1",
            "task_id": task_id,
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["No issues found — all checks pass"],
            "approved_by": "e2e-smoke-test",
            "next_action": "ship",
            "safe_for_next_stage": True,
            "open_blockers": [],
        }
        review_path = task_dir / "review-report-quality.json"
        _write_json(review_path, review)
        try:
            validate_artifact_payload(artifact_name="review-report", payload=review, source_name="smoke")
            checks.append("PASS: review-report.json validated")
        except Exception as e:
            errors.append(f"FAIL: review-report validation: {e}")

        # 6. Stage gate enforcement (load policy from repo)
        try:
            policy = load_runtime_policy(REPO_ROOT)
            enforce_stage_gate(task_dir, policy, "review", canonical_task_id=task_id)
            checks.append("PASS: review gate enforcement")
        except Exception as e:
            errors.append(f"FAIL: review gate: {e}")

        # 7. All artifact schemas covered
        try:
            checks.append(f"PASS: {len(SCHEMA_BY_ARTIFACT)} artifact schemas registered")
        except Exception as e:
            errors.append(f"FAIL: artifact schemas: {e}")

    return checks, errors


def smoke_imports() -> tuple[list[str], list[str]]:
    """Verify all runtime modules import cleanly."""
    import importlib
    import pkgutil
    import forgeflow_runtime

    checks: list[str] = []
    errors: list[str] = []

    mods = sorted(
        m.name
        for m in pkgutil.walk_packages(forgeflow_runtime.__path__, prefix="forgeflow_runtime.")
    )
    failed = []
    for m in mods:
        try:
            importlib.import_module(m)
        except Exception as e:
            failed.append((m, str(e)[:80]))

    if failed:
        for m, e in failed:
            errors.append(f"FAIL: import {m}: {e}")
    else:
        checks.append(f"PASS: all {len(mods)} modules import OK")

    return checks, errors


def main() -> int:
    all_checks: list[str] = []
    all_errors: list[str] = []

    print("=== ForgeFlow E2E Smoke Test ===\n")

    # Import check
    print("--- Module Imports ---")
    c, e = smoke_imports()
    all_checks.extend(c)
    all_errors.extend(e)
    for line in c + e:
        print(f"  {line}")

    # Lifecycle check
    print("\n--- Task Lifecycle ---")
    c, e = smoke_lifecycle()
    all_checks.extend(c)
    all_errors.extend(e)
    for line in c + e:
        print(f"  {line}")

    # Summary
    total = len(all_checks) + len(all_errors)
    passed = len(all_checks)
    failed = len(all_errors)

    print(f"\n=== Result: {passed}/{total} passed ===")
    if all_errors:
        print("\nFailures:")
        for err in all_errors:
            print(f"  {err}")
        return 1
    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
