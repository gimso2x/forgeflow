#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forgeflow_runtime.evolution import adopt_example_rule, audit_events, doctor_evolution_state, dry_run_rule, effectiveness_review, execute_rule, inspect_evolution_policy, list_rules, promotion_plan, proposal_review, restore_rule, retire_rule, write_promotion_plan


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


def cmd_doctor(args: argparse.Namespace) -> int:
    report = doctor_evolution_state(_target_root(args))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1
    print(f"Evolution doctor: {'ok' if report['ok'] else 'issues found'}")
    print(f"- root: {report['root']}")
    print(f"- active rules: {report['summary']['active_rules']}")
    print(f"- retired rules: {report['summary']['retired_rules']}")
    print(f"- audit events: {report['summary']['audit_events']}")
    print(f"- unsafe active rules: {report['summary']['unsafe_active_rules']}")
    print(f"- restore candidates: {report['summary']['restore_candidates']}")
    print("- closed-loop surfaces:")
    surfaces = report["closed_loop_surfaces"]
    print(f"  - reactive fix learning: {surfaces['reactive_fix_learning'].replace('_', ' ')}")
    print(f"  - proactive feedback learning: {surfaces['proactive_feedback_learning'].replace('_', ' ')}")
    meta_text = surfaces['meta_effectiveness_review'].replace('audit_backed', 'audit-backed').replace('_', ' ')
    print(f"  - meta effectiveness review: {meta_text}")
    if report["issues"]:
        print("- issues:")
        for issue in report["issues"]:
            rule_text = f" rule={issue['rule_id']}" if issue.get("rule_id") else ""
            line_text = f" line={issue['line']}" if issue.get("line") else ""
            print(f"  - {issue['severity']} {issue['code']}{rule_text}{line_text}")
    else:
        print("- issues: <none>")
    return 0 if report["ok"] else 1


def cmd_effectiveness(args: argparse.Namespace) -> int:
    try:
        result = effectiveness_review(_target_root(args), args.rule, since_days=args.since_days)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"Evolution effectiveness: {result['rule_id']}")
    print(f"- read-only: {str(result['read_only']).lower()}")
    print(f"- window days: {result['window_days']}")
    print(f"- executions: {result['metrics']['executions']}")
    print(f"- passes: {result['metrics']['passes']}")
    print(f"- failures: {result['metrics']['failures']}")
    print(f"- recommendation: {result['recommendation']}")
    print(f"- would promote: {str(result['would_promote']).lower()}")
    print(f"- would mutate: {str(result['would_mutate']).lower()}")
    return 0


def cmd_promotion_plan(args: argparse.Namespace) -> int:
    try:
        if args.write:
            result = write_promotion_plan(_target_root(args), args.rule, since_days=args.since_days)
        else:
            result = promotion_plan(_target_root(args), args.rule, since_days=args.since_days)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"Evolution promotion plan: {result['rule_id']}")
    print(f"- read-only: {str(result['read_only']).lower()}")
    print(f"- would mutate: {str(result['would_mutate']).lower()}")
    print(f"- recommendation: {result['recommendation']}")
    print(f"- failures: {result['evidence_summary']['failures']}")
    print("- required approvals:")
    if result["required_human_approvals"]:
        for approval in result["required_human_approvals"]:
            print(f"  - {approval}")
    else:
        print("  - <none>")
    print("- risk flags:")
    if result["risk_flags"]:
        for flag in result["risk_flags"]:
            print(f"  - {flag}")
    else:
        print("  - <none>")
    if result.get("suggested_next_command"):
        print(f"- suggested next command: {result['suggested_next_command']}")
    if result.get("proposal_written"):
        print(f"- proposal written: {result['proposal_path']}")
    return 0


def cmd_proposal_review(args: argparse.Namespace) -> int:
    try:
        result = proposal_review(_target_root(args), Path(args.proposal))
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1
    print(f"Evolution proposal review: {result['proposal_path']}")
    print(f"- rule: {result['rule_id']}")
    print(f"- read-only: {str(result['read_only']).lower()}")
    print(f"- would mutate: {str(result['would_mutate']).lower()}")
    print(f"- active rule exists: {str(result['active_rule_exists']).lower()}")
    print(f"- valid: {str(result['valid']).lower()}")
    if result["issues"]:
        print("- issues:")
        for issue in result["issues"]:
            print(f"  - {issue['severity']} {issue['code']}")
    else:
        print("- issues: <none>")
    return 0 if result["valid"] else 1


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
    doctor = sub.add_parser("doctor", help="read-only project-local evolution health check")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=cmd_doctor)
    effectiveness = sub.add_parser("effectiveness", help="read-only audit-backed rule effectiveness review")
    effectiveness.add_argument("--rule", required=True)
    effectiveness.add_argument("--since-days", type=int, default=30)
    effectiveness.add_argument("--json", action="store_true")
    effectiveness.set_defaults(func=cmd_effectiveness)
    promotion = sub.add_parser("promotion-plan", help="read-only promotion planning from effectiveness evidence")
    promotion.add_argument("--rule", required=True)
    promotion.add_argument("--since-days", type=int, default=30)
    promotion.add_argument("--write", action="store_true")
    promotion.add_argument("--json", action="store_true")
    promotion.set_defaults(func=cmd_promotion_plan)
    proposal_review_cmd = sub.add_parser("proposal-review", help="read-only validation of a persisted promotion proposal")
    proposal_review_cmd.add_argument("--proposal", required=True)
    proposal_review_cmd.add_argument("--json", action="store_true")
    proposal_review_cmd.set_defaults(func=cmd_proposal_review)
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
