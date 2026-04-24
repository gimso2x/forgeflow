#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forgeflow_runtime.evolution import adopt_example_rule, audit_events, dry_run_rule, execute_rule, inspect_evolution_policy, list_rules, restore_rule, retire_rule


def _target_root(args: argparse.Namespace) -> Path:
    return Path(args.root).resolve()


def cmd_inspect(args: argparse.Namespace) -> int:
    report = inspect_evolution_policy(_target_root(args))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print("ForgeFlow evolution policy")
    print(f"- policy version: {report['policy_version']}")
    print("- global advisory only: yes")
    print(f"- global activation: {report['global']['activation']}")
    print(f"- global advises: {', '.join(report['global']['advises'])}")
    print(f"- global can block: {str(report['global']['can_block']).lower()}")
    print(f"- project can enforce HARD: {str(report['project']['can_enforce_hard']).lower()}")
    print(f"- project HARD examples valid: {str(report['examples_valid']).lower()}")
    for rule in report["project_hard_examples"]:
        print(f"  - {rule['id']}: {rule['mode']} deterministic={str(rule['deterministic']).lower()}")
    print(f"- retrieval max patterns: {report['retrieval_contract'].get('max_patterns')}")
    print(f"- runtime enforcement: {report['runtime_enforcement'].replace('_', ' ')}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    registry = list_rules(_target_root(args), include_examples=args.include_examples, fallback_root=ROOT)
    if args.json:
        print(json.dumps(registry, ensure_ascii=False, indent=2))
        return 0
    print(f"Project rule dir: {registry['project_rule_dir']}")
    print("Project rules:")
    if registry["project_rules"]:
        for rule in registry["project_rules"]:
            print(f"- {rule['id']} ({rule['mode']}, source={rule['source']})")
    else:
        print("- <none>")
    if args.include_examples:
        print("Example rules:")
        for rule in registry["example_rules"]:
            print(f"- {rule['id']} ({rule['mode']}, source={rule['source']})")
    return 0


def cmd_adopt(args: argparse.Namespace) -> int:
    try:
        result = adopt_example_rule(_target_root(args), args.example, fallback_root=ROOT)
    except (ValueError, FileExistsError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"Adopted evolution rule: {result['rule_id']}")
    print(f"- source: {result['source']}")
    print(f"- destination: {result['destination']}")
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    try:
        result = dry_run_rule(_target_root(args), args.rule, fallback_root=ROOT)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"ForgeFlow evolution dry-run: {result['rule_id']}")
    print(f"- title: {result['title']}")
    print(f"- mode: {result['mode']}")
    print(f"- would execute: {str(result['would_execute']).lower()}")
    print("- command not executed")
    print(f"- command: {result['command']}")
    print(f"- safe to execute later: {str(result['safe_to_execute_later']).lower()}")
    print("- safety checks:")
    for name, passed in result["safety_checks"].items():
        print(f"  - {name}: {str(passed).lower()}")
    return 0


def cmd_execute(args: argparse.Namespace) -> int:
    if not args.i_understand_project_local_hard_rule:
        print("Error: execute requires --i-understand-project-local-hard-rule", file=sys.stderr)
        return 2
    try:
        result = execute_rule(_target_root(args), args.rule)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("passed") else 2

    print(f"ForgeFlow evolution execute: {result['rule_id']}")
    print(f"- executed: {str(result['executed']).lower()}")
    print(f"- exit code: {result['exit_code']} expected={result['expected_exit_code']}")
    print(f"- passed: {str(result['passed']).lower()}")
    if result.get("stdout"):
        print("- stdout:")
        print(result["stdout"].rstrip())
    if result.get("stderr"):
        print("- stderr:")
        print(result["stderr"].rstrip())
    return 0 if result.get("passed") else 2


def cmd_retire(args: argparse.Namespace) -> int:
    try:
        result = retire_rule(_target_root(args), args.rule, reason=args.reason)
    except (ValueError, FileExistsError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"Retired evolution rule: {result['rule_id']}")
    print(f"- source: {result['source_path']}")
    print(f"- destination: {result['destination']}")
    print(f"- reason: {result['reason']}")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    try:
        result = restore_rule(_target_root(args), args.rule, reason=args.reason)
    except (ValueError, FileExistsError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"Restored evolution rule: {result['rule_id']}")
    print(f"- source: {result['source_path']}")
    print(f"- destination: {result['destination']}")
    print(f"- reason: {result['reason']}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    try:
        result = audit_events(_target_root(args), limit=args.limit)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"Evolution audit log: {result['audit_log']}")
    if not result["events"]:
        print("- <none>")
        return 0
    for event in result["events"]:
        status = "passed" if event.get("passed") else "failed"
        executed = event.get("executed")
        executed_text = "" if executed is None else f" executed={str(executed).lower()}"
        print(f"- {event.get('timestamp')} {event.get('event')} {event.get('rule_id')} {status}{executed_text}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ForgeFlow evolution policy helper")
    parser.add_argument("--root", default=str(ROOT), help="project root; defaults to the ForgeFlow checkout")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="read-only evolution policy summary")
    inspect.add_argument("--json", action="store_true")
    inspect.set_defaults(func=cmd_inspect)
    list_cmd = sub.add_parser("list", help="list project-local rules and optionally examples")
    list_cmd.add_argument("--include-examples", action="store_true")
    list_cmd.add_argument("--json", action="store_true")
    list_cmd.set_defaults(func=cmd_list)
    adopt = sub.add_parser("adopt", help="copy a safe example rule into the project-local registry")
    adopt.add_argument("--example", required=True)
    adopt.add_argument("--json", action="store_true")
    adopt.set_defaults(func=cmd_adopt)
    dry_run = sub.add_parser("dry-run", help="show a project rule command without executing it")
    dry_run.add_argument("--rule", required=True)
    dry_run.add_argument("--json", action="store_true")
    dry_run.set_defaults(func=cmd_dry_run)
    execute = sub.add_parser("execute", help="execute a project-local rule after explicit acknowledgement")
    execute.add_argument("--rule", required=True)
    execute.add_argument("--i-understand-project-local-hard-rule", action="store_true")
    execute.add_argument("--json", action="store_true")
    execute.set_defaults(func=cmd_execute)
    retire = sub.add_parser("retire", help="move a project-local rule out of the active registry")
    retire.add_argument("--rule", required=True)
    retire.add_argument("--reason", required=True)
    retire.add_argument("--json", action="store_true")
    retire.set_defaults(func=cmd_retire)
    restore = sub.add_parser("restore", help="move a retired rule back into the active registry")
    restore.add_argument("--rule", required=True)
    restore.add_argument("--reason", required=True)
    restore.add_argument("--json", action="store_true")
    restore.set_defaults(func=cmd_restore)
    audit = sub.add_parser("audit", help="show recent project-local evolution audit events")
    audit.add_argument("--limit", type=int, default=20)
    audit.add_argument("--json", action="store_true")
    audit.set_defaults(func=cmd_audit)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
