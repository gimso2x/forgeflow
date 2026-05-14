import json
import jsonschema
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_milestone_schema_validates_valid_milestone() -> None:
    schema_path = ROOT / "schemas" / "milestone.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    
    valid_milestone = {
        "schema_version": "0.2",
        "milestone_id": "M1",
        "title": "Core Feature Set",
        "status": "in_progress",
        "tasks": [
            {"task_id": "task-auth", "status": "completed"},
            {"task_id": "task-api", "status": "pending"}
        ]
    }
    jsonschema.validate(instance=valid_milestone, schema=schema)

def test_milestone_schema_rejects_invalid_milestone() -> None:
    schema_path = ROOT / "schemas" / "milestone.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    
    invalid_milestone = {
        "schema_version": "0.1",  # Expects 0.2
        "milestone_id": "M1",
        "title": "Core Feature Set",
        "status": "unknown_status", # Invalid status
        "tasks": []
    }
    
    try:
        jsonschema.validate(instance=invalid_milestone, schema=schema)
        assert False, "Should have raised a ValidationError"
    except jsonschema.exceptions.ValidationError:
        pass

def test_prompts_contain_tdd_and_debugging_instructions() -> None:
    worker_prompt_path = ROOT / "prompts" / "canonical" / "worker.md"
    planner_prompt_path = ROOT / "prompts" / "canonical" / "planner.md"
    
    worker_text = worker_prompt_path.read_text(encoding="utf-8")
    planner_text = planner_prompt_path.read_text(encoding="utf-8")
    
    assert "TDD (Test-Driven Development)" in worker_text, "Worker must contain TDD instructions"
    assert "가설 기반 디버깅(Hypothesis-Driven Debugging)" in worker_text, "Worker must contain debugging instructions"
    assert "TDD 원칙을 따르도록" in planner_text, "Planner must contain TDD planning instructions"
