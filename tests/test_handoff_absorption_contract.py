from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_parallel_work_safety_doc_defines_boundaries() -> None:
    doc = _read("docs/parallel-work.md")

    for required in [
        "One task, one workspace boundary",
        "Single writer for shared documents",
        "Worktree or terminal isolation",
        "plan-ledger.tasks[].parallel_safe",
        "Merge order is serial",
        "structured evidence refs",
    ]:
        assert required in doc


def test_workflow_links_parallel_safety_to_plan_ledger_contract() -> None:
    workflow = _read("docs/workflow.md")

    assert "Parallel work safety" in workflow
    assert "plan-ledger.tasks[].id" in workflow
    assert "files` list" in workflow
    assert "parallel_safe" in workflow
    assert "single-writer rule" in workflow
    assert "Parallel Work Safety" in workflow


def test_artifact_model_documents_structured_evidence_and_parallel_flag() -> None:
    artifact_model = _read("docs/artifact-model.md")
    schema = _read("schemas/plan-ledger.schema.json")

    assert "`evidence_refs`는 문자열 로그가 아니라 `{type, target, relation, label?}` 객체" in artifact_model
    assert "`parallel_safe`는 병렬 실행 허가 신호" in artifact_model
    assert '"parallel_safe"' in schema
    assert '"type"' in schema and '"target"' in schema and '"relation"' in schema


def test_developer_handoff_template_is_executable() -> None:
    doc = _read("docs/developer-handoff-template.md")

    for required in [
        "Background",
        "Goal",
        "In scope",
        "Out of scope",
        "Acceptance criteria",
        "File locations",
        "Execution order",
        "Verification",
        "Handoff summary",
    ]:
        assert required in doc

    assert "Do not depend on hidden chat history" in doc
    assert ".forgeflow/tasks/<task-id>/plan-ledger.json" in doc


def test_init_skill_seeds_blueprint_without_crossing_stage_boundary() -> None:
    skill = _read("skills/forgeflow-init/SKILL.md")

    assert "Starter blueprint" in skill
    assert "initial team/role split" in skill
    assert "docs/PRD.md" in skill
    assert "docs/ARCHITECTURE.md" in skill
    assert "docs/developer-handoff-template.md" in skill
    assert "These are drafts, not approval to skip `clarify`" in skill
    assert "Do not automatically continue into `/forgeflow:clarify`" in skill


def test_role_model_routing_doc_keeps_role_boundaries_explicit() -> None:
    doc = _read("docs/role-model-routing.md")
    workflow = _read("docs/workflow.md")

    for required in [
        "planning",
        "implementation",
        "review",
        "qa",
        "forgeflow_runtime/operator_routing.py",
        "Model names are intentionally not hard-coded in artifacts",
        "Do not let the implementing session silently approve its own work",
    ]:
        assert required in doc

    assert "Role / Model Routing" in workflow
