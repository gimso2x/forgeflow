#!/usr/bin/env python3
"""Extracted from Makefile target: validate-workflow-vocab"""
import pathlib, sys
failures = []
checks = {pathlib.Path('skills/SKILLS.md'): ['→ init             → task workspace']}
for path, stale_terms in checks.items():
    text = path.read_text(encoding='utf-8')
    for stale in stale_terms:
        if stale in text:
            failures.append(f'{path}: use forgeflow-init for user-facing workflow bootstrap, not init')
active_docs = [path for path in pathlib.Path('.').rglob('*.md') if '.git' not in path.parts and '.venv' not in path.parts and '.forgeflow' not in path.parts and path.parts[0] not in {'CHANGELOG.md', 'evals'}]
removed_commands = ('/forgeflow:finish', '/forgeflow:milestone', '/forgeflow-init', '/forgeflow:subagent-execute', '/forgeflow:config')
removed_stage_phrases = ('ship → finish', 'Current Stage: ship' + chr(96) + ' → ' + chr(96) + 'finish')
for path in active_docs:
    text = path.read_text(encoding='utf-8')
    if 'large_high_risk' in text:
        failures.append(f'{path}: active docs must use canonical route labels small/medium/high/epic, not large_high_risk')
    for command in removed_commands:
        if command in text:
            failures.append(f'{path}: active docs must not reference removed command {command!r}')
    for phrase in removed_stage_phrases:
        if phrase in text:
            failures.append(f'{path}: active docs must treat ship as terminal workflow stage, not removed finish stage phrase {phrase!r}')
readme = pathlib.Path('README.md').read_text(encoding='utf-8')
workflow_marker = '## 기본 워크플로우'
workflow = readme.split(workflow_marker, 1)[1].split('## Routes', 1)[0] if workflow_marker in readme and '## Routes' in readme else ''
if '/forgeflow:clarify' not in workflow:
    failures.append('README.md: basic workflow must include /forgeflow:clarify')
route_section = readme.split('## Routes', 1)[1].split('### Route scoring', 1)[0] if '## Routes' in readme and '### Route scoring' in readme else ''
for label in ('small', 'medium', 'high', 'epic'):
    if f'| {label}' not in route_section:
        failures.append(f'README.md: Routes table must document canonical route {label!r}')
for stale in ('large_high_risk', '| low ', '| critical '):
    if stale in route_section:
        failures.append(f'README.md: Routes table contains stale/non-route label {stale!r}')
first_run_marker = '## 첫 실행 예시'
first_run = readme.split(first_run_marker, 1)[1] if first_run_marker in readme else ''
if '> /forgeflow:clarify' not in first_run:
    failures.append('README.md: first-run example must start with /forgeflow:clarify')
if '> /forgeflow:ff-plan' in first_run and 'route: small' in first_run:
    failures.append('README.md: first-run example must not route small and then run plan; small route skips plan')
for needle in ('plugin cache', '--task-dir'):
    if needle not in first_run:
        failures.append(f'README.md: first-run example must warn about plugin cache safety and explicit task dirs (missing {needle!r})')
ship = pathlib.Path('skills/ship/SKILL.md').read_text(encoding='utf-8')
for forbidden in ('Worktree cleanup (before verification)', 'After successful merge (or if user chose "discard")'):
    if forbidden in ship:
        failures.append(f'skills/ship/SKILL.md: worktree preflight must not imply destructive cleanup before option confirmation ({forbidden!r})')
for required in ('Worktree preflight (before verification)', 'Do not remove or discard yet', 'option-specific confirmation'):
    if required not in ship:
        failures.append(f'skills/ship/SKILL.md: missing conservative worktree preflight guardrail {required!r}')
