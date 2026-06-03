#!/usr/bin/env python3
"""Validate that template fields referenced by skills exist in the actual templates.

Cross-references skill expectations against template content:
1. Skill → template section mentions (e.g., Goal Contract fields in brief.md)
2. Skill → template schema fields (YAML frontmatter)
3. Skill → artifact field expectations (e.g., review-report verdict enum)
"""
import pathlib, re, sys

root = pathlib.Path('.')
failures = []

# Map: (skill_file, template_file, required_sections)
# Each entry: skill references these section headers/fields in the template.
skill_template_contract = [
    {
        'skill': 'skills/clarify/SKILL.md',
        'template': 'templates/brief.md',
        'required_sections': [
            ('Goal Contract', 'clarify step 11 requires Goal Contract'),
            ('성공 기준', 'Goal Contract 성공 기준 field'),
            ('필수 증거', 'Goal Contract 필수 증거 field'),
            ('인정된 리스크', 'Goal Contract 인정된 리스크 field'),
            ('명시적 제외', 'Goal Contract 명시적 제외 field'),
            ('scope_boundary', 'brief frontmatter scope_boundary'),
            ('specialist', 'brief frontmatter specialist'),
            ('route', 'brief route field'),
        ],
    },
    {
        'skill': 'skills/ff-review/SKILL.md',
        'template': 'templates/review-report.md',
        'required_sections': [
            ('Standalone', 'review standalone mode section'),
            ('verdict', 'review verdict field'),
            ('Findings', 'review findings section'),
            ('specialist_profile', 'review frontmatter specialist_profile'),
            ('scope_boundary', 'review frontmatter scope_boundary'),
        ],
    },
    {
        'skill': 'skills/ff-plan/SKILL.md',
        'template': 'templates/plan.md',
        'required_sections': [
            ('Architecture Notes', 'plan architecture notes'),
            ('아키텍처 메모', 'plan architecture notes (Korean)'),
            ('Self-Critique', 'plan self-critique section'),
            ('Verification Plan', 'plan verification section'),
            ('검증 계획', 'plan verification section (Korean)'),
        ],
    },
    {
        'skill': 'skills/execute/SKILL.md',
        'template': 'templates/ledger.md',
        'required_sections': [
            ('Execution Tracking', 'ledger execution tracking'),
            ('Plan Items', 'ledger plan items'),
            ('Claim Marker', 'ledger claim marker'),
        ],
    },
    {
        'skill': 'skills/execute/SKILL.md',
        'template': 'templates/implementation-notes.md',
        'required_sections': [
            ('Decisions', 'implementation decisions'),
            ('Evidence', 'implementation evidence'),
        ],
    },
    {
        'skill': 'skills/ship/SKILL.md',
        'template': 'templates/ship-summary.md',
        'required_sections': [
            ('evolution', 'ship evolution rule extraction'),
        ],
    },
]

for contract in skill_template_contract:
    skill_path = root / contract['skill']
    template_path = root / contract['template']

    if not skill_path.exists():
        failures.append(f"{contract['skill']}: skill file not found (cannot validate)")
        continue
    if not template_path.exists():
        failures.append(f"{contract['template']}: template file not found (referenced by {contract['skill']})")
        continue

    template_text = template_path.read_text(encoding='utf-8')

    for section_token, description in contract['required_sections']:
        if section_token not in template_text:
            failures.append(
                f"{contract['template']}: missing '{section_token}' "
                f"({description}) referenced by {contract['skill']}"
            )

# Cross-check: skill frontmatter schema fields vs template frontmatter
# Verify that brief.md template has all YAML frontmatter fields that clarify skill promises
brief_template = root / 'templates/brief.md'
clarify_skill = root / 'skills/clarify/SKILL.md'

if brief_template.exists() and clarify_skill.exists():
    brief_text = brief_template.read_text(encoding='utf-8')
    brief_fm = {}
    in_fm = False
    fm_count = 0
    for line in brief_text.split('\n'):
        stripped = line.strip()
        if stripped == '---':
            fm_count += 1
            if fm_count == 2:
                break
            continue
        if fm_count == 1 and ':' in stripped:
            key = stripped.split(':')[0].strip()
            if key and not key.startswith('#'):
                brief_fm[key] = True

    # Fields that MUST be in brief frontmatter
    required_fm_fields = ['schema', 'task_id', 'route', 'specialist', 'scope_boundary']
    for field in required_fm_fields:
        if field not in brief_fm:
            failures.append(f"templates/brief.md: missing frontmatter field '{field}' required by clarify skill")

if failures:
    print('ERROR: Template field cross-validation failed')
    for f in failures:
        print(f'- {f}')
    sys.exit(1)

print('OK: Template fields consistent with skill expectations')
