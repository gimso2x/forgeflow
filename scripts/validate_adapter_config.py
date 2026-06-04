#!/usr/bin/env python3
"""Extracted from Makefile target: validate-adapter-config"""
import pathlib, sys
text = pathlib.Path('docs/adapter-config.md').read_text(encoding='utf-8')
readme = pathlib.Path('README.md').read_text(encoding='utf-8')
required = {
    'Claude Code': ['claude -p', '--dangerously-skip-permissions', 'CLAUDE_CODE_SESSION=1', '대상 프로젝트 루트', 'plugin cache'],
    'Codex CLI': ['codex exec', 'danger-full-access', 'CODEX_SESSION=1', '대상 프로젝트 루트', 'plugin cache'],
    'Gemini CLI': ['gemini -p', '--yolo', '--skip-trust', 'GEMINI_CLI=1', 'gemini extensions install', 'Extension 업데이트', 'gemini extensions update forgeflow', 'gemini extensions list', 'gemini extensions validate .', 'gemini extensions link .'],
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
gemini_update = 'printf ' + chr(39) + 'Y' + chr(92) + 'n' + chr(39) + ' ' + chr(124) + ' gemini extensions update forgeflow'
if gemini_update not in readme:
    failures.append('README.md: Gemini automated update example must pipe explicit Y confirmation')
if 'gemini extensions list' not in readme:
    failures.append('README.md: Gemini quickstart must verify extension visibility with gemini extensions list')
for needle in ('대상 프로젝트 루트', '.codex/plugins/forgeflow', 'install-codex-local', 'CODEX_LOCAL_PLUGIN_DIR', 'plugin.json', 'skills/', 'templates/'):
    if needle not in readme:
        failures.append(f'README.md: Codex quickstart must document {needle!r}')
for needle in ('대상 프로젝트 루트', 'plugin cache'):
    if needle not in text:
        failures.append(f'docs/adapter-config.md: Codex section must warn about {needle!r}')
for path, body in ((pathlib.Path('README.md'), readme), (pathlib.Path('docs/adapter-config.md'), text)):
    if '--consent' in body:
        failures.append(f'{path}: Gemini extensions update currently has no --consent flag; pipe explicit Y instead')
if failures:
    print('ERROR: Adapter config contract failed')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print('OK: Adapter config covers CLI flags, env signals, route timeouts, Gemini update confirmation, and extension list verification')

