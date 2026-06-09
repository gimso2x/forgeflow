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

# Section header / body aliases for required_fields.name (snake_case) → template prose labels
FIELD_ALIASES: dict[str, list[str]] = {
    'goal_contract': ['Goal Contract'],
    'goal': ['Goal', 'Plan Readiness', 'Objective', 'Reader Summary'],
    'requirements': ['Requirements', '요구사항'],
    'implementation_steps': ['Tasks', 'Implementation Steps', '작업 목록'],
    'verification': ['Verification Plan', 'Verification', '검증'],
    'decisions': ['Decisions', '결정 사항'],
    'progress': ['Progress', '진행 상황'],
    'evidence': ['Evidence', '증거'],
    'verdict': ['Verdict', '판정'],
    'findings': ['Findings', '발견 사항'],
    'open_blockers': ['Open Blockers', '열린 blocker'],
    'next_action': ['Next Action', '다음 작업'],
    'changed_files': ['Changed Files', '변경 파일'],
    'residual_risks': ['Residual Risks', '잔여 위험'],
    'resume_pointer': ['Resume Pointer'],
    'plan_items': ['Plan Items'],
    'execution_tracking': ['Execution Tracking'],
    'stage': ['Stage', 'Current Stage', '현재 단계'],
    'status': ['Status', '상태'],
    'input_mode': ['input_mode'],
    'review_verdict': ['Review Verdict', '리뷰 판정'],
    'task_id': ['task_id'],
    'route': ['Route', '라우트'],
    'scope_boundary': ['scope_boundary'],
    'ambiguity': ['Ambiguity Score', '모호성 점수'],
    'total_items': ['total_items'],
}

FIELD_BODY_PATTERNS: dict[str, list[str]] = {
    'goal': [r'\*\*Goal\*\*'],
}


def _field_present(field: str, fm: str, body: str) -> bool:
    if re.search(rf'^{re.escape(field)}\s*:', fm, re.MULTILINE):
        return True
    title_case = ' '.join(part.capitalize() for part in field.split('_'))
    candidates = list(dict.fromkeys(
        FIELD_ALIASES.get(field, []) + [title_case, field.replace('_', ' ')]
    ))
    for candidate in candidates:
        if re.search(rf'##[^\n]*\b{re.escape(candidate)}\b', body, re.IGNORECASE):
            return True
    for pattern in FIELD_BODY_PATTERNS.get(field, []):
        if re.search(pattern, body, re.IGNORECASE):
            return True
    return False

# Cross-check: all templates with YAML frontmatter must use consistent schema field name
# review-report.md was using 'schema_version' instead of 'schema' — verify consistency
template_schema_check = {
    'brief.md': 'schema',
    'review-report.md': 'schema',
    'plan.md': 'schema',
    'implementation-notes.md': 'schema',
    'checkpoint.md': 'schema',
    'ship-summary.md': 'schema',
    'input-source.md': 'schema',
    'normalized-input.md': 'schema',
    'ledger.md': 'schema',
    'metrics-dashboard.md': 'schema',
    'project-draft.md': 'schema',
    'telemetry-event.md': 'schema',
    'run-state.json': 'schema',
}

for tmpl_name, expected_field in template_schema_check.items():
    tmpl_path = root / 'templates' / tmpl_name
    if not tmpl_path.exists():
        continue
    tmpl_text = tmpl_path.read_text(encoding='utf-8')
    # Only check files that have YAML frontmatter (start with ---)
    if not tmpl_text.startswith('---'):
        continue
    # Check for 'schema_version' (the old inconsistent name)
    if 'schema_version:' in tmpl_text:
        failures.append(
            f"templates/{tmpl_name}: uses 'schema_version:' instead of '{expected_field}:' — "
            f"must use consistent field name '{expected_field}' across all templates"
        )

if failures:
    print('ERROR: Template field cross-validation failed')
    for f in failures:
        print(f'- {f}')
    sys.exit(1)

print('OK: Template fields consistent with skill expectations')

# --- Warning mode: check required_fields from template YAML frontmatter ---
# New in v2.1.0: templates declare required_fields/optional_fields in frontmatter.
# This block checks that declared required fields exist as frontmatter keys or section headers.
# Warnings do NOT affect exit code unless --strict is passed.

_warnings = []
_strict = '--strict' in sys.argv

_warn_templates = [
    'brief.md', 'plan.md', 'implementation-notes.md',
    'review-report.md', 'ship-summary.md', 'checkpoint.md', 'ledger.md',
]

