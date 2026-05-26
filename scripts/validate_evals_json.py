#!/usr/bin/env python3
"""Extracted from Makefile target: validate-evals-json"""
import json, pathlib, re, sys
data = json.loads(pathlib.Path('evals/evals.json').read_text(encoding='utf-8'))
failures = []
allowed_assertion_types = {'contains', 'contains_all', 'contains_any', 'equals', 'not_contains', 'not_contains_any'}
if not isinstance(data.get('skill_name'), str):
    failures.append('skill_name missing')
evals = data.get('evals')
if not isinstance(evals, list) or not evals:
    failures.append('evals must be non-empty list')
else:
    ids = [item.get('id') for item in evals if isinstance(item, dict)]
    names = [item.get('name') for item in evals if isinstance(item, dict)]
    expected_ids = list(range(len(evals)))
    if not all(isinstance(item.get('id'), int) and not isinstance(item.get('id'), bool) for item in evals if isinstance(item, dict)):
        failures.append('eval ids must be integers, not strings or booleans')
    if ids != expected_ids:
        failures.append(f'eval ids must be sequential starting at 0: expected {expected_ids}, got {ids}')
    duplicate_names = sorted({name for name in names if isinstance(name, str) and names.count(name) > 1})
    if duplicate_names:
        failures.append(f'eval names must be unique: duplicates {duplicate_names}')
    invalid_names = sorted(name for name in names if isinstance(name, str) and not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name))
    if invalid_names:
        failures.append(f'eval names must be kebab-case slugs: {invalid_names}')
    for i, item in enumerate(evals):
        if not isinstance(item, dict):
            failures.append(f'eval[{i}] must be object')
            continue
        for key in ('id', 'name', 'prompt', 'expected_output', 'files', 'assertions'):
            if key not in item:
                failures.append(f'eval[{i}] missing {key}')
        for key in ('name', 'prompt', 'expected_output'):
            if key in item and (not isinstance(item.get(key), str) or not item.get(key).strip()):
                failures.append(f'eval[{i}] {key} must be a non-empty string')
        files = item.get('files')
        if not isinstance(files, list) or not all(isinstance(path, str) for path in files):
            failures.append(f'eval[{i}] files must be a list of strings')
        assertions = item.get('assertions')
        if not isinstance(assertions, list) or not assertions:
            failures.append(f'eval[{i}] assertions must be non-empty list')
            continue
        for j, assertion in enumerate(assertions):
            if not isinstance(assertion, dict):
                failures.append(f'eval[{i}].assertions[{j}] must be object')
                continue
            assertion_type = assertion.get('type')
            if not isinstance(assertion.get('text'), str) or not assertion.get('text', '').strip():
                failures.append(f'eval[{i}].assertions[{j}] must include non-empty text')
            seen_texts = [a.get('text') for a in assertions[:j] if isinstance(a, dict)]
            if assertion.get('text') in seen_texts:
                _atxt = repr(assertion.get('text'))
                failures.append(f'eval[{i}].assertions[{j}] duplicates assertion text {_atxt}')
            if assertion_type not in allowed_assertion_types:
                failures.append(f'eval[{i}].assertions[{j}] unknown type {assertion_type!r}')
            if assertion_type in {'contains', 'equals', 'not_contains'}:
                if 'values' in assertion:
                    failures.append(f'eval[{i}].assertions[{j}] uses value, not values, for {assertion_type}')
                if not isinstance(assertion.get('value'), str) or not assertion.get('value', '').strip():
                    failures.append(f'eval[{i}].assertions[{j}] must include non-empty non-blank string value')
            elif assertion_type in {'contains_all', 'contains_any', 'not_contains_any'}:
                if 'value' in assertion:
                    failures.append(f'eval[{i}].assertions[{j}] uses values, not value, for {assertion_type}')
                values = assertion.get('values')
                if not isinstance(values, list) or not values or not all(isinstance(v, str) and v.strip() for v in values):
                    failures.append(f'eval[{i}].assertions[{j}] must include non-empty non-blank string values')
                elif len(set(values)) != len(values):
                    duplicates = sorted({v for v in values if values.count(v) > 1})
                    failures.append(f'eval[{i}].assertions[{j}] duplicates assertion values {duplicates}')
if failures:
    print('ERROR: evals/evals.json schema invalid')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print(f'OK: evals/evals.json schema valid ({len(evals)} cases)')

