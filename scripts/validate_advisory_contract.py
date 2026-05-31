#!/usr/bin/env python3
"""Extracted from Makefile target: validate-advisory-contract"""
import pathlib, re, sys
root = pathlib.Path('.')
checks = {
    'skills/forgeflow/SKILL.md': ['intent:', 'inputs:', 'outputs:', 'dependencies:', 'docs/advisory-guidelines.md'],
    'skills/clarify/SKILL.md': ['intent:', 'inputs:', 'outputs:', 'dependencies:', '리뷰해줘', '계획 세워', 'suggested_next_skill', 'Keyword hints are advisory'],
    'skills/review/SKILL.md': ['docs/review-runtime-contract.md', 'brief / evidence / scope / constraints', 'read-only except for review artifacts', 'observed evidence', 'Cross-role conflicts', 'Evidence Source', 'Evidence Level', 'observed | reported | missing', 'lead/member guardrails', 'does not spawn unmanaged child work'],
    'skills/_shared/automation.md': ['Stage artifact/tool boundary catalog', 'clarify', 'plan', 'execute', 'review', 'ship', 'product code edits', 'Code findings hand back to execute'],
    'templates/brief.md': ['Route Rationale', 'Budget Note', 'Suggested Next Skill', 'Suggested specialists'],
    'templates/review-report.md': ['Evidence Source', 'Evidence Level', 'observed | reported | missing'],
    'templates/plan.md': ['Execution Pattern', 'Applied Evolution Rules'],
    'docs/advisory-guidelines.md': ['Route Budget Guide', 'small:', 'medium:', 'high:', 'epic:', 'Non-goals'],
    'docs/review-runtime-contract.md': ['Adapter-neutral core', 'Thin adapter responsibilities', 'Role separation', 'Stage tool catalog', 'Evidence levels', 'Human review gate', 'Minimal team-mode absorption', 'Lead/member guardrails', 'Claim marker', 'Non-goal', 'input-source.md', 'normalized-input.md'],
    'README.md': ['docs/review-runtime-contract.md', 'adapter-neutral input normalization', 'input-source.md', 'normalized-input.md', 'adapter별 별도 report나 자동 승인 경로 없음'],
}
failures = []
for raw_path, needles in checks.items():
    path = root / raw_path
    if not path.is_file():
        failures.append(f'{raw_path}: missing required file')
        continue
    text = path.read_text(encoding='utf-8')
    for needle in needles:
        if needle not in text:
            failures.append(f'{raw_path}: missing {needle!r}')
clarify = (root / 'skills/clarify/SKILL.md').read_text(encoding='utf-8')
if 'auto-invoke' in clarify.lower() and 'Do not auto-invoke' not in clarify:
    failures.append('skills/clarify/SKILL.md: alias hints must stay non-invoking/advisory')
for sf in ['skills/forgeflow/SKILL.md', 'skills/clarify/SKILL.md']:
    text = (root / sf).read_text(encoding='utf-8')
    m = re.search(r'^---\s*\n(.*?\n)---\s*\n', text, re.DOTALL)
    if not m:
        failures.append(f'{sf}: YAML frontmatter block not found')
        continue
    yaml_block = m.group(1)
    for field in ('intent:', 'inputs:', 'outputs:', 'dependencies:'):
        if field not in yaml_block:
            failures.append(f'{sf}: field {field!r} missing inside frontmatter')
    try:
        {k: v for k, v in [line.split(':', 1) for line in yaml_block.strip().splitlines() if ':' in line and not line.strip().startswith('-')]}
    except Exception as exc:
        failures.append(f'{sf}: frontmatter parse error: {exc}')
review_template = (root / 'templates/review-report.md').read_text(encoding='utf-8')
role_pos = review_template.find('**Role**')
source_pos = review_template.find('**Evidence Source**')
level_pos = review_template.find('**Evidence Level**')
description_pos = review_template.find('**Description**')
if not (role_pos != -1 and source_pos != -1 and level_pos != -1 and description_pos != -1 and role_pos < source_pos < level_pos < description_pos):
    failures.append('templates/review-report.md: finding fields must include Role, Evidence Source, and Evidence Level before Description')
if failures:
    print('ERROR: advisory contract drift')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print('OK: advisory metadata, alias hints, stage tool boundaries, advisory docs, and YAML frontmatter integrity')

