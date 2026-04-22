#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_yaml_lines(path: Path):
    return path.read_text(encoding='utf-8').splitlines()


def stage_list_from_workflow(path: Path) -> list[str]:
    stages = []
    capture = False
    for raw in load_yaml_lines(path):
        stripped = raw.strip()
        if stripped == 'stages:':
            capture = True
            continue
        if capture:
            if stripped.startswith('- '):
                stages.append(stripped[2:].strip())
            elif stripped and not raw.startswith('  '):
                break
    return stages


def stage_keys_from_stages(path: Path) -> list[str]:
    keys = []
    capture = False
    for raw in load_yaml_lines(path):
        if raw.strip() == 'stages:':
            capture = True
            continue
        if capture:
            if raw.startswith('  ') and raw.strip().endswith(':') and not raw.strip().startswith('- '):
                keys.append(raw.strip()[:-1])
    return keys


def review_order(path: Path) -> list[str]:
    items = []
    capture = False
    for raw in load_yaml_lines(path):
        stripped = raw.strip()
        if stripped == 'review_order:':
            capture = True
            continue
        if capture:
            if stripped.startswith('- '):
                items.append(stripped[2:].strip())
            elif stripped and not raw.startswith('  '):
                break
    return items


def route_map(path: Path) -> dict[str, list[str]]:
    lines = load_yaml_lines(path)
    routes: dict[str, list[str]] = {}
    current = None
    in_routes = False
    for raw in lines:
        if raw.strip() == 'routes:':
            in_routes = True
            continue
        if not in_routes:
            continue
        if raw.startswith('  ') and not raw.startswith('    ') and raw.strip().endswith(':') and not raw.strip().startswith('- '):
            current = raw.strip()[:-1]
            routes[current] = []
            continue
        if current and raw.startswith('    stages: ['):
            chunk = raw.strip()[len('stages: ['):-1]
            routes[current] = [x.strip() for x in chunk.split(',') if x.strip()]
    return routes


def required_in_schema(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding='utf-8'))
    req = data.get('required', [])
    if not isinstance(req, list):
        raise ValueError(f'required must be a list in {path}')
    return req


def main() -> int:
    errors = []
    workflow = ROOT / 'policy/canonical/workflow.yaml'
    stages_file = ROOT / 'policy/canonical/stages.yaml'
    routes_file = ROOT / 'policy/canonical/complexity-routing.yaml'
    gates_file = ROOT / 'policy/canonical/gates.yaml'

    workflow_stages = stage_list_from_workflow(workflow)
    stage_keys = stage_keys_from_stages(stages_file)
    if workflow_stages != stage_keys:
        errors.append(f'stage mismatch: workflow={workflow_stages} stages={stage_keys}')

    order = review_order(workflow)
    if order != ['spec-review', 'quality-review']:
        errors.append(f'invalid review order: {order}')

    routes = route_map(routes_file)
    if 'small' not in routes or routes['small'] != ['clarify', 'execute', 'quality-review', 'finalize']:
        errors.append('small route mismatch')
    if 'medium' not in routes or routes['medium'] != ['clarify', 'plan', 'execute', 'quality-review', 'finalize']:
        errors.append('medium route mismatch')
    if 'large_high_risk' not in routes or routes['large_high_risk'] != ['clarify', 'plan', 'execute', 'spec-review', 'quality-review', 'finalize', 'long-run']:
        errors.append('large_high_risk route mismatch')

    for schema_name in ['brief', 'plan', 'decision-log', 'run-state', 'review-report', 'eval-record']:
        schema_path = ROOT / 'schemas' / f'{schema_name}.schema.json'
        required = required_in_schema(schema_path)
        if 'schema_version' not in required:
            errors.append(f'{schema_name}.schema.json missing schema_version')
        if 'task_id' not in required:
            errors.append(f'{schema_name}.schema.json missing task_id')

    run_state_required = required_in_schema(ROOT / 'schemas' / 'run-state.schema.json')
    for field in ['spec_review_approved', 'quality_review_approved']:
        if field not in run_state_required:
            errors.append(f'run-state.schema.json missing {field}')

    review_text = (ROOT / 'docs/review-model.md').read_text(encoding='utf-8')
    if 'spec-review 승인 전 finalize 금지' not in review_text:
        errors.append('review-model missing spec-review finalize guard')
    if 'quality-review 승인 전 high-risk finalize 금지' not in review_text:
        errors.append('review-model missing quality-review high-risk guard')
    if 'run-state.spec_review_approved' not in review_text:
        errors.append('review-model missing run-state approval flag guidance')

    gates_text = gates_file.read_text(encoding='utf-8')
    if 'review_type: spec' not in gates_text:
        errors.append('gates missing spec review_type binding')
    if 'review_type: quality' not in gates_text:
        errors.append('gates missing quality review_type binding')
    if 'run_state_flags: [spec_review_approved, quality_review_approved]' not in gates_text:
        errors.append('gates missing finalize run_state_flags binding')

    if errors:
        print('POLICY VALIDATION: FAIL')
        for err in errors:
            print(f'- {err}')
        return 1

    print('POLICY VALIDATION: PASS')
    print(f'- stages: {workflow_stages}')
    print(f'- review order: {order}')
    print(f'- routes checked: {list(routes)}')
    print('- review gate semantics: bound to review_type and run-state flags')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
