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


def require_text(path, needle, message):
    text = (root / path).read_text(encoding='utf-8')
    if needle not in text:
        failures.append(f'{path}: {message}')


def require_all_skill_refs(pattern, needle, message):
    for path in sorted(root.glob(pattern)):
        text = path.read_text(encoding='utf-8')
        if needle not in text:
            failures.append(f'{path}: {message}')

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

checks = [
    ('skills/_shared/discipline.md', '~/.gemini/antigravity-cli/plugins', 'shared discipline must protect Antigravity CLI plugin cache paths'),
    ('skills/clarify/SKILL.md', '~/.gemini/antigravity-cli/plugins', 'clarify must protect Antigravity CLI plugin cache paths'),
    ('skills/_shared/preflight.md', 'git status --short --branch', 'preflight must inspect git branch/ahead-behind status before maintainer mutations'),
    ('skills/_shared/preflight.md', 'git branch --show-current', 'preflight must use an explicit branch command before maintainer mutations'),
    ('skills/_shared/preflight.md', 'confirm the current branch is the expected target branch', 'preflight must confirm the expected target branch before maintainer mutations'),
    ('skills/_shared/preflight.md', 'If the branch is not the configured target branch', 'preflight must stop on wrong branch before pull/edit/commit/push'),
    ('skills/_shared/preflight.md', 'git pull --ff-only', 'preflight must document ff-only refresh after clean status'),
    ('skills/_shared/preflight.md', 'Re-read `AGENTS.md` after the pull', 'preflight must re-read AGENTS.md after ff-only refresh'),
    ('skills/_shared/preflight.md', 'Shared preflight procedure for maintainer automation', 'preflight overview must cover maintainer automation'),
    ('skills/_shared/preflight.md', 'then immediately rerun `git status --short`', 'preflight must re-check dirty status after ff-only refresh'),
    ('skills/_shared/preflight.md', 'Report the dirty paths as user/unknown changes', 'preflight must stop and report unknown dirty paths'),
    ('skills/_shared/preflight.md', 'rerun `git status --short` before staging', 'preflight must re-check dirty status before staging intentional files'),
    ('skills/_shared/preflight.md', 'Stage only the files you intentionally changed in this run', 'preflight must stage only intentional current-run files'),
    ('skills/_shared/preflight.md', 'After commit and push, rerun `git status --short`', 'preflight must re-check dirty status after push before reporting clean'),
    ('skills/_shared/preflight.md', 'git push origin HEAD:refs/heads/main', 'preflight must document explicit branch push to avoid branch/tag collisions'),
    ('skills/_shared/preflight.md', 'Do not schedule jobs, modify cron/crontab, or change external automation', 'preflight must keep scheduled-run cadence changes operator-owned'),
    ('skills/_shared/preflight.md', 'Never run broad cleanup commands such as `git clean -fdX`', 'preflight must forbid broad destructive cleanup in scheduled maintainer runs'),
    ('skills/_shared/preflight.md', 'inspect `git status --short --ignored` first', 'preflight must require ignored-status inspection before any targeted cleanup'),
    ('skills/_shared/preflight.md', 'Do not call separate message-delivery tools', 'preflight must keep scheduled-run delivery in final response only'),
    ('skills/_shared/preflight.md', 'Use the headings `요약`, `변경한 것`, `검증`, `커밋/푸시`, `다음 후보`, and `블로커`', 'preflight must document scheduled-run report headings'),
    ('skills/_shared/preflight.md', 'use exactly `[SILENT]` only when there is genuinely nothing new to report', 'preflight must document exact scheduled-run silent suppression'),
    ('README.md', 'make validate-agent-docs', 'README local validation docs must include focused AGENTS/preflight validation'),
    ('README.md', 'shared discipline/automation linkage', 'README local validation docs must mention shared discipline/automation linkage'),
]
for path, needle, message in checks:
    require_text(path, needle, message)
require_all_skill_refs('skills/*/SKILL.md', '_shared/discipline.md', 'skill must reference shared discipline rules')
for path in [
    'skills/forgeflow/SKILL.md',
    'skills/clarify/SKILL.md',
    'skills/ff-plan/SKILL.md',
    'skills/execute/SKILL.md',
    'skills/ff-review/SKILL.md',
    'skills/ship/SKILL.md',
]:
    require_text(path, '_shared/automation.md', 'core workflow skill must reference shared automation rules')

if failures:
    print('ERROR: AGENTS/preflight docs contract drift')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print(f'OK: AGENTS.md lists {len(active)} active skills and maintainer guardrails')

