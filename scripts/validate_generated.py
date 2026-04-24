#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

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
    'Runtime realism contract',
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


def load_manifest(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'{path}: manifest must be a YAML mapping')
    return data


def load_manifest_roles(path: Path) -> list[str]:
    roles = load_manifest(path).get('supports_roles', [])
    if not isinstance(roles, list):
        return []
    return [str(role) for role in roles]


def load_manifest_value(path: Path, key: str) -> str | None:
    value = load_manifest(path).get(key)
    return str(value) if value is not None else None


def load_manifest_list(path: Path, key: str) -> list[str]:
    values = load_manifest(path).get(key, [])
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


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
    if untracked.returncode != 0:
        untracked_error = (untracked.stdout or untracked.stderr).strip()
        if not untracked_error:
            untracked_error = 'git ls-files reported untracked generated files lookup failure'
        errors.extend(['generator untracked-file lookup failed', untracked_error])
    elif untracked_paths:
        drift_messages.append('untracked files:\n' + '\n'.join(untracked_paths))

    tracked = subprocess.run(
        ['git', 'ls-files', '--', 'adapters/generated'],
        cwd=root,
        capture_output=True,
        text=True,
    )
    tracked_paths = {line.strip() for line in tracked.stdout.splitlines() if line.strip()}
    if tracked.returncode != 0:
        tracked_error = (tracked.stdout or tracked.stderr).strip()
        if not tracked_error:
            tracked_error = 'git ls-files reported tracked generated files lookup failure'
        errors.extend(['generator tracked-file lookup failed', tracked_error])
        tracked_paths = set()

    if drift_messages:
        errors.append(
            'generated adapters drift from canonical sources after regeneration:\n'
            + '\n'.join(drift_messages)
        )

    expected_generated_paths = set()
    for target, name in REQUIRED_GENERATED.items():
        manifest = root / 'adapters' / 'targets' / target / 'manifest.yaml'
        expected_filename = load_manifest_value(manifest, 'generated_filename') or name
        relative_path = Path('adapters/generated') / target / expected_filename
        expected_generated_paths.add(str(relative_path))
        path = root / relative_path
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
        expected_session = load_manifest_value(manifest, 'session_persistence')
        expected_boundary = load_manifest_value(manifest, 'workspace_boundary')
        expected_review_delivery = load_manifest_value(manifest, 'review_delivery')
        expected_lines = [
            f'- generated_filename: {expected_filename}',
            f'- recommended_location: {expected_location}',
            f'- surface_style: {expected_surface}',
            f'- handoff_format: {expected_handoff}',
            f'- session_persistence: {expected_session}',
            f'- workspace_boundary: {expected_boundary}',
            f'- review_delivery: {expected_review_delivery}',
            '## Installation steps',
        ]
        for expected_line in expected_lines:
            if expected_line not in text:
                errors.append(f'{path.relative_to(root)} missing manifest-derived line: {expected_line}')
        for index, step in enumerate(installation_steps, start=1):
            expected_step = f'{index}. {step}'
            if expected_step not in text:
                errors.append(f'{path.relative_to(root)} missing installation step: {expected_step}')
    stale_tracked_paths = sorted(tracked_paths - expected_generated_paths)
    for stale_path in stale_tracked_paths:
        errors.append(f'stale generated file tracked outside canonical manifest set: {stale_path}')
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
