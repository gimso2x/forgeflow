#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_GENERATED = {
    'claude': 'CLAUDE.md',
    'codex': 'CODEX.md',
    'cursor': 'HARNESS_CURSOR.md',
}
REQUIRED_MARKERS = [
    'This file is generated from canonical harness policy.',
    'Non-negotiable rules',
    'Canonical workflow snapshot',
    'Canonical role prompts',
]
ROLE_TITLES = {
    'coordinator': '# Coordinator',
    'planner': '# Planner',
    'worker': '# Worker',
    'spec-reviewer': '# Spec Reviewer',
    'quality-reviewer': '# Quality Reviewer',
}


def load_manifest_roles(path: Path) -> list[str]:
    roles = []
    capture = False
    for raw in path.read_text(encoding='utf-8').splitlines():
        stripped = raw.strip()
        if stripped == 'supports_roles:':
            capture = True
            continue
        if capture:
            if stripped.startswith('- '):
                roles.append(stripped[2:].strip())
            elif stripped:
                break
    return roles


def check_generated_outputs(root: Path) -> list[str]:
    errors = []
    regen = subprocess.run(
        [sys.executable, str(root / 'scripts' / 'generate_adapters.py')],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if regen.returncode != 0:
        return [
            'generator itself failed',
            regen.stdout.strip(),
            regen.stderr.strip(),
        ]

    diff = subprocess.run(
        ['git', 'diff', '--exit-code', '--', 'adapters/generated'],
        cwd=root,
        capture_output=True,
        text=True,
    )
    drift_messages: list[str] = []
    if diff.returncode != 0:
        tracked_drift = (diff.stdout or diff.stderr).strip()
        if not tracked_drift:
            tracked_drift = 'git diff reported generated adapter changes after regeneration'
        drift_messages.append(tracked_drift)

    untracked = subprocess.run(
        ['git', 'ls-files', '--others', '--exclude-standard', '--', 'adapters/generated'],
        cwd=root,
        capture_output=True,
        text=True,
    )
    untracked_paths = [line.strip() for line in untracked.stdout.splitlines() if line.strip()]
    if untracked_paths:
        drift_messages.append('untracked files:\n' + '\n'.join(untracked_paths))

    if drift_messages:
        errors.append(
            'generated adapters drift from canonical sources after regeneration:\n'
            + '\n'.join(drift_messages)
        )

    for target, name in REQUIRED_GENERATED.items():
        path = root / 'adapters' / 'generated' / target / name
        manifest = root / 'adapters' / 'targets' / target / 'manifest.yaml'
        if not path.is_file():
            errors.append(f'missing generated file: {path.relative_to(root)}')
            continue
        text = path.read_text(encoding='utf-8')
        for marker in REQUIRED_MARKERS:
            if marker not in text:
                errors.append(f'{path.relative_to(root)} missing marker: {marker}')
        supported_roles = load_manifest_roles(manifest)
        for role, title in ROLE_TITLES.items():
            has_title = title in text
            should_have = role in supported_roles
            if has_title and not should_have:
                errors.append(f'{path.relative_to(root)} includes unsupported role {role}')
            if should_have and not has_title:
                errors.append(f'{path.relative_to(root)} missing supported role {role}')
    return [err for err in errors if err]


def main() -> int:
    errors = check_generated_outputs(ROOT)
    if errors:
        print('GENERATED VALIDATION: FAIL')
        for err in errors:
            print(f'- {err}')
        return 1
    print('GENERATED VALIDATION: PASS')
    for target, name in REQUIRED_GENERATED.items():
        print(f'- checked adapters/generated/{target}/{name}')
    print('- regeneration left adapters/generated clean')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
