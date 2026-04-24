#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forgeflow_runtime.evolution import dry_run_rule, inspect_evolution_policy


def cmd_inspect(args: argparse.Namespace) -> int:
    report = inspect_evolution_policy(ROOT)
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


def cmd_dry_run(args: argparse.Namespace) -> int:
    try:
        result = dry_run_rule(ROOT, args.rule)
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ForgeFlow evolution policy helper")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="read-only evolution policy summary")
    inspect.add_argument("--json", action="store_true")
    inspect.set_defaults(func=cmd_inspect)
    dry_run = sub.add_parser("dry-run", help="show a project rule command without executing it")
    dry_run.add_argument("--rule", required=True)
    dry_run.add_argument("--json", action="store_true")
    dry_run.set_defaults(func=cmd_dry_run)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
