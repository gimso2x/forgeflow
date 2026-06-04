#!/usr/bin/env python3
"""Extracted from Makefile target: validate-agent-docs"""
import pathlib, re, sys
root = pathlib.Path('.')
agents = (root / 'AGENTS.md').read_text(encoding='utf-8')
active = sorted(d.name for d in (root / 'skills').iterdir() if d.is_dir() and not d.name.startswith('_'))
listed = sorted(set(re.findall(r'^  ([a-z0-9-]+)/\s+#', agents, re.M)))
missing = sorted(set(active) - set(listed))
stale = sorted(set(listed) - set(active))
failures = []
if missing:
    failures.append(f'AGENTS.md: missing active skill directories {missing}')
if stale:
    failures.append(f'AGENTS.md: lists stale skill directories {stale}')
for required in ('외부 의존성 추가 금지', 'Review는 읽기 전용', 'slim, markdown-only distribution', 'Do not assume the older', 'trees exist'):
    if required not in agents:
        failures.append(f'AGENTS.md: missing maintainer guardrail {required!r}')
version = (root / 'VERSION').read_text(encoding='utf-8').strip()
if f'currently `{version}`' not in agents:
    failures.append(f'AGENTS.md: VERSION note must match VERSION={version}')
if 'VERSION' not in agents or '단일 소스' not in agents:
    failures.append('AGENTS.md: missing maintainer guardrail for VERSION single source')
frontmatter_contract = 'name' + chr(96) + ', ' + chr(96) + 'description' + chr(96) + ', ' + chr(96) + 'version' + chr(96) + ', ' + chr(96) + 'validate_prompt' + chr(96)
release_version_phrase = '릴리즈 ' + chr(96) + 'VERSION' + chr(96) + '과 별개'
if frontmatter_contract not in agents or release_version_phrase not in agents:
    failures.append('AGENTS.md: missing public skill frontmatter version contract')
for required in ('Maintainer / Autonomous Preflight', 'git branch --show-current', 'git status --short --branch', 'git pull --ff-only', 'git add -A', 'Do not schedule jobs'):
    if required not in agents:
        failures.append(f'AGENTS.md: missing autonomous preflight guardrail {required!r}')
if failures:
    print('ERROR: AGENTS.md contract drift')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print(f'OK: AGENTS.md lists {len(active)} active skills and maintainer guardrails')

