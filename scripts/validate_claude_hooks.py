#!/usr/bin/env python3
from __future__ import annotations

import json
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = ROOT / 'adapters/targets/claude/hooks'
MANIFEST = HOOKS_DIR / 'hooks.json'
PREFIX = '${CLAUDE_PLUGIN_ROOT}/hooks/'


def iter_commands(manifest: dict):
    for event_name, groups in manifest.get('hooks', {}).items():
        if not isinstance(groups, list):
            yield event_name, None, f'{event_name}: hook groups must be a list'
            continue
        for group_index, group in enumerate(groups):
            for hook_index, hook in enumerate(group.get('hooks', [])):
                command = hook.get('command')
                yield event_name, command, f'{event_name}[{group_index}].hooks[{hook_index}]'


def main() -> int:
    errors: list[str] = []
    if not MANIFEST.is_file():
        errors.append(f'missing manifest: {MANIFEST.relative_to(ROOT)}')
    else:
        try:
            manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            errors.append(f'invalid JSON: {exc}')
            manifest = {}
        for _event, command, label in iter_commands(manifest):
            if command is None:
                errors.append(label)
                continue
            if not isinstance(command, str) or not command.startswith(PREFIX):
                errors.append(f'{label}: command must start with {PREFIX}')
                continue
            script_name = command[len(PREFIX):]
            if '/' in script_name or not script_name.endswith('.py'):
                errors.append(f'{label}: command must reference a hook .py script by filename')
                continue
            script_path = HOOKS_DIR / script_name
            if not script_path.is_file():
                errors.append(f'{label}: missing script {script_name}')
                continue
            try:
                py_compile.compile(str(script_path), doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append(f'{label}: syntax error in {script_name}: {exc.msg}')

    if errors:
        print('CLAUDE HOOK VALIDATION: FAIL')
        for error in errors:
            print(f'- {error}')
        return 1
    print('CLAUDE HOOK VALIDATION: PASS')
    print(f'- manifest: {MANIFEST.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
