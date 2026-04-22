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


def main() -> int:
    errors = []
    regen = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'generate_adapters.py')],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if regen.returncode != 0:
        print('GENERATED VALIDATION: FAIL')
        print('- generator itself failed')
        print(regen.stdout)
        print(regen.stderr)
        return 1

    for target, name in REQUIRED_GENERATED.items():
        path = ROOT / 'adapters' / 'generated' / target / name
        manifest = ROOT / 'adapters' / 'targets' / target / 'manifest.yaml'
        if not path.is_file():
            errors.append(f'missing generated file: {path.relative_to(ROOT)}')
            continue
        text = path.read_text(encoding='utf-8')
        for marker in REQUIRED_MARKERS:
            if marker not in text:
                errors.append(f'{path.relative_to(ROOT)} missing marker: {marker}')
        supported_roles = load_manifest_roles(manifest)
        for role, title in ROLE_TITLES.items():
            has_title = title in text
            should_have = role in supported_roles
            if has_title and not should_have:
                errors.append(f'{path.relative_to(ROOT)} includes unsupported role {role}')
            if should_have and not has_title:
                errors.append(f'{path.relative_to(ROOT)} missing supported role {role}')
    if errors:
        print('GENERATED VALIDATION: FAIL')
        for err in errors:
            print(f'- {err}')
        return 1
    print('GENERATED VALIDATION: PASS')
    for target, name in REQUIRED_GENERATED.items():
        print(f'- checked adapters/generated/{target}/{name}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
