#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'scripts/forgeflow_plan.py'
SAMPLE = ROOT / 'examples/artifacts/plan.sample.json'
CONTRACTS = ROOT / 'examples/artifacts/contracts.md'


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CLI), *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def assert_ok(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        raise AssertionError(f'{label} failed: stdout={result.stdout!r} stderr={result.stderr!r}')


def assert_fail(result: subprocess.CompletedProcess[str], expected: str, label: str) -> None:
    if result.returncode == 0 or expected not in result.stderr:
        raise AssertionError(f'{label} expected failure containing {expected!r}: stdout={result.stdout!r} stderr={result.stderr!r}')


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='forgeflow-plan-cli-') as tmp:
        task_dir = Path(tmp) / 'task'
        task_dir.mkdir()
        shutil.copy2(SAMPLE, task_dir / 'plan.json')
        shutil.copy2(CONTRACTS, task_dir / 'contracts.md')

        assert_ok(run('validate', str(task_dir), cwd=ROOT), 'validate')
        list_result = run('list', str(task_dir), cwd=ROOT)
        assert_ok(list_result, 'list')
        if 'step-1' not in list_result.stdout:
            raise AssertionError('list did not include step-1')

        assert_ok(run('task', str(task_dir), '--status', 'step-1=completed', '--summary', 'smoke done', cwd=ROOT), 'task complete')
        plan = json.loads((task_dir / 'plan.json').read_text())
        step_1 = next(step for step in plan['steps'] if step['id'] == 'step-1')
        if step_1.get('status') != 'completed':
            raise AssertionError('step-1 status was not persisted')

        assert_ok(run('task', str(task_dir), '--status', 'step-1=completed', cwd=ROOT), 'task idempotent')
        assert_fail(run('task', str(task_dir), '--status', 'step-1=pending', cwd=ROOT), 'cannot transition', 'completed backward block')
        assert_ok(run('list', str(task_dir), '--status', 'completed', cwd=ROOT), 'list completed')

    print('PLAN CLI SMOKE: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
