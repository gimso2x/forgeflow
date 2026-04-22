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
    'Installation guidance',
    'Target operating notes',
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


def load_manifest_value(path: Path, key: str) -> str | None:
    prefix = f'{key}:'
    for raw in path.read_text(encoding='utf-8').splitlines():
        stripped = raw.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix):].strip()
    return None


def load_manifest_list(path: Path, key: str) -> list[str]:
    values = []
    capture = False
    prefix = f'{key}:'
    for raw in path.read_text(encoding='utf-8').splitlines():
        stripped = raw.strip()
        if stripped == prefix:
            capture = True
            continue
        if capture:
            if stripped.startswith('- '):
                values.append(stripped[2:].strip())
                continue
            if stripped:
                break
    return values


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
        manifest = root / 'adapters' / 'targets' / target / 'manifest.yaml'
        expected_filename = load_manifest_value(manifest, 'generated_filename') or name
        path = root / 'adapters' / 'generated' / target / expected_filename
        if not path.is_file():
            errors.append(f'missing generated file: {path.relative_to(root)}')
            continue
        text = path.read_text(encoding='utf-8')
        for marker in REQUIRED_MARKERS:
            if marker not in text:
                errors.append(f'{path.relative_to(root)} missing marker: {marker}')
        supported_roles = load_manifest_roles(manifest)
        expected_filename = load_manifest_value(manifest, 'generated_filename')
        expected_location = load_manifest_value(manifest, 'recommended_location')
        expected_surface = load_manifest_value(manifest, 'surface_style')
        expected_handoff = load_manifest_value(manifest, 'handoff_format')
        installation_steps = load_manifest_list(manifest, 'installation_steps')
        for role, title in ROLE_TITLES.items():
            has_title = title in text
            should_have = role in supported_roles
            if has_title and not should_have:
                errors.append(f'{path.relative_to(root)} includes unsupported role {role}')
            if should_have and not has_title:
                errors.append(f'{path.relative_to(root)} missing supported role {role}')
        expected_lines = [
            f'- generated_filename: {expected_filename}',
            f'- recommended_location: {expected_location}',
            f'- surface_style: {expected_surface}',
            f'- handoff_format: {expected_handoff}',
            '## Installation steps',
        ]
        for expected_line in expected_lines:
            if expected_line not in text:
                errors.append(f'{path.relative_to(root)} missing manifest-derived line: {expected_line}')
        for index, step in enumerate(installation_steps, start=1):
            expected_step = f'{index}. {step}'
            if expected_step not in text:
                errors.append(f'{path.relative_to(root)} missing installation step: {expected_step}')
    return [err for err in errors if err]


def main() -> int:
    errors = check_generated_outputs(ROOT)
    if errors:
        print('GENERATED VALIDATION: FAIL')
        for err in errors:
            print(f'- {err}')
        return 1
    print('GENERATED VALIDATION: PASS')
    for target, fallback_name in REQUIRED_GENERATED.items():
        manifest = ROOT / 'adapters' / 'targets' / target / 'manifest.yaml'
        expected_name = load_manifest_value(manifest, 'generated_filename') or fallback_name
        print(f'- checked adapters/generated/{target}/{expected_name}')
    print('- regeneration left adapters/generated clean')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
