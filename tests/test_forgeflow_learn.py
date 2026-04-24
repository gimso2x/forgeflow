from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "forgeflow_learn.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(CLI), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_task_artifacts(task_dir: Path, *, secret: bool = False) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    decision_log = {
        "task_id": "learn-task-001",
        "entries": [
            {
                "decision": "Use atomic writes for plan mutation",
                "rationale": "Direct writes can corrupt plan.json on interruption",
                "evidence": "scripts/forgeflow_plan.py uses tmp.replace(path)",
            }
        ],
    }
    review_report = {
        "task_id": "learn-task-001",
        "status": "approved",
        "findings": [
            {
                "severity": "medium",
                "problem": "Plan mutation can leave partial JSON if interrupted",
                "cause": "Non-atomic file replacement",
                "recommendation": "Use temp-file write followed by atomic replace for generated JSON artifacts",
                "evidence": "api_key=oops" if secret else "scripts/forgeflow_plan.py: write_plan",
            }
        ],
    }
    (task_dir / "decision-log.json").write_text(json.dumps(decision_log), encoding="utf-8")
    (task_dir / "review-report.json").write_text(json.dumps(review_report), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_extracts_learning_from_task_artifacts(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    output = tmp_path / "learnings.jsonl"
    write_task_artifacts(task_dir)

    result = run_cli("extract", str(task_dir), "--output", str(output))

    assert result.returncode == 0, result.stderr
    entries = read_jsonl(output)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["type"] == "review-finding"
    assert "atomic replace" in entry["rule"]
    assert entry["source"]["task_id"] == "learn-task-001"
    assert entry["evidence"] == ["scripts/forgeflow_plan.py: write_plan"]


def test_extract_skips_duplicate_learning_ids(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    output = tmp_path / "learnings.jsonl"
    write_task_artifacts(task_dir)

    first = run_cli("extract", str(task_dir), "--output", str(output))
    second = run_cli("extract", str(task_dir), "--output", str(output))

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert len(read_jsonl(output)) == 1
    assert "skipped_duplicates=1" in second.stdout


def test_extract_rejects_secret_like_evidence(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    output = tmp_path / "learnings.jsonl"
    write_task_artifacts(task_dir, secret=True)

    result = run_cli("extract", str(task_dir), "--output", str(output))

    assert result.returncode != 0
    assert "secret-like evidence" in result.stderr
    assert not output.exists()


def test_validate_existing_jsonl(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    output = tmp_path / "learnings.jsonl"
    write_task_artifacts(task_dir)
    extract = run_cli("extract", str(task_dir), "--output", str(output))
    assert extract.returncode == 0, extract.stderr

    result = run_cli("validate", str(output))

    assert result.returncode == 0, result.stderr
    assert "LEARNING VALIDATION: PASS" in result.stdout
