from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from forgeflow_runtime.errors import RuntimeViolation


SCHEMA_BY_ARTIFACT = {
    "brief": "brief",
    "plan": "plan",
    "plan-ledger": "plan-ledger",
    "decision-log": "decision-log",
    "run-state": "run-state",
    "review-report": "review-report",
    "review-report-spec": "review-report",
    "review-report-quality": "review-report",
    "eval-record": "eval-record",
    "checkpoint": "checkpoint",
    "session-state": "session-state",
}

REPO_ROOT = Path(__file__).resolve().parents[1]


def artifact_path(task_dir: Path, artifact_name: str) -> Path:
    return task_dir / f"{artifact_name}.json"


def artifact_variants(artifact_name: str) -> list[str]:
    if artifact_name == "review-report":
        return ["review-report", "review-report-spec", "review-report-quality"]
    return [artifact_name]


def has_artifact(task_dir: Path, artifact_name: str) -> bool:
    return any(artifact_path(task_dir, variant).exists() for variant in artifact_variants(artifact_name))


def missing_artifacts(task_dir: Path, artifact_names: list[str]) -> list[str]:
    return [name for name in artifact_names if not has_artifact(task_dir, name)]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def schema_validator(schema_name: str) -> Draft202012Validator:
    schema_path = REPO_ROOT / "schemas" / f"{schema_name}.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def schema_name_for_artifact(artifact_name: str) -> str | None:
    return SCHEMA_BY_ARTIFACT.get(artifact_name)


def validate_artifact_payload(*, artifact_name: str, payload: dict[str, Any], source_name: str) -> None:
    schema_name = schema_name_for_artifact(artifact_name)
    if schema_name is None:
        return
    errors = sorted(schema_validator(schema_name).iter_errors(payload), key=lambda err: list(err.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, err.path)) or '<root>'}: {err.message}" for err in errors[:3]
        )
        raise RuntimeViolation(f"{source_name} failed schema validation: {details}")


def coerce_legacy_artifact_payload(artifact_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if artifact_name != "decision-log":
        return payload

    entries = payload.get("entries")
    if not isinstance(entries, list):
        return payload

    migrated_entries: list[dict[str, Any]] = []
    migrated = False
    base = datetime(1970, 1, 1, tzinfo=UTC)
    for entry in entries:
        if not isinstance(entry, dict):
            return payload
        timestamp = entry.get("timestamp")
        if isinstance(timestamp, str) and timestamp.startswith("seq-"):
            suffix = timestamp[4:]
            if not suffix.isdigit():
                return payload
            sequence = int(suffix)
            normalized = (base + timedelta(seconds=sequence)).strftime("%Y-%m-%dT%H:%M:%SZ")
            migrated_entries.append({**entry, "timestamp": normalized})
            migrated = True
        else:
            migrated_entries.append(entry)

    if not migrated:
        return payload
    return {**payload, "entries": migrated_entries}


def assert_task_id_matches(path: Path, payload: dict[str, Any], expected_task_id: str | None) -> None:
    if expected_task_id is None:
        return
    artifact_task_id = payload.get("task_id")
    if artifact_task_id != expected_task_id:
        raise RuntimeViolation(
            f"{path.name} task_id {artifact_task_id} does not match canonical task_id {expected_task_id}"
        )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_validated_artifact(
    task_dir: Path,
    artifact_name: str,
    *,
    expected_task_id: str | None = None,
) -> dict[str, Any]:
    path = artifact_path(task_dir, artifact_name)
    payload = load_json(path)
    try:
        validate_artifact_payload(artifact_name=artifact_name, payload=payload, source_name=path.name)
        assert_task_id_matches(path, payload, expected_task_id)
        return payload
    except RuntimeViolation:
        coerced_payload = coerce_legacy_artifact_payload(artifact_name, payload)
        if coerced_payload == payload:
            raise
        validate_artifact_payload(artifact_name=artifact_name, payload=coerced_payload, source_name=path.name)
        assert_task_id_matches(path, coerced_payload, expected_task_id)
        write_json(path, coerced_payload)
        return coerced_payload


def write_validated_artifact(task_dir: Path, artifact_name: str, payload: dict[str, Any]) -> None:
    validate_artifact_payload(
        artifact_name=artifact_name,
        payload=payload,
        source_name=artifact_path(task_dir, artifact_name).name,
    )
    write_json(artifact_path(task_dir, artifact_name), payload)

