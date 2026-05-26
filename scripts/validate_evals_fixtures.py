#!/usr/bin/env python3
"""Extracted from Makefile target: validate-evals-fixtures"""
import json, pathlib, sys
root = pathlib.Path('.')
data = json.loads((root / 'evals/evals.json').read_text(encoding='utf-8'))
failures = []
stale_terms = ('/forgeflow:finish', '/forgeflow:milestone', '/forgeflow-init', '/forgeflow:subagent-execute', 'large_high_risk')
def walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from walk_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk_strings(nested)
for i, item in enumerate(data.get('evals', [])):
    if not isinstance(item, dict):
        continue
    name = item.get('name', f'#{i}')
    for stale in stale_terms:
        if any(stale in text for text in walk_strings(item)):
            failures.append(f'eval[{i}] {name}: fixture text references stale workflow vocabulary {stale!r}')
for smoke in ('audit-smoke-high', 'audit-smoke-epic'):
    report = root / 'evals/results/smoke-tasks' / smoke / 'review-report.md'
    if not report.is_file():
        failures.append(f'{report}: missing smoke fixture')
        continue
    text = report.read_text(encoding='utf-8')
    for heading in ('## Execute Micro-Gates', '## Verdict', '## Evidence Classification', '## Next Action'):
        if heading not in text:
            failures.append(f'{report}: missing required heading {heading!r}')
if failures:
    print('ERROR: eval fixture contract failed')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print('OK: eval fixtures avoid stale workflow vocabulary and smoke fixtures are concrete')

