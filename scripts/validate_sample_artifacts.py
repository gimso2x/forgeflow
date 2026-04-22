#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = {
    'examples/artifacts/brief.sample.json': 'schemas/brief.schema.json',
    'examples/artifacts/plan.sample.json': 'schemas/plan.schema.json',
    'examples/artifacts/decision-log.sample.json': 'schemas/decision-log.schema.json',
    'examples/artifacts/run-state.sample.json': 'schemas/run-state.schema.json',
    'examples/artifacts/review-report-spec.sample.json': 'schemas/review-report.schema.json',
    'examples/artifacts/review-report-quality.sample.json': 'schemas/review-report.schema.json',
    'examples/artifacts/eval-record.sample.json': 'schemas/eval-record.schema.json',
}


def validate_value(value, schema, path: str, errors: list[str]):
    schema_type = schema.get('type')
    if schema_type == 'object':
        if not isinstance(value, dict):
            errors.append(f'{path}: expected object')
            return
        required = schema.get('required', [])
        for key in required:
            if key not in value:
                errors.append(f'{path}: missing required key {key}')
        props = schema.get('properties', {})
        if schema.get('additionalProperties') is False:
            unknown = [key for key in value if key not in props]
            for key in unknown:
                errors.append(f'{path}: unknown key {key}')
        for key, subschema in props.items():
            if key in value:
                validate_value(value[key], subschema, f'{path}.{key}', errors)
    elif schema_type == 'array':
        if not isinstance(value, list):
            errors.append(f'{path}: expected array')
            return
        item_schema = schema.get('items', {})
        for idx, item in enumerate(value):
            validate_value(item, item_schema, f'{path}[{idx}]', errors)
    elif schema_type == 'string':
        if not isinstance(value, str):
            errors.append(f'{path}: expected string')
            return
        if 'enum' in schema and value not in schema['enum']:
            errors.append(f'{path}: invalid enum value {value}')
    elif schema_type == 'boolean':
        if not isinstance(value, bool):
            errors.append(f'{path}: expected boolean')
    elif schema_type == 'integer':
        if not isinstance(value, int):
            errors.append(f'{path}: expected integer')
            return
        minimum = schema.get('minimum')
        if minimum is not None and value < minimum:
            errors.append(f'{path}: expected integer >= {minimum}')
    else:
        if 'enum' in schema and value not in schema['enum']:
            errors.append(f'{path}: invalid enum value {value}')
        if 'additionalProperties' in schema and isinstance(value, dict):
            sub = schema['additionalProperties']
            for key, val in value.items():
                validate_value(val, sub, f'{path}.{key}', errors)


def main() -> int:
    errors = []
    for sample_rel, schema_rel in SAMPLES.items():
        sample_path = ROOT / sample_rel
        schema_path = ROOT / schema_rel
        sample = json.loads(sample_path.read_text(encoding='utf-8'))
        schema = json.loads(schema_path.read_text(encoding='utf-8'))
        validate_value(sample, schema, sample_rel, errors)
    if errors:
        print('SAMPLE ARTIFACT VALIDATION: FAIL')
        for err in errors:
            print(f'- {err}')
        return 1
    print('SAMPLE ARTIFACT VALIDATION: PASS')
    for sample_rel in SAMPLES:
        print(f'- checked {sample_rel}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
