from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.evolution_observations import (
    append_review_blocker_observation,
    read_observations,
    suggest_from_task,
)

ROOT = Path(__file__).resolve().parents[2]


def test_append_review_blocker_observation_is_task_local_and_sanitized(tmp_path: Path) -> None:
    task_dir = tmp_path / ".forgeflow" / "tasks" / "task-001"
    task_dir.mkdir(parents=True)

    event = append_review_blocker_observation(
        task_dir,
        task_id="task-001",
        stage="quality-review",
        gate="quality-review-approved",
        review_payload={
            "verdict": "changes_requested",
            "review_type": "quality",
            "findings": ["raw user complaint and secret text must not be persisted"],
            "open_blockers": ["Generated adapter drift: token sk-SECRET must not leak"],
        },
        artifact_refs=["review-report.json"],
        reason="quality-review requires approved quality review-report artifact",
    )

    observation_path = task_dir / "evolution-observations.jsonl"
    assert observation_path.is_file()
    persisted = json.loads(observation_path.read_text(encoding="utf-8").strip())
    assert persisted == event
    assert persisted["schema_version"] == "0.1"
    assert persisted["event"] == "review_blocker_observed"
    assert persisted["blocker_codes"] == ["generated_adapter_drift_token_sk_secret_must_not_leak"]
    assert persisted["would_generate_rule"] is False
    assert persisted["would_enforce"] is False
    assert "findings" not in persisted
    assert "raw user complaint" not in observation_path.read_text(encoding="utf-8")


def test_suggest_from_task_is_read_only_and_does_not_create_evolution_dir(tmp_path: Path) -> None:
    task_dir = tmp_path / ".forgeflow" / "tasks" / "task-001"
    task_dir.mkdir(parents=True)
    append_review_blocker_observation(
        task_dir,
        task_id="task-001",
        stage="quality-review",
        gate="quality-review-approved",
        review_payload={"verdict": "changes_requested", "review_type": "quality", "open_blockers": ["missing verification"]},
        artifact_refs=["review-report.json"],
        reason="quality-review requires approved quality review-report artifact",
    )

    before = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
    suggestion = suggest_from_task(tmp_path, "task-001")
    after = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))

    assert before == after
    assert suggestion["read_only"] is True
    assert suggestion["would_mutate"] is False
    assert suggestion["would_generate_rule"] is False
    assert suggestion["would_enforce"] is False
    assert suggestion["suggestions"][0]["suggested_rule_id"] == "observed-missing-verification"
    assert not (tmp_path / ".forgeflow" / "evolution").exists()


def test_observations_cli_outputs_json_without_mutating(tmp_path: Path) -> None:
    task_dir = tmp_path / ".forgeflow" / "tasks" / "task-001"
    task_dir.mkdir(parents=True)
    append_review_blocker_observation(
        task_dir,
        task_id="task-001",
        stage="quality-review",
        gate="quality-review-approved",
        review_payload={"verdict": "changes_requested", "review_type": "quality", "open_blockers": ["missing verification"]},
        artifact_refs=["review-report.json"],
        reason="quality-review requires approved quality review-report artifact",
    )

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "observations", "--task", "task-001", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["read_only"] is True
    assert payload["would_mutate"] is False
    assert len(payload["observations"]) == 1


def test_suggest_cli_is_read_only(tmp_path: Path) -> None:
    task_dir = tmp_path / ".forgeflow" / "tasks" / "task-001"
    task_dir.mkdir(parents=True)
    append_review_blocker_observation(
        task_dir,
        task_id="task-001",
        stage="quality-review",
        gate="quality-review-approved",
        review_payload={"verdict": "changes_requested", "review_type": "quality", "open_blockers": ["missing verification"]},
        artifact_refs=["review-report.json"],
        reason="quality-review requires approved quality review-report artifact",
    )

    before = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "suggest", "--task", "task-001", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    after = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))

    assert result.returncode == 0, result.stderr
    assert before == after
    payload = json.loads(result.stdout)
    assert payload["read_only"] is True
    assert payload["would_mutate"] is False
    assert payload["would_generate_rule"] is False
    assert payload["would_enforce"] is False
