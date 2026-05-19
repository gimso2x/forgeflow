#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Ensure forgeflow_runtime is importable when run outside the venv
sys.path.insert(0, str(ROOT))

REQUIRED_DIRS = [
    'docs',
    'policy/canonical',
    'schemas',
    'prompts/canonical',
    'adapters/targets/claude',
    'adapters/targets/codex',
    'adapters/generated/claude',
    'adapters/generated/codex',
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
    'schemas/review-input.schema.json',
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
    # specialist agent prompts (2-axis: spec-based specialist selection)
    'adapters/targets/claude/agents/forgeflow-security-reviewer.md',
    'adapters/targets/claude/agents/forgeflow-ux-reviewer.md',
    'adapters/targets/claude/agents/forgeflow-perf-reviewer.md',
    'adapters/targets/claude/agents/forgeflow-frontend-worker.md',
    'adapters/targets/claude/agents/forgeflow-backend-worker.md',
    'adapters/targets/claude/agents/forgeflow-infra-worker.md',
    'adapters/targets/codex/agents/forgeflow-security-reviewer.md',
    'adapters/targets/codex/agents/forgeflow-ux-reviewer.md',
    'adapters/targets/codex/agents/forgeflow-perf-reviewer.md',
    'adapters/targets/codex/agents/forgeflow-frontend-worker.md',
    'adapters/targets/codex/agents/forgeflow-backend-worker.md',
    'adapters/targets/codex/agents/forgeflow-infra-worker.md',
    'adapters/manifest.schema.json',
    'adapters/targets/claude/manifest.yaml',
    'adapters/targets/codex/manifest.yaml',
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

    # Adapter registry cross-check: verify every discovered adapter has
    # a manifest.yaml that the runtime can parse.
    registry_failures = _validate_adapter_registry()
    if registry_failures:
        print('ADAPTER REGISTRY: FAIL')
        for item in registry_failures:
            print(f'- {item}')
        return 1

    adapter_count = len(registry_failures)  # 0, just for summary
    print('STRUCTURE VALIDATION: PASS')
    print(f'- checked directories: {len(REQUIRED_DIRS)}')
    print(f'- checked files: {len(REQUIRED_FILES)}')
    print(f'- adapter registry: OK')
    return 0


def _validate_adapter_registry() -> list[str]:
    """Use AdapterRegistry to cross-check manifest discoverability."""
    from forgeflow_runtime.adapter_registry import AdapterRegistry

    failures: list[str] = []
    targets_dir = ROOT / 'adapters' / 'targets'
    if not targets_dir.is_dir():
        return ['adapters/targets/ directory not found']

    registry = AdapterRegistry(targets_dir)

    # Every subdirectory with a manifest.yaml should be discoverable
    for subdir in sorted(targets_dir.iterdir()):
        if not subdir.is_dir():
            continue
        has_manifest = (subdir / 'manifest.yaml').exists()
        name = subdir.name
        if has_manifest and not registry.has_adapter(name):
            failures.append(f'{name}/ has manifest.yaml but registry skipped it (malformed?)')

    return failures


if __name__ == '__main__':
    raise SystemExit(main())
