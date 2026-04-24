#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
TARGETS_DIR = ROOT / 'adapters' / 'targets'
GENERATED_DIR = ROOT / 'adapters' / 'generated'
PROMPTS_DIR = ROOT / 'prompts' / 'canonical'
POLICY_DIR = ROOT / 'policy' / 'canonical'
MANIFEST_SCHEMA = json.loads((ROOT / 'adapters' / 'manifest.schema.json').read_text(encoding='utf-8'))
MANIFEST_VALIDATOR = Draft202012Validator(MANIFEST_SCHEMA)

ROLE_FILE_MAP = {
    'coordinator': 'coordinator.md',
    'planner': 'planner.md',
    'worker': 'worker.md',
    'spec-reviewer': 'spec-reviewer.md',
    'quality-reviewer': 'quality-reviewer.md',
}


def load_manifest(path: Path) -> dict[str, object]:
    data: dict[str, object] = {}
    current_list: list[str] | None = None
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.rstrip()
        if not line:
            continue
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if stripped.startswith('- '):
            if current_list is None:
                raise ValueError(f'list item without key in {path}')
            current_list.append(stripped[2:].strip())
            continue
        if ':' not in stripped:
            raise ValueError(f'invalid manifest line in {path}: {stripped}')
        key, value = stripped.split(':', 1)
        key = key.strip()
        value = value.strip()
        if value == '':
            current_list = []
            data[key] = current_list
        elif value.lower() == 'true':
            data[key] = True
            current_list = None
        elif value.lower() == 'false':
            data[key] = False
            current_list = None
        else:
            data[key] = value
            current_list = None
    return data


def validate_manifest(manifest: dict[str, object], source: Path) -> None:
    required = MANIFEST_SCHEMA['required']
    props = MANIFEST_SCHEMA['properties']
    missing = [key for key in required if key not in manifest]
    if missing:
        raise ValueError(f'{source}: missing required keys {missing}')
    unknown = [key for key in manifest if key not in props]
    if unknown:
        raise ValueError(f'{source}: unknown keys {unknown}')
    if not isinstance(manifest['supports_roles'], list):
        raise ValueError(f'{source}: supports_roles must be a list')
    if not isinstance(manifest['tooling_constraints'], list):
        raise ValueError(f'{source}: tooling_constraints must be a list')
    for role in manifest['supports_roles']:
        if role not in ROLE_FILE_MAP:
            raise ValueError(f'{source}: unsupported role {role}')
    errors = sorted(MANIFEST_VALIDATOR.iter_errors(manifest), key=lambda err: list(err.path))
    if errors:
        details = '; '.join(f"{'/'.join(map(str, err.path)) or '<root>'}: {err.message}" for err in errors[:3])
        raise ValueError(f'{source}: schema validation failed: {details}')


def file_for_target(name: str, manifest: dict[str, object] | None = None) -> str:
    if manifest is not None:
        generated_filename = manifest.get('generated_filename')
        if isinstance(generated_filename, str) and generated_filename:
            return generated_filename
    mapping = {
        'claude': 'CLAUDE.md',
        'codex': 'CODEX.md',
        'cursor': 'HARNESS_CURSOR.md',
    }
    return mapping.get(name, f'{name.upper()}.md')


def build_content(target: str, manifest: dict[str, object]) -> str:
    workflow = (POLICY_DIR / 'workflow.yaml').read_text(encoding='utf-8').strip()
    recovery = (POLICY_DIR / 'recovery.yaml').read_text(encoding='utf-8').strip()
    supported_roles = manifest.get('supports_roles', [])
    role_files = [ROLE_FILE_MAP[role] for role in supported_roles]
    roles_blob = '\n\n'.join((PROMPTS_DIR / name).read_text(encoding='utf-8').strip() for name in role_files)
    roles = ', '.join(supported_roles)
    constraints = '\n'.join(f'- {item}' for item in manifest.get('tooling_constraints', []))
    generated_filename = manifest.get('generated_filename')
    recommended_location = manifest.get('recommended_location')
    surface_style = manifest.get('surface_style')
    handoff_format = manifest.get('handoff_format')
    installation_steps = manifest.get('installation_steps', [])
    installation_steps_blob = '\n'.join(
        f'{index}. {step}' for index, step in enumerate(installation_steps, start=1)
    )
    session_persistence = manifest.get('session_persistence')
    workspace_boundary = manifest.get('workspace_boundary')
    review_delivery = manifest.get('review_delivery')
    delivery_note = manifest.get('recovery_delivery_note')
    parts = [
        f'# {target.capitalize()} ForgeFlow Adapter',
        '',
        'This file is generated from canonical harness policy.',
        'Do not edit manually. Update canonical docs/policy/prompts and rerun `scripts/generate_adapters.py`.',
        '',
        '## Adapter manifest summary',
        f'- name: {manifest.get("name")}',
        f'- runtime_type: {manifest.get("runtime_type")}',
        f'- input_mode: {manifest.get("input_mode")}',
        f'- output_mode: {manifest.get("output_mode")}',
        f'- supports_roles: {roles}',
        f'- supports_generated_files: {manifest.get("supports_generated_files")}',
        '',
        '## Installation guidance',
        f'- generated_filename: {generated_filename}',
        f'- recommended_location: {recommended_location}',
        f'- Copy this generated adapter into `{recommended_location}` when wiring ForgeFlow into {target}.',
        '',
        '## Installation steps',
        installation_steps_blob,
        '',
        '## Target operating notes',
        f'- surface_style: {surface_style}',
        f'- handoff_format: {handoff_format}',
        '',
        '## Runtime realism contract',
        f'- session_persistence: {session_persistence}',
        f'- workspace_boundary: {workspace_boundary}',
        f'- review_delivery: {review_delivery}',
        '',
        '## Non-negotiable rules',
        '- Do not change canonical stage semantics.',
        '- Do not bypass artifact gates.',
        '- Do not merge spec review and quality review.',
        '- Do not treat worker self-report as sufficient evidence.',
        '',
        '## Tooling constraints',
        constraints,
        '',
        '## Recovery contract',
        f'- delivery_note: {delivery_note}',
        '```yaml',
        recovery,
        '```',
        '',
        '## Canonical workflow snapshot',
        '```yaml',
        workflow,
        '```',
        '',
        '## Canonical role prompts',
        '',
        roles_blob,
        '',
    ]
    return '\n'.join(parts)


def main() -> int:
    generated = []
    for manifest_path in sorted(TARGETS_DIR.glob('*/manifest.yaml')):
        manifest = load_manifest(manifest_path)
        validate_manifest(manifest, manifest_path)
        target = manifest_path.parent.name
        out_dir = GENERATED_DIR / target
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / file_for_target(target, manifest)
        out_file.write_text(build_content(target, manifest), encoding='utf-8')
        generated.append(str(out_file.relative_to(ROOT)))
    print('ADAPTER GENERATION: PASS')
    for path in generated:
        print(f'- wrote {path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
