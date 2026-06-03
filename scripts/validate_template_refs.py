#!/usr/bin/env python3
"""Extracted from Makefile target: validate-template-refs"""
import pathlib, re, sys
root = pathlib.Path('.')
refs = set()
for skill_md in list((root / 'skills').glob('*/SKILL.md')) + list((root / 'skills' / '_shared').glob('*.md')):
    text = skill_md.read_text(encoding='utf-8')
    for match in re.finditer(r'templates/([a-zA-Z0-9_-]+\.md)', text):
        refs.add(match.group(1))
missing = sorted(t for t in refs if not (root / 'templates' / t).exists())
if missing:
    print('ERROR: Missing template files referenced by skills:')
    [print(f'- {item}') for item in missing]
    sys.exit(1)
print(f'OK: {len(refs)} template references resolve')

