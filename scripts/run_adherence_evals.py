#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forgeflow_runtime.orchestrator import RuntimeViolation, advance_to_next_stage, load_runtime_policy, run_route


def _copy_fixture(source: Path, workspace: Path) -> Path:
    destination = workspace / source.name
    shutil.copytree(source, destination)
    return destination


def _positive_case(name: str, fixture_dir: Path, route_name: str, expected_stage: str, workspace: Path) -> str:
    task_dir = _copy_fixture(fixture_dir, workspace)
    result = run_route(task_dir=task_dir, policy=load_runtime_policy(ROOT), route_name=route_name)
    if result['status'] != 'completed' or result['current_stage'] != expected_stage:
        raise AssertionError(f'{name}: unexpected result {result}')
    return f'PASS {name}: route={route_name} final_stage={expected_stage}'


def _negative_run_case(name: str, fixture_dir: Path, route_name: str, expected_error: str, workspace: Path) -> str:
    task_dir = _copy_fixture(fixture_dir, workspace)
    try:
        run_route(task_dir=task_dir, policy=load_runtime_policy(ROOT), route_name=route_name)
    except RuntimeViolation as exc:
        if expected_error not in str(exc):
            raise AssertionError(f'{name}: expected error containing {expected_error!r}, got {exc!r}') from exc
        return f'PASS {name}: blocked with {exc}'
    raise AssertionError(f'{name}: expected RuntimeViolation')


def _negative_advance_case(name: str, fixture_dir: Path, route_name: str, current_stage: str, expected_error: str, workspace: Path) -> str:
    task_dir = _copy_fixture(fixture_dir, workspace)
    try:
        advance_to_next_stage(task_dir=task_dir, policy=load_runtime_policy(ROOT), route_name=route_name, current_stage=current_stage)
    except RuntimeViolation as exc:
        if expected_error not in str(exc):
            raise AssertionError(f'{name}: expected error containing {expected_error!r}, got {exc!r}') from exc
        return f'PASS {name}: blocked with {exc}'
    raise AssertionError(f'{name}: expected RuntimeViolation')


def main() -> int:
    fixtures_root = ROOT / 'examples' / 'runtime-fixtures'
    scenarios = []
    try:
        with tempfile.TemporaryDirectory(prefix='forgeflow-adherence-') as tmpdir:
            workspace = Path(tmpdir)
            scenarios.append(_positive_case('small-doc-task', fixtures_root / 'small-doc-task', 'small', 'finalize', workspace))
            scenarios.append(_positive_case('resume-small-task', fixtures_root / 'resume-small-task', 'small', 'finalize', workspace))
            scenarios.append(_positive_case('medium-refactor-task', fixtures_root / 'medium-refactor-task', 'medium', 'finalize', workspace))
            scenarios.append(_positive_case('large-migration-task', fixtures_root / 'large-migration-task', 'large_high_risk', 'long-run', workspace))
            negative_root = fixtures_root / 'negative'
            scenarios.append(_negative_run_case('missing-quality-approval', negative_root / 'missing-quality-approval', 'small', 'quality-review requires approved quality review-report artifact', workspace))
            scenarios.append(_negative_run_case('invalid-review-report', negative_root / 'invalid-review-report', 'small', 'review-report.json failed schema validation', workspace))
            scenarios.append(_negative_advance_case('missing-run-state-before-spec-review', negative_root / 'missing-run-state-before-spec-review', 'large_high_risk', 'execute', 'missing required artifacts for spec-review: run-state', workspace))
            scenarios.append(_negative_run_case('missing-eval-record-before-long-run', negative_root / 'missing-eval-record-before-long-run', 'large_high_risk', 'long-run requires artifacts satisfying gate worth_long_run_capture: eval-record', workspace))
            scenarios.append(_negative_run_case('checkpoint-gate-drift', negative_root / 'checkpoint-gate-drift', 'small', 'run-state checkpoint is missing completed gates before execute: clarification_complete', workspace))
    except Exception as exc:
        print('ADHERENCE EVALS: FAIL')
        print(f'- {exc}')
        for line in scenarios:
            print(f'- {line}')
        return 1

    print('ADHERENCE EVALS: PASS')
    for line in scenarios:
        print(f'- {line}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
