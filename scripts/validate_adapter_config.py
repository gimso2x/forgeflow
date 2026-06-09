#!/usr/bin/env python3
"""Extracted from Makefile target: validate-adapter-config"""
import pathlib, sys
text = pathlib.Path('docs/adapter-config.md').read_text(encoding='utf-8')
required = {
    'Claude Code': ['claude -p', '--dangerously-skip-permissions', 'CLAUDE_CODE_SESSION=1', '대상 프로젝트 루트', 'plugin cache'],
    'Codex CLI': ['codex exec', 'danger-full-access', 'CODEX_SESSION=1', '대상 프로젝트 루트', 'plugin cache'],
    'Cursor': ['~/.cursor/plugins/local/forgeflow', '/clarify', '/ff-plan', '/execute', '/ff-review', '/ship', '/long-run', '/benchmark', '/ff-config', '콜론 없음', '대상 프로젝트 루트', '~/.forgeflow/projects/<project-slug>/tasks/<task-id>/', 'cache 내부에 task artifact를 만들지 않습니다'],
}
failures = []
for adapter, needles in required.items():
    if f'### {adapter}' not in text:
        failures.append(f'docs/adapter-config.md: missing section ### {adapter}')
    for needle in needles:
        if needle not in text:
            failures.append(f'docs/adapter-config.md: {adapter} missing {needle!r}')
route_labels = ('small', 'medium', 'high', 'epic')
for label in route_labels:
    if f'| {label} |' not in text:
        failures.append(f'docs/adapter-config.md: timeout table missing route {label!r}')
for needle in ('plugin cache',):
    if needle not in text:
        failures.append(f'docs/adapter-config.md: adapter sections must mention {needle!r}')
if failures:
    print('ERROR: Adapter config contract failed')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print('OK: Adapter config covers CLI flags, env signals, route timeouts, and supported adapter surfaces')
