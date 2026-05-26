#!/usr/bin/env python3
"""Extracted from Makefile target: validate-gemini-imports"""
import json, pathlib, re, sys
root = pathlib.Path('.')
gemini = (root / 'GEMINI.md').read_text(encoding='utf-8')
imports = re.findall(r'@(\./skills/[^\s]+)', gemini)
imported_paths = set(imports)
failures = []
manifest = json.loads((root / 'gemini-extension.json').read_text(encoding='utf-8'))
if manifest.get('contextFileName') != 'GEMINI.md':
    failures.append('gemini-extension.json: contextFileName must be GEMINI.md')
if './skills/SKILLS.md' not in imported_paths:
    failures.append('GEMINI.md: missing @./skills/SKILLS.md inventory import')
active_skills = {d.name for d in (root / 'skills').iterdir() if d.is_dir() and not d.name.startswith('_')}
expected_imports = {f'./skills/{name}/SKILL.md' for name in active_skills}
missing_active = sorted(expected_imports - imported_paths)
stale_active = sorted(p for p in imported_paths if p.startswith('./skills/') and p.endswith('/SKILL.md') and p not in expected_imports)
missing_files = [p for p in imports if not (root / p.lstrip('./')).exists()]
if missing_active:
    failures.append(f'GEMINI.md: missing active skill imports {missing_active}')
if stale_active:
    failures.append(f'GEMINI.md: imports stale skill paths {stale_active}')
for item in missing_files:
    failures.append(f'GEMINI.md: broken import {item}')
if '@./docs/adapter-config.md' not in gemini:
    failures.append('GEMINI.md: missing @./docs/adapter-config.md import')
if failures:
    print('ERROR: Gemini extension import contract failed')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print(f'OK: GEMINI.md imports inventory and {len(active_skills)} active skills')

