#!/usr/bin/env python3
"""Extracted from Makefile target: validate-advisory-contract"""
import pathlib, re, sys
root = pathlib.Path('.')
checks = {
    'skills/forgeflow/SKILL.md': ['intent:', 'inputs:', 'outputs:', 'dependencies:', 'docs/advisory-guidelines.md'],
    'skills/clarify/SKILL.md': ['intent:', 'inputs:', 'outputs:', 'dependencies:', '리뷰해줘', '계획 세워', 'suggested_next_skill', 'Keyword hints are advisory'],
    'skills/review/SKILL.md': ['docs/review-runtime-contract.md', 'brief / evidence / scope / constraints', 'read-only except for review artifacts', 'observed evidence', 'Cross-role conflicts', 'Evidence Source', 'Evidence Level', 'observed | reported | missing', 'lead/member guardrails', 'does not spawn unmanaged child work', 'Adapter compliance checklist', 'source classified', 'fetch reproduced', 'normalization complete', 'limitations visible', 'review ownership delegated', 'Checklist Version', 'Review tool posture', 'hand it back to execute', 'role-pass record', 'chat-only role completion claims', 'role routing rationale', 'Active roles', 'Skipped roles', 'silently broadening or narrowing review scope', 'role=<reviewer> scope=<artifact section/evidence IDs> at=<ISO8601>', 'role evidence map', 'stable evidence IDs', 'Role trigger matrix', 'missing trigger evidence', '.diff` / `.patch`', 'Evidence Escalation Log', 'hidden adapter state', 'role input packet'],
    'skills/review/references/role-checklists.md': ['Checklist version:', 'role input packet', 'Role trigger matrix', 'role evidence map', 'scoped files/ranges/exclusions', 'constraints/focus flags', 'Evidence Escalation Log', 'blocked: missing role input packet'],
    'skills/execute/SKILL.md': ['Claim marker before delegation/concurrency', 'role=<worker|specialist|spec-reviewer|quality-reviewer> scope=<repo paths or artifact section> at=<ISO8601>', 'Run ledger claim markers'],
    'skills/_shared/automation.md': ['Stage artifact/tool boundary catalog', 'clarify', 'plan', 'execute', 'review', 'ship', 'product code edits', 'Code findings hand back to execute'],
    'templates/brief.md': ['Route Rationale', 'Budget Note', 'Suggested Next Skill', 'Suggested specialists'],
    'templates/review-report.md': ['Evidence Source', 'Evidence Level', 'observed | reported | missing', 'Checklist Version', 'role-pass record', 'Chat-only completion claims are not evidence', 'Normalization Gate', 'Role routing rationale', 'Role evidence map', 'Review ownership plan', 'Active roles', 'Skipped roles', 'Trigger Rationale', 'Claim Marker', 'Independence Check', 'Evidence Escalation Log', 'Requester Role', 'Approval Impact'],
    'templates/normalized-input.md': ['brief_present', 'evidence_present_or_blocked', 'scope_explicit', 'constraints_explicit', 'limitations_visible', 'role evidence map', 'stable evidence IDs', 'fetch_status', 'limitations', 'ignored_flags', 'Role trigger matrix', 'run | skipped | blocked', 'role input packet readiness', 'READY | BLOCKED | SKIPPED', 'review ownership plan', 'lead_reviewer', 'member_assignments', 'aggregation_owner', 'child_work_policy', 'product_mutation_policy', 'adapter handoff checklist', 'source_classified', 'fetch_reproduced', 'normalization_complete', 'canonical_review_ownership'],
    'templates/plan.md': ['Execution Pattern', 'Applied Evolution Rules'],
    'templates/run-ledger.md': ['Claim Marker', 'role=<worker|specialist|spec-reviewer|quality-reviewer> scope=<repo paths or artifact section> at=<ISO8601>', 'not chat-only claims'],
    'docs/advisory-guidelines.md': ['Route Budget Guide', 'small:', 'medium:', 'high:', 'epic:', 'Non-goals'],
    'docs/review-runtime-contract.md': ['Adapter-neutral core', 'Thin adapter responsibilities', 'Adapter compliance checklist', 'Source classified', 'Fetch reproduced', 'Normalization complete', 'Limitations visible', 'Review ownership delegated', 'Role separation', 'Stage tool catalog', 'Evidence levels', 'Human review gate', 'Minimal team-mode absorption', 'Lead/member guardrails', 'Claim marker', 'Ownership plan', 'role=<reviewer> scope=<artifact section/evidence IDs> at=<ISO8601>', 'Non-goal', 'input-source.md', 'normalized-input.md', 'source classification rationale', 'role-pass record', 'Active roles', 'Skipped roles', 'Chat-only role completion claims', 'role evidence map', 'stable ID', 'fetch_status', 'ignored_flags', 'Evidence Source Map', 'role trigger matrix', 'missing trigger evidence', '.diff` / `.patch` file path', 'Independence Check', 'Evidence escalation log', 'hidden adapter state', 'role input packet'],
    'README.md': ['docs/review-runtime-contract.md', 'adapter-neutral input normalization', 'input-source.md', 'normalized-input.md', 'source classification rationale', 'role trigger matrix', 'review ownership plan', 'ignored flags', 'adapter별 별도 report나 자동 승인 경로 없음', '.diff`/`.patch` 파일', 'lead reviewer', 'member reviewer', 'unmanaged child work', 'role=<reviewer> scope=<artifact section/evidence IDs> at=<ISO8601>', 'Multi-harness 원칙', 'adapter-neutral core contract', 'hidden provider state', 'Evidence Escalation Log', 'role input packet'],
    'docs/adapter-config.md': ['Multi-harness routing invariants', 'Canonical stage contract first', 'Harness-specific code paths stay shallow', 'Artifact handoff is the boundary', 'Review adapters normalize before judging', 'Validation follows touched surface'],
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
if 'Checklist Version' not in review_template or 'Checklist version: YYYY-MM-DD' not in review_template:
    failures.append('templates/review-report.md: reviewer role summary must capture the exact role checklist version')
role_pass_fields = [
    'Role-pass record:',
    '**Claim Marker**',
    '**Scope/Evidence IDs Inspected**',
    '**Trigger Rationale**',
    '**Observed Verification**',
    '**Limitations/Truncation Seen**',
    '**Independence Check**',
    '**Finding Counts**',
    '**Role Verdict**',
]
missing_role_pass_fields = [field for field in role_pass_fields if field not in review_template]
if missing_role_pass_fields:
    failures.append(f'templates/review-report.md: missing explicit role-pass fields {missing_role_pass_fields}')
input_source_template = (root / 'templates/input-source.md').read_text(encoding='utf-8')
classification_fields = ['Source Classification Rationale', 'Why this type', 'Ambiguities considered', 'Ambiguity outcome', 'Evidence Source Map', 'type=diff|file|artifact|url|command_output|reported_summary|missing', 'evidence_level=observed|reported|missing']
missing_classification_fields = [field for field in classification_fields if field not in input_source_template]
if missing_classification_fields:
    failures.append(f'templates/input-source.md: missing source classification fields {missing_classification_fields}')
normalized_input_template = (root / 'templates/normalized-input.md').read_text(encoding='utf-8')
normalization_gate_fields = [
    'brief_present',
    'evidence_present_or_blocked',
    'scope_explicit',
    'constraints_explicit',
    'limitations_visible',
]
missing_gate_fields = [field for field in normalization_gate_fields if field not in normalized_input_template]
if missing_gate_fields:
    failures.append(f'templates/normalized-input.md: missing normalization gate fields {missing_gate_fields}')
adapter_handoff_fields = [
    'source_classified',
    'fetch_reproduced',
    'normalization_complete',
    'limitations_visible',
    'canonical_review_ownership',
]
missing_handoff_fields = [field for field in adapter_handoff_fields if field not in normalized_input_template]
if missing_handoff_fields:
    failures.append(f'templates/normalized-input.md: missing adapter handoff checklist fields {missing_handoff_fields}')
role_trigger_roles = [
    'spec-reviewer',
    'quality-reviewer',
    'security-reviewer',
    'ux-reviewer',
    'perf-reviewer',
]
trigger_matrix_pos = normalized_input_template.find('### Role trigger matrix')
role_evidence_map_pos = normalized_input_template.find('## role evidence map')
role_packet_readiness_pos = normalized_input_template.find('## role input packet readiness')
ownership_plan_pos = normalized_input_template.find('## review ownership plan')
normalization_gate_pos = normalized_input_template.find('## normalization gate')
adapter_handoff_pos = normalized_input_template.find('## adapter handoff checklist')
if not (trigger_matrix_pos != -1 and role_evidence_map_pos != -1 and role_packet_readiness_pos != -1 and ownership_plan_pos != -1 and normalization_gate_pos != -1 and adapter_handoff_pos != -1 and trigger_matrix_pos < role_evidence_map_pos < role_packet_readiness_pos < ownership_plan_pos < normalization_gate_pos < adapter_handoff_pos):
    failures.append('templates/normalized-input.md: role trigger matrix must appear before role evidence map, role input packet readiness, review ownership plan, normalization gate, and adapter handoff checklist')
def section_between(text, start_marker, end_marker):
    start = text.find(start_marker)
    if start == -1:
        return ''
    end = text.find(end_marker, start + len(start_marker))
    return text[start:end if end != -1 else len(text)]

role_trigger_section = section_between(normalized_input_template, '### Role trigger matrix', '## role evidence map')
role_evidence_section = section_between(normalized_input_template, '## role evidence map', '## role input packet readiness')
role_packet_section = section_between(normalized_input_template, '## role input packet readiness', '## review ownership plan')
for role in role_trigger_roles:
    role_marker = f'**{role}**'
    if role_marker not in role_trigger_section:
        failures.append(f'templates/normalized-input.md: role trigger matrix must include {role}')
    if role_marker not in role_evidence_section:
        failures.append(f'templates/normalized-input.md: role evidence map must include {role}')
    if role_marker not in role_packet_section:
        failures.append(f'templates/normalized-input.md: role input packet readiness must include {role}')
if 'trigger:' not in role_trigger_section or 'evidence:' not in role_trigger_section:
    failures.append('templates/normalized-input.md: role trigger rows must preserve trigger and evidence fields')
packet_required_fragments = ['READY | BLOCKED | SKIPPED', 'trigger,evidence_ids,scope,constraints,limitations']
missing_packet_fragments = [fragment for fragment in packet_required_fragments if fragment not in role_packet_section]
if missing_packet_fragments:
    failures.append(f'templates/normalized-input.md: role input packet readiness must preserve readiness enum and required packet fields {missing_packet_fragments}')
automation_doc = (root / 'skills/_shared/automation.md').read_text(encoding='utf-8')
stage_order = ['clarify', 'plan', 'execute', 'review', 'ship']
stage_positions = []
for stage in stage_order:
    marker = f'- **{stage}** — owns'
    pos = automation_doc.find(marker)
    if pos == -1:
        failures.append(f'skills/_shared/automation.md: missing stage boundary entry {marker!r}')
    else:
        stage_positions.append((stage, pos))
        line_end = automation_doc.find('\n', pos)
        stage_line = automation_doc[pos: line_end if line_end != -1 else len(automation_doc)]
        if 'Allowed posture:' not in stage_line or 'Forbidden:' not in stage_line:
            failures.append(f'skills/_shared/automation.md: stage boundary entry for {stage} must include Allowed posture and Forbidden on the same line')
if len(stage_positions) == len(stage_order):
    ordered_positions = [pos for _, pos in stage_positions]
    if ordered_positions != sorted(ordered_positions):
        failures.append('skills/_shared/automation.md: stage boundary entries must stay in workflow order clarify → plan → execute → review → ship')
if 'forbidden action being delegated' not in automation_doc:
    failures.append('skills/_shared/automation.md: Handoff Boundary must record forbidden-action delegation')
review_gate_pos = review_template.find('**Normalization Gate**')
standalone_pos = review_template.find('## Standalone 입력 소스')
reader_summary_pos = review_template.find('## 사용자용 요약')
if not (standalone_pos != -1 and review_gate_pos != -1 and reader_summary_pos != -1 and standalone_pos < review_gate_pos < reader_summary_pos):
    failures.append('templates/review-report.md: standalone normalization gate must be visible before reader summary')
if failures:
    print('ERROR: advisory contract drift')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print('OK: advisory metadata, alias hints, stage tool boundaries, advisory docs, and YAML frontmatter integrity')