for _tmpl_name in _warn_templates:
    _tmpl_path = root / 'templates' / _tmpl_name
    if not _tmpl_path.exists():
        continue
    _text = _tmpl_path.read_text(encoding='utf-8')
    # Parse YAML frontmatter
    _fm_match = re.search(r'^---\n(.*?)\n---', _text, re.DOTALL)
    if not _fm_match:
        continue
    _fm = _fm_match.group(1)
    # Extract required_fields entries (lines matching "  - name: <field>")
    _in_required = False
    _req_fields = []
    for _line in _fm.split('\n'):
        if _line.strip() == 'required_fields:':
            _in_required = True
            continue
        if _line.strip() == 'optional_fields:':
            _in_required = False
            continue
        if _in_required and _line.strip().startswith('- name:'):
            _field = _line.strip().replace('- name:', '').strip()
            if _field:
                _req_fields.append(_field)
    # Check each required field: present as frontmatter key OR section header in body
    for _field in _req_fields:
        if not _field_present(_field, _fm, _text):
            _warnings.append(
                f"templates/{_tmpl_name}: missing recommended field '{_field}' "
                f"(declared in required_fields)"
            )

if _warnings:
    import io
    _prefix = 'ERROR' if _strict else 'WARNING'
    _stream = sys.stdout if _strict else sys.stderr
    print(f'{_prefix}: Recommended fields missing ({("strict" if _strict else "warning")} mode)', file=_stream)
    for _w in _warnings:
        print(f'  - {_w}', file=_stream)
    if _strict:
        sys.exit(1)

# --- Next Steps section check (v2.1.0 M2) ---
# Pipeline templates must have a "Next Steps →" section at the end for stage handoff.
_next_steps_templates = {
    'brief.md': 'ff-plan',
    'plan.md': 'execute',
    'implementation-notes.md': 'ff-review',
    'review-report.md': 'ship',
    'ship-summary.md': 'long-run/complete',
}

for _tmpl, _target in _next_steps_templates.items():
    _path = root / 'templates' / _tmpl
    if not _path.exists():
        continue
    _text = _path.read_text(encoding='utf-8')
    _has_next = f'Next Steps → {_target}' in _text
    if not _has_next:
        if _strict:
            print(f'ERROR: templates/{_tmpl}: missing "Next Steps → {_target}" section', file=sys.stdout)
            sys.exit(1)
        else:
            print(f'WARNING: templates/{_tmpl}: missing "Next Steps → {_target}" section', file=sys.stderr)

# --- Cross-artifact stage handoff checks (v2.1.0 M4) ---
# Verify structural consistency between adjacent pipeline templates.
# These checks validate that template *structure* supports stage handoff,
# not that runtime artifacts are consistent (that's forgeflow_guard_check.py territory).
_cross_handoff_checks = [
    {
        'name': 'brief.md ↔ plan.md: route field pair',
        'templates': ('templates/brief.md', 'templates/plan.md'),
        'check': lambda a, b: ('route:' in a or 'route |' in a) and ('route:' in b or 'route |' in b),
        'detail': 'both templates must reference route field',
    },
    {
        'name': 'plan.md ↔ ledger.md: tasks/plan items pair',
        'templates': ('templates/plan.md', 'templates/ledger.md'),
        'check': lambda a, b: ('Tasks' in a or '작업' in a) and ('Plan Items' in b or 'Execution Tracking' in b),
        'detail': 'plan must have tasks, ledger must have Plan Items or Execution Tracking',
    },
    {
        'name': 'review-report.md ↔ ship-summary.md: verdict pair',
        'templates': ('templates/review-report.md', 'templates/ship-summary.md'),
        'check': lambda a, b: 'verdict' in a.lower() and ('review_verdict' in b or 'verdict' in b.lower()),
        'detail': 'review must have verdict, ship-summary must reference verdict',
    },
    {
        'name': 'checkpoint.md: field integrity (Stage, Status, Next Action, Blockers)',
        'templates': ('templates/checkpoint.md',),
        'check': lambda a: all(s in a for s in ['## Stage', '## Status', '## Next Action', '## Blockers']),
        'detail': 'checkpoint must have instant-answer block sections',
    },
]

_cross_prefix = 'ERROR' if _strict else 'WARNING'
_cross_stream = sys.stdout if _strict else sys.stderr

for _check in _cross_handoff_checks:
    _tmpls = _check['templates']
    _texts = {}
    _missing = False
    for _t in _tmpls:
        _p = root / _t
        if not _p.exists():
            _missing = True
            break
        _texts[_t] = _p.read_text(encoding='utf-8')
    if _missing:
        continue
    _vals = list(_texts.values())
    _passed = _check['check'](*_vals)
    if not _passed:
        print(f'{_cross_prefix}: Cross-artifact handoff: {_check["name"]} — {_check["detail"]}', file=_cross_stream)
        if _strict:
            sys.exit(1)
