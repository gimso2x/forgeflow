from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

AUDIT_LOG_PATH = Path(".forgeflow") / "evolution" / "audit-log.jsonl"


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def append_audit_event(root: Path, event: dict[str, Any]) -> None:
    audit_path = root / AUDIT_LOG_PATH
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "timestamp": utc_timestamp(), **event}
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def read_audit_events(root: Path) -> list[dict[str, Any]]:
    audit_path = root / AUDIT_LOG_PATH
    if not audit_path.is_file():
        return []
    lines = [line for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def audit_events(root: Path, *, limit: int = 20) -> dict[str, Any]:
    root = root.resolve()
    audit_path = root / AUDIT_LOG_PATH
    if limit < 1:
        raise ValueError("audit limit must be >= 1")
    events = read_audit_events(root)[-limit:]
    return {"audit_log": str(audit_path), "events": events}


def effectiveness_review(root: Path, rule_id: str, *, since_days: int = 30) -> dict[str, Any]:
    """Read-only audit-backed effectiveness review for one evolution rule."""

    root = root.resolve()
    if since_days < 1:
        raise ValueError("since_days must be >= 1")
    cutoff = datetime.now(UTC).timestamp() - since_days * 86400
    matching_events = []
    for event in read_audit_events(root):
        if event.get("rule_id") != rule_id or event.get("event") != "execute":
            continue
        timestamp = event.get("timestamp")
        if isinstance(timestamp, str):
            try:
                event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
            except ValueError:
                event_time = cutoff
            if event_time < cutoff:
                continue
        matching_events.append(event)
    executions = len(matching_events)
    failures = sum(1 for event in matching_events if event.get("passed") is False)
    blocked = sum(1 for event in matching_events if event.get("executed") is False)
    passes = sum(1 for event in matching_events if event.get("passed") is True)
    if failures >= 2:
        recommendation = "promotion_candidate"
    elif failures == 1:
        recommendation = "watch_candidate"
    elif executions > 0:
        recommendation = "effective_candidate"
    else:
        recommendation = "insufficient_data"
    return {
        "rule_id": rule_id,
        "read_only": True,
        "window_days": since_days,
        "metrics": {
            "executions": executions,
            "passes": passes,
            "failures": failures,
            "blocked_executions": blocked,
        },
        "recommendation": recommendation,
        "would_promote": False,
        "would_mutate": False,
        "audit_backed_only": True,
    }
