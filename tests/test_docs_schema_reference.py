from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_REF = ROOT / "docs" / "reference" / "schemas.md"


def test_brief_reference_matches_current_required_field_names() -> None:
    text = SCHEMAS_REF.read_text(encoding="utf-8")
    for required in [
        '"in_scope": ["..."]',
        '"out_of_scope": ["..."]',
        '"acceptance_criteria": ["..."]',
        '"risk_level": "low|medium|high|critical"',
        '"route": "small|medium|high|epic"',
    ]:
        assert required in text

    for stale in [
        '"success_criteria"',
        '"risk": "low|medium|high"',
        '"route": "small|medium|high"',
        '"selected_architecture"',
    ]:
        assert stale not in text


def test_run_state_reference_uses_current_stage_and_required_fields() -> None:
    text = SCHEMAS_REF.read_text(encoding="utf-8")
    for required in [
        '"current_stage": "execute"',
        '"status": "in_progress"',
        '"completed_gates": ["clarify", "plan"]',
        '"failed_gates": []',
        '"retries": {"execute": 0}',
        '"spec_review_approved": false',
        '"quality_review_approved": false',
    ]:
        assert required in text

    for stale in [
        '"current_stage": "run"',
        '"tasks_completed"',
        '"tasks_remaining"',
    ]:
        assert stale not in text


def test_cli_docs_include_current_risk_and_route_vocabularies() -> None:
    cli = (ROOT / "docs" / "reference" / "cli.md").read_text(encoding="utf-8")
    init_skill = (ROOT / "skills" / "init" / "SKILL.md").read_text(encoding="utf-8")
    codex_desktop = (ROOT / "docs" / "codex-desktop.md").read_text(encoding="utf-8")

    for text in [cli, init_skill, codex_desktop]:
        assert "low|medium|high|critical" in text
        assert "low|medium|high [" not in text
        assert "--risk low|medium|high\n" not in text

    for text in [cli, init_skill]:
        assert "small|medium|high|epic" in text


def test_cli_docs_include_current_adapter_vocabulary() -> None:
    cli = (ROOT / "docs" / "reference" / "cli.md").read_text(encoding="utf-8")

    assert "--adapter claude|codex|gemini" in cli
    assert "--adapter claude|codex|generic" not in cli
