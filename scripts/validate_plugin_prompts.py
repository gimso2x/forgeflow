#!/usr/bin/env python3
"""Extracted from Makefile target: validate-plugin-prompts"""
import json, pathlib, sys
root = pathlib.Path('.')
active = {p.name for p in (root / 'skills').iterdir() if p.is_dir() and not p.name.startswith('_')}
files = [root / '.claude-plugin/plugin.json', root / '.codex-plugin/plugin.json', root / '.cursor-plugin/plugin.json']
legacy_tokens = ('/forgeflow:plan', '/forgeflow:review', 'forgeflow:plan', 'forgeflow:review')
scan_files = [root / 'README.md', root / 'SKILL.md'] + sorted((root / 'skills').glob('**/*.md'))
failures = []
for path in files:
    data = json.loads(path.read_text(encoding='utf-8'))
    prompts = data.get('interface', {}).get('defaultPrompt', [])
    if not isinstance(prompts, list) or not prompts:
        failures.append(f'{path}: interface.defaultPrompt must be a non-empty list')
        continue
    seen = set()
    for prompt in prompts:
        if not isinstance(prompt, str) or not prompt.startswith('/'):
            failures.append(f'{path}: defaultPrompt entry must be a slash command: {prompt!r}')
            continue
        if path.name == 'plugin.json' and path.parent.name == '.cursor-plugin' and ':' in prompt.split()[0]:
            failures.append(f'{path}: Cursor defaultPrompt must use colonless slash commands, not {prompt!r}')
        command = prompt.split()[0].split(':')[-1].lstrip('/')
        if command == 'init':
            failures.append(f'{path}: use /forgeflow:clarify, not /init')
        if command not in active:
            failures.append(f'{path}: defaultPrompt {prompt!r} does not map to an active skill')
        if command in seen:
            failures.append(f'{path}: duplicate defaultPrompt command {command!r}')
        seen.add(command)
for path in scan_files:
    text = path.read_text(encoding='utf-8')
    for token in legacy_tokens:
        if token in text:
            failures.append(f'{path}: legacy plan/review skill reference {token!r}; use ff-plan/ff-review')
if failures:
    print('ERROR: Plugin defaultPrompt contract failed')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print('OK: Plugin defaultPrompt entries map to active skills and adapter slash forms')