stale_route_terms = ('large_high_risk', 'medium/large')
stale_schema_terms = {
    'selected_architecture': 'brief artifacts no longer expose selected_architecture',
    'success_criteria': 'brief artifacts use acceptance_criteria',
    'progress.percentage': 'run-state progress uses progress.percent',
}
deprecated_artifact_generation_terms = (
    ('`plan-ledger.md` (신규)', 'use `ledger.md` Plan Items instead of presenting deprecated plan-ledger.md as a new artifact'),
    ('`decision-log.md` (신규)', 'use `implementation-notes.md` Decisions instead of presenting deprecated decision-log.md as a new artifact'),
    ('run-ledger.md = per-task status truth', 'use ledger.md as the per-task status truth'),
    ('implementation-notes.md` + `run-ledger.md', 'use `implementation-notes.md` + `ledger.md` Execution Tracking section for post-execute review prerequisites'),
    ('| `run-ledger.md` | plan.md scope |', 'use `ledger.md` Execution Tracking section in post-execute review evidence tables'),
)
scan_roots = [pathlib.Path('README.md'), pathlib.Path('SKILL.md'), pathlib.Path('AGENTS.md'), pathlib.Path('docs'), pathlib.Path('skills'), pathlib.Path('templates'), pathlib.Path('.claude/skills')]
for root in scan_roots:
    paths = [root] if root.is_file() else sorted(root.rglob('*.md'))
    for path in paths:
        text = path.read_text(encoding='utf-8')
        for stale in stale_route_terms:
            if stale in text:
                failures.append(f'{path}: stale route vocabulary {stale!r}; use small/medium/high/epic')
        for stale, guidance in stale_schema_terms.items():
            if stale in text:
                failures.append(f'{path}: stale schema vocabulary {stale!r}; {guidance}')
        for stale, guidance in deprecated_artifact_generation_terms:
            if stale in text:
                failures.append(f'{path}: deprecated artifact generation wording {stale!r}; {guidance}')
lifecycle_expectations = {'README.md': 'ship → long-run', 'SKILL.md': 'ship → long-run', 'skills/forgeflow/SKILL.md': 'ship -> long-run'}
for rel_path, snippet in lifecycle_expectations.items():
    if snippet not in pathlib.Path(rel_path).read_text(encoding='utf-8'):
        failures.append(f'{rel_path}: missing canonical ship -> long-run lifecycle ordering')
skills_md = pathlib.Path('skills/SKILLS.md').read_text(encoding='utf-8')
if '→ ship             → final handoff + branch disposition' not in skills_md or '→ long-run         → eval-record.md' not in skills_md:
    failures.append('skills/SKILLS.md: missing canonical ship -> long-run lifecycle ordering')
for rel_path in ('README.md', 'SKILL.md', 'skills/forgeflow/SKILL.md', 'skills/SKILLS.md'):
    text = pathlib.Path(rel_path).read_text(encoding='utf-8')
    if '/forgeflow:finish' in text or 'ship → long-run → finish' in text or 'ship -> long-run -> finish' in text:
        failures.append(f'{rel_path}: finish is not a separate stage; branch disposition lives in ship')
storage_drift_terms = {
    'FORGEFLOW_STORAGE_MODE': 'storage is always global/project-scoped; use FORGEFLOW_HOME for root overrides',
    'storage.mode': 'storage.mode local has been removed; storage is always global/project-scoped',
    'local storage': 'storage is always global/project-scoped; do not document repo-local task storage',
}
for root in [pathlib.Path('README.md'), pathlib.Path('SKILL.md'), pathlib.Path('AGENTS.md'), pathlib.Path('docs'), pathlib.Path('skills'), pathlib.Path('scripts')]:
    paths = [root] if root.is_file() else sorted(root.rglob('*.md')) + sorted(root.rglob('*.py'))
    for path in paths:
        if path == pathlib.Path('scripts/validate_workflow_vocab.py'):
            continue
        text = path.read_text(encoding='utf-8')
        for stale, guidance in storage_drift_terms.items():
            if stale in text:
                failures.append(f'{path}: stale storage vocabulary {stale!r}; {guidance}')
if failures:
    print('ERROR: Workflow/schema vocabulary drift found')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print('OK: Workflow examples use /forgeflow:clarify, current route vocabulary, and current schema field names')

