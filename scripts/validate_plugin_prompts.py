#!/usr/bin/env python3
"""Extracted from Makefile target: validate-plugin-prompts"""
import json, pathlib, sys
root = pathlib.Path('.')
active = {p.name for p in (root / 'skills').iterdir() if p.is_dir() and not p.name.startswith('_')}
files = [root / '.codex-plugin/plugin.json', root / '.cursor-plugin/plugin.json']
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
        command = prompt.split()[0].split(':')[-1].lstrip('/')
        if command == 'init':
            failures.append(f'{path}: use /forgeflow:clarify, not /init')
        if command not in active:
            failures.append(f'{path}: defaultPrompt {prompt!r} does not map to an active skill')
        if command in seen:
            failures.append(f'{path}: duplicate defaultPrompt command {command!r}')
        seen.add(command)
if failures:
    print('ERROR: Plugin defaultPrompt contract failed')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print('OK: Plugin defaultPrompt entries map to active skills')

