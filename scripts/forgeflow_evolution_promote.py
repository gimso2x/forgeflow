#!/usr/bin/env python3
"""forgeflow_evolution_promote.py — Track soft rule failures and auto-promote to hard rules.

Usage:
  forgeflow_evolution_promote.py record-fail --rule <rule-id> [--project <path>]
  forgeflow_evolution_promote.py check-promote --rule <rule-id> [--project <path>] [--threshold N]
  forgeflow_evolution_promote.py list-failures [--project <path>]
  forgeflow_evolution_promote.py promote --rule <rule-id> [--project <path>]

Exit codes:
  0 = success
  1 = error
  2 = BLOCK (promotion threshold reached, rule promoted)

Behavior:
  - record-fail: Increment failure count for a soft rule in fail-counts.json
  - check-promote: Check if threshold reached, auto-promote if so
  - list-failures: Show current failure counts
  - promote: Force-promote a soft rule to hard regardless of count
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path


def forgeflow_home() -> Path:
    return Path(os.environ.get("FORGEFLOW_HOME", os.path.expanduser("~/.forgeflow")))


def fail_counts_path(project: str | None = None) -> Path:
    if project:
        p = Path(project) / ".forgeflow" / "evolution" / "fail-counts.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    h = forgeflow_home() / "evolution" / "fail-counts.json"
    h.parent.mkdir(parents=True, exist_ok=True)
    return h


def load_counts(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_counts(path: Path, counts: dict) -> None:
    path.write_text(json.dumps(counts, indent=2, ensure_ascii=False) + "\n")


def audit_log_path(project: str | None = None) -> Path:
    if project:
        return Path(project) / ".forgeflow" / "evolution" / "audit-log.jsonl"
    return forgeflow_home() / "evolution" / "audit-log.jsonl"


def append_audit(project: str | None, event: dict) -> None:
    path = audit_log_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def find_advisory_rule(rule_id: str, project: str | None = None) -> Path | None:
    """Find the advisory (markdown) rule file."""
    dirs = [forgeflow_home() / "evolution" / "active"]
    if project:
        dirs.append(Path(project) / ".forgeflow" / "evolution" / "active")
    for d in dirs:
        if d.exists():
            for f in d.iterdir():
                if f.is_file() and f.suffix == ".md" and rule_id in f.stem:
                    return f
    return None


def generate_hard_rule(rule_id: str, advisory_path: Path) -> dict:
    """Generate a hard rule JSON from an advisory markdown rule."""
    content = advisory_path.read_text()
    summary = ""
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("<!--"):
            summary = line
            break

    return {
        "id": rule_id,
        "title": summary[:80] if summary else rule_id,
        "scope": "project",
        "lifecycle": "adopted_hard",
        "source_signal": "auto_promote",
        "summary": summary if summary else f"Auto-promoted from advisory rule: {rule_id}",
        "check": {
            "kind": "command",
            "command_id": rule_id,
            "command": f"bash scripts/forgeflow_hook_check.sh --rule {rule_id}",
            "expected_exit_code": 0,
        },
        "enforcement": {
            "mode": "hard_exit_2",
            "deterministic": True,
            "message": f"Hard rule enforced: {summary[:60] if summary else rule_id}",
        },
        "hard_gate_evidence": {
            "auto_promoted": True,
            "soft_soak_period": "Exceeded failure threshold during advisory phase",
            "audit_trail": f"Auto-promoted by forgeflow_evolution_promote.py at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        },
    }


def cmd_record_fail(args: argparse.Namespace) -> int:
    path = fail_counts_path(args.project)
    counts = load_counts(path)
    rule_id = args.rule

    if rule_id not in counts:
        counts[rule_id] = {"failures": 0, "last_fail": None}

    counts[rule_id]["failures"] += 1
    counts[rule_id]["last_fail"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    save_counts(path, counts)

    append_audit(args.project, {
        "event": "soft_fail",
        "rule_id": rule_id,
        "total_failures": counts[rule_id]["failures"],
        "timestamp": counts[rule_id]["last_fail"],
    })

    print(f"{rule_id}: failure count = {counts[rule_id]['failures']}")
    return 0


def cmd_check_promote(args: argparse.Namespace) -> int:
    path = fail_counts_path(args.project)
    counts = load_counts(path)
    rule_id = args.rule
    threshold = args.threshold or 2

    if rule_id not in counts:
        print(f"{rule_id}: no failures recorded")
        return 0

    failures = counts[rule_id]["failures"]
    if failures < threshold:
        print(f"{rule_id}: {failures}/{threshold} failures — not yet at threshold")
        return 0

    print(f"{rule_id}: {failures}/{threshold} failures — threshold reached, promoting...")
    return cmd_promote(args)


def cmd_promote(args: argparse.Namespace) -> int:
    rule_id = args.rule

    advisory = find_advisory_rule(rule_id, args.project)
    if advisory is None:
        print(f"Advisory rule not found: {rule_id}", file=sys.stderr)
        return 1

    hard_rule = generate_hard_rule(rule_id, advisory)

    rules_dir = forgeflow_home() / "evolution" / "rules"
    if args.project:
        rules_dir = Path(args.project) / ".forgeflow" / "evolution" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    rule_file = rules_dir / f"{rule_id}-rule.json"
    rule_file.write_text(json.dumps(hard_rule, indent=2, ensure_ascii=False) + "\n")

    append_audit(args.project, {
        "event": "auto_promote",
        "rule_id": rule_id,
        "destination": str(rule_file),
        "source": str(advisory),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "passed": True,
    })

    print(f"Promoted {rule_id}: {advisory} -> {rule_file}")
    return 2


def cmd_list_failures(args: argparse.Namespace) -> int:
    path = fail_counts_path(args.project)
    counts = load_counts(path)
    if not counts:
        print("No failures recorded.")
        return 0

    for rule_id, data in counts.items():
        failures = data.get("failures", 0)
        last = data.get("last_fail", "unknown")
        print(f"  {rule_id}: {failures} failures (last: {last})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ForgeFlow soft-to-hard rule promotion")
    sub = parser.add_subparsers(dest="command")

    rec = sub.add_parser("record-fail")
    rec.add_argument("--rule", required=True)
    rec.add_argument("--project")

    chk = sub.add_parser("check-promote")
    chk.add_argument("--rule", required=True)
    chk.add_argument("--project")
    chk.add_argument("--threshold", type=int, default=2)

    pro = sub.add_parser("promote")
    pro.add_argument("--rule", required=True)
    pro.add_argument("--project")

    lst = sub.add_parser("list-failures")
    lst.add_argument("--project")

    args = parser.parse_args()

    if args.command == "record-fail":
        return cmd_record_fail(args)
    elif args.command == "check-promote":
        return cmd_check_promote(args)
    elif args.command == "promote":
        return cmd_promote(args)
    elif args.command == "list-failures":
        return cmd_list_failures(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
