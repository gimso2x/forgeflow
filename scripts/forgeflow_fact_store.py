#!/usr/bin/env python3
"""forgeflow_fact_store.py — Lightweight fact store for ForgeFlow Memory Bank (L4).

Usage:
  forgeflow_fact_store.py add --content "..." --type decision --domain auth [--project xxx] [--tags a,b] [--confidence high] [--source-task xxx]
  forgeflow_fact_store.py search --query "..." [--domain auth] [--type decision] [--project xxx] [--limit 10]
  forgeflow_fact_store.py list [--domain auth] [--type decision] [--project xxx] [--limit 20]
  forgeflow_fact_store.py show --id fact-xxx
  forgeflow_fact_store.py consolidate [--project xxx]
  forgeflow_fact_store.py stats [--project xxx]

Storage:
  Global: ~/.forgeflow/memory/facts.jsonl
  Project: .forgeflow/memory/facts.jsonl
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path


def forgeflow_home() -> Path:
    return Path(os.environ.get("FORGEFLOW_HOME", os.path.expanduser("~/.forgeflow")))


def facts_path(project: str | None = None) -> Path:
    if project:
        p = Path(project) / ".forgeflow" / "memory" / "facts.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    h = forgeflow_home() / "memory" / "facts.jsonl"
    h.parent.mkdir(parents=True, exist_ok=True)
    return h


def generate_id(content: str, timestamp: str) -> str:
    raw = f"{content}:{timestamp}"
    return f"fact-{hashlib.sha256(raw.encode()).hexdigest()[:8]}"


VALID_TYPES = {"decision", "constraint", "preference", "pattern", "bug_fix", "discovery"}
VALID_DOMAINS = {"auth", "api", "ui", "infra", "testing", "project", "architecture", "tooling", "general"}
VALID_CONFIDENCE = {"high", "medium", "low"}


def load_facts(path: Path) -> list[dict]:
    if not path.exists():
        return []
    facts = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                facts.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return facts


def append_fact(path: Path, fact: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(fact, ensure_ascii=False) + "\n")


def keyword_match(query: str, text: str) -> bool:
    q_lower = query.lower()
    t_lower = text.lower()
    # Exact substring
    if q_lower in t_lower:
        return True
    # All query words present
    words = re.findall(r"\w+", q_lower)
    if words and all(w in t_lower for w in words):
        return True
    return False


def cmd_add(args: argparse.Namespace) -> int:
    path = facts_path(args.project)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    fact_type = args.type or "discovery"
    if fact_type not in VALID_TYPES:
        print(f"Invalid type: {fact_type}. Valid: {', '.join(sorted(VALID_TYPES))}", file=sys.stderr)
        return 1

    domain = args.domain or "general"
    confidence = args.confidence or "medium"

    content = args.content
    if not content:
        print("--content is required", file=sys.stderr)
        return 1

    fact_id = generate_id(content, ts)
    tags = []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    fact = {
        "id": fact_id,
        "type": fact_type,
        "domain": domain,
        "content": content,
        "source": {
            "task_id": args.source_task or "",
            "timestamp": ts,
        },
        "project": args.project or "global",
        "confidence": confidence,
        "supersedes": [],
        "tags": tags,
    }

    append_fact(path, fact)
    print(fact_id)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    path = facts_path(args.project)
    facts = load_facts(path)
    query = args.query or ""

    results = []
    for f in facts:
        if args.type and f.get("type") != args.type:
            continue
        if args.domain and f.get("domain") != args.domain:
            continue
        if query and not keyword_match(query, f.get("content", "")):
            continue
        results.append(f)

    limit = args.limit or 10
    results = results[:limit]

    if not results:
        print("No matching facts.")
        return 0

    for f in results:
        src = f.get("source", {})
        task = src.get("task_id", "")
        ts = src.get("timestamp", "")
        print(f"  [{f['id']}] ({f.get('type','?')}/{f.get('domain','?')}) {f['content']}")
        if task:
            print(f"    source: task={task} at={ts}")
    print(f"\n{len(results)} fact(s) found.")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    path = facts_path(args.project)
    facts = load_facts(path)

    filtered = []
    for f in facts:
        if args.type and f.get("type") != args.type:
            continue
        if args.domain and f.get("domain") != args.domain:
            continue
        filtered.append(f)

    limit = args.limit or 20
    filtered = filtered[:limit]

    if not filtered:
        print("No facts stored.")
        return 0

    for f in filtered:
        conf = f.get("confidence", "?")
        print(f"  [{f['id']}] {f.get('type','?'):10} {f.get('domain','?'):12} [{conf:6}] {f['content'][:80]}")
    print(f"\n{len(filtered)} fact(s).")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    path = facts_path(args.project)
    facts = load_facts(path)

    for f in facts:
        if f["id"] == args.id:
            print(json.dumps(f, indent=2, ensure_ascii=False))
            return 0

    print(f"Fact not found: {args.id}", file=sys.stderr)
    return 1


def cmd_consolidate(args: argparse.Namespace) -> int:
    path = facts_path(args.project)
    facts = load_facts(path)

    if not facts:
        print("No facts to consolidate.")
        return 0

    # Find duplicates (same content)
    seen_content: dict[str, str] = {}
    duplicates = 0
    for f in facts:
        content_key = f["content"].strip().lower()
        if content_key in seen_content:
            f.setdefault("supersedes", []).append(seen_content[content_key])
            duplicates += 1
        else:
            seen_content[content_key] = f["id"]

    if duplicates > 0:
        # Rewrite facts with dedup info
        backup = path.with_suffix(".jsonl.bak")
        path.rename(backup)
        for f in facts:
            append_fact(path, f)
        print(f"Consolidated: {duplicates} duplicate(s) marked. Backup: {backup}")
    else:
        print("No duplicates found.")

    # Stats
    type_counts: dict[str, int] = {}
    domain_counts: dict[str, int] = {}
    for f in facts:
        t = f.get("type", "unknown")
        d = f.get("domain", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
        domain_counts[d] = domain_counts.get(d, 0) + 1

    print(f"\nTotal facts: {len(facts)}")
    print(f"By type: {dict(sorted(type_counts.items()))}")
    print(f"By domain: {dict(sorted(domain_counts.items()))}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    path = facts_path(args.project)
    facts = load_facts(path)

    if not facts:
        print("No facts stored.")
        return 0

    type_counts: dict[str, int] = {}
    domain_counts: dict[str, int] = {}
    confidence_counts: dict[str, int] = {}
    for f in facts:
        t = f.get("type", "unknown")
        d = f.get("domain", "unknown")
        c = f.get("confidence", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
        domain_counts[d] = domain_counts.get(d, 0) + 1
        confidence_counts[c] = confidence_counts.get(c, 0) + 1

    print(f"Total facts: {len(facts)}")
    print(f"Storage: {path}")
    print(f"\nBy type:")
    for k, v in sorted(type_counts.items()):
        print(f"  {k}: {v}")
    print(f"\nBy domain:")
    for k, v in sorted(domain_counts.items()):
        print(f"  {k}: {v}")
    print(f"\nBy confidence:")
    for k, v in sorted(confidence_counts.items()):
        print(f"  {k}: {v}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ForgeFlow Fact Store (Memory Bank L4)")
    sub = parser.add_subparsers(dest="command")

    add_p = sub.add_parser("add")
    add_p.add_argument("--content", required=True)
    add_p.add_argument("--type", default="discovery", choices=sorted(VALID_TYPES))
    add_p.add_argument("--domain", default="general", choices=sorted(VALID_DOMAINS))
    add_p.add_argument("--project")
    add_p.add_argument("--confidence", default="medium", choices=sorted(VALID_CONFIDENCE))
    add_p.add_argument("--tags")
    add_p.add_argument("--source-task")

    search_p = sub.add_parser("search")
    search_p.add_argument("--query", required=True)
    search_p.add_argument("--type", choices=sorted(VALID_TYPES))
    search_p.add_argument("--domain", choices=sorted(VALID_DOMAINS))
    search_p.add_argument("--project")
    search_p.add_argument("--limit", type=int, default=10)

    list_p = sub.add_parser("list")
    list_p.add_argument("--type", choices=sorted(VALID_TYPES))
    list_p.add_argument("--domain", choices=sorted(VALID_DOMAINS))
    list_p.add_argument("--project")
    list_p.add_argument("--limit", type=int, default=20)

    show_p = sub.add_parser("show")
    show_p.add_argument("--id", required=True)
    show_p.add_argument("--project")

    cons_p = sub.add_parser("consolidate")
    cons_p.add_argument("--project")

    stats_p = sub.add_parser("stats")
    stats_p.add_argument("--project")

    args = parser.parse_args()

    if args.command == "add":
        return cmd_add(args)
    elif args.command == "search":
        return cmd_search(args)
    elif args.command == "list":
        return cmd_list(args)
    elif args.command == "show":
        return cmd_show(args)
    elif args.command == "consolidate":
        return cmd_consolidate(args)
    elif args.command == "stats":
        return cmd_stats(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
