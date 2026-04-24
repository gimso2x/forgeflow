#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_SOURCES = [
    Path('/tmp/hoyeon-analysis'),
    Path('/home/ubuntu/hoyeon'),
    Path('/home/ubuntu/work/hoyeon'),
]
SOURCE_FILES = {
    'skills/specify/SKILL.md': 'skills/specify.md',
    'skills/blueprint/SKILL.md': 'skills/blueprint.md',
    'skills/execute/SKILL.md': 'skills/execute.md',
    'skills/compound/SKILL.md': 'skills/compound.md',
    'cli/src/commands/plan.js': 'cli/plan.js',
    'hooks/hooks.json': 'hooks/hooks.json',
}
MIRROR = ROOT / 'docs/upstream/hoyeon'


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_source() -> Path | None:
    for source in CANDIDATE_SOURCES:
        if all((source / rel).is_file() for rel in SOURCE_FILES):
            return source
    return None


def main() -> int:
    errors: list[str] = []
    source = find_source()
    if not (MIRROR / 'README.md').is_file():
        errors.append('missing docs/upstream/hoyeon/README.md')

    for upstream_rel, mirror_rel in SOURCE_FILES.items():
        mirror_path = MIRROR / mirror_rel
        if not mirror_path.is_file():
            errors.append(f'missing mirror file: {mirror_path.relative_to(ROOT)}')
            continue
        if source is not None:
            upstream_path = source / upstream_rel
            if sha256(upstream_path) != sha256(mirror_path):
                errors.append(f'mirror drift: {upstream_rel} -> {mirror_rel}')

    if errors:
        print('HOYEON IMPORT VALIDATION: FAIL')
        for error in errors:
            print(f'- {error}')
        return 1

    print('HOYEON IMPORT VALIDATION: PASS')
    if source is None:
        print('- source unavailable; checked committed mirror only')
    else:
        print(f'- source: {source}')
    print(f'- mirrored files: {len(SOURCE_FILES)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
