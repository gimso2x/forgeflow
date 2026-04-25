#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRS = [
    'docs',
    'policy/canonical',
    'schemas',
    'prompts/canonical',
    'adapters/targets/claude',
    'adapters/targets/codex',
    'adapters/targets/cursor',
    'adapters/generated/claude',
    'adapters/generated/codex',
    'adapters/generated/cursor',
    'runtime/orchestrator',
    'runtime/ledger',
    'runtime/gates',
    'runtime/recovery',
    'memory/patterns',
    'memory/decisions',
    'evals/adherence',
    'evals/regression',
    'examples/small-task',
    'examples/medium-task',
    'examples/large-task',
]

REQUIRED_FILES = [
    'README.md',
    'docs/architecture.md',
    'docs/workflow.md',
    'docs/artifact-model.md',
    'docs/review-model.md',
    'docs/adapter-model.md',
    'docs/recovery-policy.md',
    'docs/evolution-model.md',
    'docs/contract-map.md',
    'docs/implementation-plan.md',
    'runtime/README.md',
    'runtime/orchestrator/README.md',
    'runtime/ledger/README.md',
    'runtime/gates/README.md',
    'runtime/recovery/README.md',
    'memory/README.md',
    'memory/patterns/README.md',
    'memory/decisions/README.md',
    'policy/canonical/workflow.yaml',
    'policy/canonical/stages.yaml',
    'policy/canonical/gates.yaml',
    'policy/canonical/review-rubrics.yaml',
    'policy/canonical/complexity-routing.yaml',
    'policy/canonical/evolution.yaml',
    'schemas/brief.schema.json',
    'schemas/plan.schema.json',
    'schemas/decision-log.schema.json',
    'schemas/run-state.schema.json',
    'schemas/review-report.schema.json',
    'schemas/eval-record.schema.json',
    'schemas/policy/workflow.schema.json',
    'schemas/policy/stages.schema.json',
    'schemas/policy/gates.schema.json',
    'schemas/policy/complexity-routing.schema.json',
    'schemas/policy/evolution.schema.json',
    'prompts/canonical/coordinator.md',
    'prompts/canonical/planner.md',
    'prompts/canonical/worker.md',
    'prompts/canonical/spec-reviewer.md',
    'prompts/canonical/quality-reviewer.md',
    'adapters/manifest.schema.json',
    'adapters/targets/claude/manifest.yaml',
    'adapters/targets/codex/manifest.yaml',
    'adapters/targets/cursor/manifest.yaml',
    'evals/adherence/README.md',
    'evals/regression/README.md',
]


def main() -> int:
    missing = []
    for rel in REQUIRED_DIRS:
        path = ROOT / rel
        if not path.is_dir():
            missing.append(f'DIR  {rel}')
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.is_file():
            missing.append(f'FILE {rel}')

    if missing:
        print('STRUCTURE VALIDATION: FAIL')
        for item in missing:
            print(f'- missing {item}')
        return 1

    print('STRUCTURE VALIDATION: PASS')
    print(f'- checked directories: {len(REQUIRED_DIRS)}')
    print(f'- checked files: {len(REQUIRED_FILES)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
