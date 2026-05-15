import json
from pathlib import Path
from tests.runtime.cli_helpers import run_orchestrator_cli, write_json

def test_clarify_generates_agents_from_brief_specialists(tmp_path: Path) -> None:
    # 1. Setup project structure
    project_root = tmp_path / "my-app"
    project_root.mkdir()
    (project_root / "package.json").write_text('{"name": "my-app"}')
    
    task_id = "migration-task"
    task_dir = project_root / ".forgeflow" / "tasks" / task_id
    task_dir.mkdir(parents=True)
    
    # 2. Create brief.json with explicit required_specialists and ALL required schema fields
    brief = {
        "schema_version": "0.2",
        "task_id": task_id,
        "objective": "Migrate login feature",
        "route": "high",
        "risk_level": "high",
        "required_specialists": ["frontend-execute", "ux-review"],
        "in_scope": ["login feature"],
        "out_of_scope": ["payment feature"],
        "constraints": ["must use react"],
        "acceptance_criteria": ["login works"]
    }
    write_json(task_dir / "brief.json", brief)
    
    # 3. Create other required artifacts to satisfy clarify
    write_json(task_dir / "run-state.json", {
        "schema_version": "0.2",
        "task_id": task_id,
        "current_stage": "clarify",
        "status": "not_started",
        "completed_gates": [],
        "failed_gates": [],
        "retries": {},
        "evidence_refs": [],
        "spec_review_approved": False,
        "quality_review_approved": False
    })
    
    # 4. Run clarify
    result = run_orchestrator_cli("clarify", "--task-dir", str(task_dir))
    assert result.returncode == 0, f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    
    # 5. Verify agents and skills are created in project_root/.gemini
    dot_dir = project_root / ".gemini"
    assert dot_dir.exists(), f".gemini dir missing in {project_root}"
    
    agents_dir = dot_dir / "agents"
    assert (agents_dir / "frontend-execute.md").exists(), f"frontend-execute agent missing in {agents_dir}"
    assert (agents_dir / "ux-review.md").exists(), f"ux-review agent missing in {agents_dir}"
    
    # 6. Verify metadata (GEMINI.md) is created in task_dir and mentions them
    metadata_file = task_dir / "GEMINI.md"
    assert metadata_file.exists(), f"GEMINI.md missing in {task_dir}"
    
    metadata_content = metadata_file.read_text()
    assert "- `frontend-execute.md`" in metadata_content
    assert "- `ux-review.md`" in metadata_content
    print("Test passed: specialists successfully scaffolded and documented.")
