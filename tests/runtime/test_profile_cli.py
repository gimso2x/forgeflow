from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "forgeflow_profile.py"


def _write_profile(task_dir: Path, *, pipeline_id: str = "run-1", duration: float = 4.0, cost: float = 0.002) -> Path:
    payload = {
        "pipeline_id": pipeline_id,
        "route": "small",
        "total_duration_s": duration,
        "total_cost_usd": cost,
        "total_input_tokens": 1200,
        "total_output_tokens": 500,
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:04+00:00",
        "stages": [
            {
                "stage": "clarify",
                "model": "claude",
                "status": "success",
                "duration_s": 1.0,
                "input_tokens": 300,
                "output_tokens": 100,
                "total_tokens": 400,
                "cost_usd": 0.0004,
                "error": None,
            },
            {
                "stage": "execute",
                "model": "codex",
                "status": "success",
                "duration_s": duration - 1.0,
                "input_tokens": 900,
                "output_tokens": 400,
                "total_tokens": 1300,
                "cost_usd": cost - 0.0004,
                "error": None,
            },
        ],
    }
    path = task_dir / "pipeline-profile.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_profile_summary_reads_task_dir_artifact(tmp_path: Path) -> None:
    _write_profile(tmp_path)

    result = _run("summary", str(tmp_path))

    assert result.returncode == 0, result.stderr
    assert "Pipeline: run-1 (route=small)" in result.stdout
    assert "Stage breakdown:" in result.stdout
    assert "execute" in result.stdout
    assert "Bottlenecks:" in result.stdout


def test_profile_summary_json_outputs_loaded_profile(tmp_path: Path) -> None:
    _write_profile(tmp_path, pipeline_id="json-run")

    result = _run("summary", str(tmp_path), "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["pipeline_id"] == "json-run"
    assert payload["stages"][0]["stage"] == "clarify"


def test_profile_bottlenecks_outputs_top_metrics(tmp_path: Path) -> None:
    _write_profile(tmp_path)

    result = _run("bottlenecks", str(tmp_path), "--top", "2")

    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("duration_s: execute")
    assert any(line.startswith("cost_usd: execute") for line in lines)


def test_profile_compare_reports_regressions(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    baseline.mkdir()
    candidate.mkdir()
    _write_profile(baseline, pipeline_id="base", duration=3.0, cost=0.001)
    _write_profile(candidate, pipeline_id="cand", duration=6.0, cost=0.004)

    result = _run("compare", str(baseline), str(candidate))

    assert result.returncode == 0, result.stderr
    assert "Comparison: base (baseline) vs cand" in result.stdout
    assert "Regressions:" in result.stdout
    assert "duration +3.00s" in result.stdout
    assert "cost +$0.003000" in result.stdout


def test_profile_missing_artifact_fails(tmp_path: Path) -> None:
    result = _run("summary", str(tmp_path))

    assert result.returncode != 0
    assert "pipeline-profile.json not found" in result.stderr
