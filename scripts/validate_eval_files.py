#!/usr/bin/env python3
"""Extracted from Makefile target: validate-eval-files"""
import json, pathlib, subprocess, sys
root = pathlib.Path('.')
tracked = set(subprocess.check_output(['git', 'ls-files'], text=True).splitlines())
data = json.loads((root / 'evals/evals.json').read_text(encoding='utf-8'))
failures = []
for i, item in enumerate(data.get('evals', [])):
    name = item.get('name', f'#{i}') if isinstance(item, dict) else f'#{i}'
    entries = item.get('files', []) if isinstance(item, dict) else []
    duplicate_entries = sorted({raw for raw in entries if isinstance(raw, str) and entries.count(raw) > 1})
    if duplicate_entries:
        failures.append(f'eval[{i}] {name}: files entries must be unique: {duplicate_entries}')
    for raw in entries:
        path = pathlib.PurePosixPath(raw)
        if path.is_absolute() or '..' in path.parts:
            failures.append(f'eval[{i}] {name}: files entry must be repo-relative and stay inside repo: {raw}')
            continue
        if not (root / raw).is_file():
            failures.append(f'eval[{i}] {name}: referenced file does not exist: {raw}')
            continue
        if raw not in tracked:
            failures.append(f'eval[{i}] {name}: referenced file must be tracked by git: {raw}')
for report in sorted((root / 'evals' / 'results').glob('**/review-report.md')):
    text = report.read_text(encoding='utf-8')
    if '<!--' in text or '-->' in text:
        failures.append(f'{report}: persisted eval review reports must be concrete audit output, not unresolved template placeholders')
    for heading in ('## Verdict', '## Evidence Classification', '## Next Action'):
        if heading not in text:
            failures.append(f'{report}: missing required concrete review heading {heading}')
if failures:
    print('ERROR: eval file references failed')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print('OK: eval file references are repo-relative, tracked, and resolvable')

