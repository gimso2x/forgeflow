from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OBSERVATION_FILE = "evolution-observations.jsonl"
OBSERVATION_SCHEMA_VERSION = "0.1"
_MAX_CODE_LENGTH = 80


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _task_dir(root: Path, task_id: str) -> Path:
    return root / ".forgeflow" / "tasks" / task_id


def _observation_path(task_dir: Path) -> Path:
    return task_dir / OBSERVATION_FILE


def _sanitize_code(value: Any) -> str:
    text = str(value or "unknown_blocker").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    if not text:
        text = "unknown_blocker"
    return text[:_MAX_CODE_LENGTH].strip("_") or "unknown_blocker"


def _blocker_codes(review_payload: dict[str, Any], reason: str) -> list[str]:
    raw_blockers = review_payload.get("open_blockers") or []
    if isinstance(raw_blockers, str):
        raw_blockers = [raw_blockers]
    if raw_blockers:
        return [_sanitize_code(blocker) for blocker in raw_blockers]
    verdict = review_payload.get("verdict")
    review_type = review_payload.get("review_type")
    if verdict and verdict != "approved":
        return [_sanitize_code(f"{review_type or 'review'}_{verdict}")]
    return [_sanitize_code(reason)]


def append_review_blocker_observation(
    task_dir: Path,
    *,
    task_id: str,
    stage: str,
    gate: str | None,
    review_payload: dict[str, Any],
    artifact_refs: list[str],
    reason: str,
) -> dict[str, Any]:
    """Append a task-local, observation-only evolution signal.

    This intentionally stores only machine-oriented metadata. It does not persist
    raw findings, prompts, user frustration text, credentials, or rule bodies.
    """

    task_dir.mkdir(parents=True, exist_ok=True)
    event = {
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "timestamp": _utc_timestamp(),
        "event": "review_blocker_observed",
        "task_id": task_id,
        "stage": stage,
        "gate": gate,
        "review_type": review_payload.get("review_type"),
        "verdict": review_payload.get("verdict"),
        "blocker_codes": _blocker_codes(review_payload, reason),
        "artifact_refs": list(artifact_refs),
        "reason_code": _sanitize_code(reason),
        "would_generate_rule": False,
        "would_enforce": False,
    }
    observation_path = _observation_path(task_dir)
    with observation_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def read_observations(root: Path, task_id: str) -> dict[str, Any]:
    task_dir = _task_dir(root, task_id)
    observation_path = _observation_path(task_dir)
    observations: list[dict[str, Any]] = []
    if observation_path.exists():
        for line in observation_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                observations.append(json.loads(line))
    return {
        "task_id": task_id,
        "observation_path": str(observation_path),
        "read_only": True,
        "would_mutate": False,
        "observations": observations,
    }


def suggest_from_task(root: Path, task_id: str) -> dict[str, Any]:
    observations_report = read_observations(root, task_id)
    observations = observations_report["observations"]
    counter: Counter[str] = Counter()
    for observation in observations:
        for code in observation.get("blocker_codes", []):
            counter[code] += 1

    suggestions = []
    for code, count in counter.most_common():
        suggestions.append({
            "suggested_rule_id": f"observed-{code.replace('_', '-')}",
            "pattern_summary": f"Observed review blocker pattern: {code}",
            "supporting_observations": count,
            "proposed_check_kind": "review_blocker_pattern",
            "confidence": "low" if count < 2 else "medium",
            "would_mutate": False,
            "would_generate_rule": False,
            "would_enforce": False,
        })

    return {
        "task_id": task_id,
        "read_only": True,
        "would_mutate": False,
        "would_generate_rule": False,
        "would_enforce": False,
        "observation_count": len(observations),
        "suggestions": suggestions,
        "next_step": "Use a separate explicit proposal command only after human review; this command never writes rules.",
    }
