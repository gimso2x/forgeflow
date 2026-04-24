#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SECRET_MARKERS = ("api_key", "token=", "password=", "begin private key")
VALID_TYPES = {"review-finding", "decision", "issue", "verification"}
REQUIRED_FIELDS = {"id", "timestamp", "source", "type", "problem", "cause", "rule", "evidence", "tags"}


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def stable_id(entry: dict[str, Any]) -> str:
    parts = [
        entry["type"],
        entry["problem"],
        entry["cause"],
        entry["rule"],
        "|".join(entry["evidence"]),
    ]
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"learn-{digest[:16]}"


def has_secret(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in SECRET_MARKERS)


def validate_entry(entry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(entry)
    if missing:
        errors.append(f"missing fields: {sorted(missing)}")
    if entry.get("type") not in VALID_TYPES:
        errors.append(f"invalid type: {entry.get('type')!r}")
    if not isinstance(entry.get("source"), dict) or not entry.get("source", {}).get("task_id"):
        errors.append("source.task_id is required")
    if not isinstance(entry.get("evidence"), list) or not entry.get("evidence"):
        errors.append("evidence must be a non-empty array")
    else:
        for item in entry["evidence"]:
            if not isinstance(item, str) or not item.strip():
                errors.append("evidence items must be non-empty strings")
            elif has_secret(item):
                errors.append("secret-like evidence is forbidden")
    for field in ["problem", "cause", "rule"]:
        if not isinstance(entry.get(field), str) or len(entry[field].strip()) < 12:
            errors.append(f"{field} is too short")
    if not isinstance(entry.get("tags"), list) or not entry.get("tags"):
        errors.append("tags must be a non-empty array")
    return errors


def read_existing_ids(output: Path) -> set[str]:
    if not output.is_file():
        return set()
    ids: set[str] = set()
    for line in output.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.add(json.loads(line)["id"])
    return ids


def extract_entries(task_dir: Path) -> list[dict[str, Any]]:
    decision_log = load_json_if_exists(task_dir / "decision-log.json") or {}
    review_report = load_json_if_exists(task_dir / "review-report.json") or {}
    eval_record = load_json_if_exists(task_dir / "eval-record.json") or {}
    task_id = review_report.get("task_id") or decision_log.get("task_id") or eval_record.get("task_id") or task_dir.name
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    entries: list[dict[str, Any]] = []

    for finding in review_report.get("findings", []) or []:
        problem = finding.get("problem") or finding.get("summary") or finding.get("message")
        cause = finding.get("cause") or finding.get("rationale") or "Review identified a reusable implementation risk."
        rule = finding.get("recommendation") or finding.get("rule") or finding.get("next_action")
        evidence = finding.get("evidence") or finding.get("file") or finding.get("path")
        if not (problem and rule and evidence):
            continue
        if isinstance(evidence, str):
            evidence_list = [evidence]
        else:
            evidence_list = [str(item) for item in evidence]
        entry = {
            "id": "",
            "timestamp": timestamp,
            "source": {"task_id": task_id, "artifact": "review-report.json"},
            "type": "review-finding",
            "problem": str(problem),
            "cause": str(cause),
            "rule": str(rule),
            "evidence": evidence_list,
            "tags": infer_tags(str(problem), str(rule), evidence_list),
        }
        entry["id"] = stable_id(entry)
        entries.append(entry)

    for decision in decision_log.get("entries", []) or []:
        rationale = decision.get("rationale")
        chosen = decision.get("decision")
        evidence = decision.get("evidence")
        if not (chosen and rationale and evidence):
            continue
        entry = {
            "id": "",
            "timestamp": timestamp,
            "source": {"task_id": task_id, "artifact": "decision-log.json"},
            "type": "decision",
            "problem": f"A decision was needed: {chosen}",
            "cause": str(rationale),
            "rule": f"When this situation recurs, prefer: {chosen}",
            "evidence": [str(evidence)],
            "tags": infer_tags(str(chosen), str(rationale), [str(evidence)]),
        }
        entry["id"] = stable_id(entry)
        # Keep decision learnings only when no stronger review learning exists.
        if not entries:
            entries.append(entry)

    return entries


def infer_tags(problem: str, rule: str, evidence: list[str]) -> list[str]:
    blob = " ".join([problem, rule, *evidence]).lower()
    tags = []
    for keyword, tag in [
        ("json", "json"),
        ("plan", "plan"),
        ("atomic", "atomic-write"),
        ("test", "testing"),
        ("schema", "schema"),
        ("review", "review"),
    ]:
        if keyword in blob and tag not in tags:
            tags.append(tag)
    return tags or ["process"]


def cmd_extract(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir)
    output = Path(args.output)
    entries = extract_entries(task_dir)
    errors: list[str] = []
    for entry in entries:
        entry_errors = validate_entry(entry)
        if entry_errors:
            errors.extend(f"{entry['id'] or '<new>'}: {error}" for error in entry_errors)
    if errors:
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
        return 1

    existing = read_existing_ids(output)
    new_entries = [entry for entry in entries if entry["id"] not in existing]
    skipped = len(entries) - len(new_entries)
    if new_entries:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("a", encoding="utf-8") as handle:
            for entry in new_entries:
                handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"LEARNING EXTRACT: PASS added={len(new_entries)} skipped_duplicates={skipped}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.jsonl)
    if not path.is_file():
        print(f"LEARNING VALIDATION: FAIL\n- missing file: {path}", file=sys.stderr)
        return 1
    errors: list[str] = []
    seen: set[str] = set()
    count = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        count += 1
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid JSON: {exc}")
            continue
        for error in validate_entry(entry):
            errors.append(f"line {line_number}: {error}")
        entry_id = entry.get("id")
        if entry_id in seen:
            errors.append(f"line {line_number}: duplicate id {entry_id}")
        seen.add(entry_id)
    if errors:
        print("LEARNING VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("LEARNING VALIDATION: PASS")
    print(f"- entries: {count}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ForgeFlow learning extractor")
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract")
    extract.add_argument("task_dir")
    extract.add_argument("--output", required=True)
    extract.set_defaults(func=cmd_extract)
    validate = sub.add_parser("validate")
    validate.add_argument("jsonl")
    validate.set_defaults(func=cmd_validate)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
