import json
from collections.abc import Callable
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def write_json() -> Callable[[Path, dict], None]:
    def _write_json(path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return _write_json


@pytest.fixture
def make_task_dir(write_json: Callable[[Path, dict], None]) -> Callable[[Path], Path]:
    def _make_task_dir(tmp_path: Path) -> Path:
        task_dir = tmp_path / "task"
        task_dir.mkdir()
        write_json(
            task_dir / "brief.json",
            {
                "schema_version": "0.1",
                "task_id": "task-001",
                "objective": "Run a small route",
                "in_scope": ["runtime"],
                "out_of_scope": [],
                "constraints": ["local only"],
                "acceptance_criteria": ["route works"],
                "risk_level": "low",
            },
        )
        write_json(
            task_dir / "run-state.json",
            {
                "schema_version": "0.1",
                "task_id": "task-001",
                "current_stage": "clarify",
                "status": "in_progress",
                "completed_gates": ["clarification_complete"],
                "failed_gates": [],
                "retries": {},
                "current_task_id": "",
                "spec_review_approved": False,
                "quality_review_approved": False,
            },
        )
        return task_dir

    return _make_task_dir


@pytest.fixture
def assert_schema_valid() -> Callable[[str, dict], None]:
    def _load_schema(name: str) -> dict:
        return json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))

    def _assert_schema_valid(name: str, payload: dict) -> None:
        errors = sorted(Draft202012Validator(_load_schema(name)).iter_errors(payload), key=lambda err: list(err.path))
        assert not errors, [f"{list(err.path)}: {err.message}" for err in errors]

    return _assert_schema_valid
