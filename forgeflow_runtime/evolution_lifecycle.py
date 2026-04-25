from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from forgeflow_runtime.evolution_audit import append_audit_event
from forgeflow_runtime.evolution_rules import (
    PROJECT_RULE_DIR,
    RETIRED_RULE_DIR,
    load_example_rule_by_id,
    load_project_rules,
    load_rule_by_id,
    safety_checks,
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rule_filename(rule: dict[str, Any], source_path: Path) -> str:
    rule_id = rule.get("id")
    if isinstance(rule_id, str) and rule_id:
        return f"{rule_id}-rule.json"
    return source_path.name


def load_retired_rule_by_id(root: Path, rule_id: str) -> tuple[dict[str, Any], Path]:
    retired_dir = root / RETIRED_RULE_DIR
    if retired_dir.is_dir():
        for path in sorted(retired_dir.glob("*.json")):
            rule = _load_json(path)
            if rule.get("id") == rule_id:
                return rule, path
    known = []
    if retired_dir.is_dir():
        known = [(_load_json(path).get("id") or path.name) for path in sorted(retired_dir.glob("*.json"))]
    known_text = ", ".join(known) or "<none>"
    raise ValueError(f"evolution rule {rule_id!r} not found in retired registry {retired_dir}; known retired rules: {known_text}")


def move_with_audit_rollback(source_path: Path, destination: Path, audit_callback: Callable[[], None]) -> None:
    source_path.replace(destination)
    try:
        audit_callback()
    except Exception:
        if destination.exists() and not source_path.exists():
            destination.replace(source_path)
        raise


def retire_rule(
    root: Path,
    rule_id: str,
    *,
    reason: str,
    audit_append: Callable[[Path, dict[str, Any]], None] = append_audit_event,
) -> dict[str, Any]:
    root = root.resolve()
    if not reason.strip():
        raise ValueError("retire reason must be non-empty")
    rule, source, source_path = load_rule_by_id(root, rule_id, allow_examples=False)
    destination_dir = root / RETIRED_RULE_DIR
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source_path.name
    if destination.exists():
        raise FileExistsError(f"retired evolution rule already exists: {destination}")
    result = {
        "retired": True,
        "rule_id": rule.get("id"),
        "source": source,
        "source_path": str(source_path),
        "destination": str(destination),
        "reason": reason,
    }

    def audit() -> None:
        audit_append(
            root,
            {
                "event": "retire",
                "rule_id": result["rule_id"],
                "source": source,
                "source_path": result["source_path"],
                "destination": result["destination"],
                "reason": reason,
                "passed": True,
            },
        )

    move_with_audit_rollback(source_path, destination, audit)
    return result


def restore_rule(
    root: Path,
    rule_id: str,
    *,
    reason: str,
    audit_append: Callable[[Path, dict[str, Any]], None] = append_audit_event,
) -> dict[str, Any]:
    root = root.resolve()
    if not reason.strip():
        raise ValueError("restore reason must be non-empty")
    rule, source_path = load_retired_rule_by_id(root, rule_id)
    destination_dir = root / PROJECT_RULE_DIR
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source_path.name
    if destination.exists():
        raise FileExistsError(f"project-local evolution rule already exists: {destination}")
    checks = safety_checks(rule)
    if not all(checks.values()):
        failed = ", ".join(name for name, passed in checks.items() if not passed)
        raise ValueError(f"retired rule {rule_id!r} failed safety checks: {failed}")
    result = {
        "restored": True,
        "rule_id": rule.get("id"),
        "source_path": str(source_path),
        "destination": str(destination),
        "reason": reason,
        "safety_checks": checks,
    }

    def audit() -> None:
        audit_append(
            root,
            {
                "event": "restore",
                "rule_id": result["rule_id"],
                "source_path": result["source_path"],
                "destination": result["destination"],
                "reason": reason,
                "passed": True,
                "safety_checks": checks,
            },
        )

    move_with_audit_rollback(source_path, destination, audit)
    return result


def adopt_example_rule(root: Path, rule_id: str, *, fallback_root: Path | None = None) -> dict[str, Any]:
    """Copy a safe example rule into the project-local registry without overwriting."""

    root = root.resolve()
    examples_root = (fallback_root or root).resolve()
    rule, source_path = load_example_rule_by_id(examples_root, rule_id)
    checks = safety_checks(rule)
    if not all(checks.values()):
        failed = ", ".join(name for name, passed in checks.items() if not passed)
        raise ValueError(f"example rule {rule_id!r} failed safety checks: {failed}")

    destination_dir = root / PROJECT_RULE_DIR
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / rule_filename(rule, source_path)
    if destination.exists():
        raise FileExistsError(f"project-local evolution rule already exists: {destination}")
    destination.write_text(json.dumps(rule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {
        "adopted": True,
        "rule_id": rule.get("id"),
        "source": str(source_path),
        "destination": str(destination),
        "safety_checks": checks,
    }
    append_audit_event(
        root,
        {
            "event": "adopt",
            "rule_id": result["rule_id"],
            "source": result["source"],
            "destination": result["destination"],
            "passed": True,
            "safety_checks": checks,
        },
    )
    return result


def load_retired_rules(root: Path) -> list[tuple[dict[str, Any], Path]]:
    retired_dir = root / RETIRED_RULE_DIR
    if not retired_dir.is_dir():
        return []
    return [(_load_json(path), path) for path in sorted(retired_dir.glob("*.json"))]
