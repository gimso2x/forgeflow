#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/home/ubuntu/engineering-discipline/skills')
MIRROR = ROOT / 'docs/upstream/engineering-discipline/skills'
EXPECTED = {
    'clarification',
    'clean-ai-slop',
    'karpathy',
    'long-run',
    'milestone-planning',
    'plan-crafting',
    'review-work',
    'rob-pike',
    'run-plan',
    'simplify',
    'systematic-debugging',
}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    errors: list[str] = []
    if not MIRROR.is_dir():
        errors.append(f'missing mirror dir: {MIRROR.relative_to(ROOT)}')
    if errors:
        print('UPSTREAM IMPORT VALIDATION: FAIL')
        for error in errors:
            print(f'- {error}')
        return 1

    source_available = SOURCE.is_dir()
    source_names = {p.parent.name for p in SOURCE.glob('*/SKILL.md')} if source_available else set()
    mirror_names = {p.stem for p in MIRROR.glob('*.md')}

    missing_source = EXPECTED - source_names if source_available else set()
    missing_mirror = EXPECTED - mirror_names
    extra_mirror = mirror_names - EXPECTED
    if missing_source:
        errors.append(f'upstream missing expected skills: {sorted(missing_source)}')
    if missing_mirror:
        errors.append(f'mirror missing expected skills: {sorted(missing_mirror)}')
    if extra_mirror:
        errors.append(f'mirror has unexpected skills: {sorted(extra_mirror)}')

    for name in sorted(EXPECTED & source_names & mirror_names) if source_available else []:
        src = SOURCE / name / 'SKILL.md'
        mirrored = MIRROR / f'{name}.md'
        if sha256(src) != sha256(mirrored):
            errors.append(f'mirror drift: {name}')

    if errors:
        print('UPSTREAM IMPORT VALIDATION: FAIL')
        for error in errors:
            print(f'- {error}')
        return 1

    print('UPSTREAM IMPORT VALIDATION: PASS')
    print(f'- mirrored skills: {len(EXPECTED)}')
    if source_available:
        print(f'- source: {SOURCE}')
    else:
        print('- source unavailable; checked committed mirror only')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
