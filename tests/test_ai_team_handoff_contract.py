from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ai_team_handoff_is_absorbed_into_existing_stage_docs() -> None:
    workflow = (ROOT / "docs" / "workflow.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    review_model = (ROOT / "docs" / "review-model.md").read_text(encoding="utf-8")

    for required_text in [
        "역할 분리는 새 stage가 아니라 기존 stage",
        "`plan`은 선택된 역할별 task와 handoff를 `plan-ledger`에 남기며",
        "사람 최종판단 원칙은 review gate를 약화하지 않는다",
    ]:
        assert required_text in workflow

    for required_text in [
        "Role-split AI team overlay",
        "QA / UX / Security 관점은 작업 위험과 route가 요구할 때만 on-demand로 활성화",
        "role assignment, skipped-role rationale, specialist output은 `plan-ledger`, `run-state`, `review-report`",
        "AI 팀을 상시 구동하거나 역할 수를 무한히 늘리는 구조",
    ]:
        assert required_text in architecture

    for required_text in [
        "AI reviewer 코멘트도 최종판단이 아니다",
        "evidence 없는 코멘트는 약한 신호로 취급한다",
        "`review-report.json`은 사람이 최종판단할 수 있게 근거와 tradeoff를 남기는 자료",
    ]:
        assert required_text in review_model


def test_ai_team_handoff_updates_role_prompts_and_team_policy() -> None:
    coordinator = (ROOT / "prompts" / "canonical" / "coordinator.md").read_text(encoding="utf-8")
    planner = (ROOT / "prompts" / "canonical" / "planner.md").read_text(encoding="utf-8")
    spec_reviewer = (ROOT / "prompts" / "canonical" / "spec-reviewer.md").read_text(encoding="utf-8")
    quality_reviewer = (ROOT / "prompts" / "canonical" / "quality-reviewer.md").read_text(encoding="utf-8")
    team_patterns = (ROOT / "policy" / "canonical" / "team-patterns.yaml").read_text(encoding="utf-8")

    assert "역할 분리는 on-demand로만 적용한다" in coordinator
    assert "canonical truth는 chat이 아니라 `plan-ledger.json`, `run-state.json`, `review-report.json`" in coordinator
    assert "role owner와 이유를 `plan-ledger`에 남기고" in planner
    assert "구현 전에 role별 task, expected output, verification" in planner
    assert "AI reviewer 코멘트는 자동 정답이 아니다" in spec_reviewer
    assert "영향도가 낮거나 근거가 약한 코멘트는 blocker로 승격하지 말고" in spec_reviewer
    assert "QA/UX/security 관점은 작업에 필요한 경우만 적용한다" in quality_reviewer
    assert "plan-ledger entry linking selected role to expected output and verification" in team_patterns
    assert "review-report finding only when specialist output is evidence-backed" in team_patterns

    for adapter in ["claude", "codex", "gemini"]:
        agents = ROOT / "adapters" / "targets" / adapter / "agents"
        assert "Role-split AI team discipline" in (agents / "forgeflow-coordinator.md").read_text(encoding="utf-8")
        assert "Plan-led role assignment" in (agents / "forgeflow-planner.md").read_text(encoding="utf-8")
        assert "Human-context triage" in (agents / "forgeflow-spec-reviewer.md").read_text(encoding="utf-8")
        assert "On-demand specialist lens" in (agents / "forgeflow-quality-reviewer.md").read_text(encoding="utf-8")

def test_standalone_review_entrypoint_contract_is_documented_and_schematized() -> None:
    workflow = (ROOT / "docs" / "workflow.md").read_text(encoding="utf-8")
    review_model = (ROOT / "docs" / "review-model.md").read_text(encoding="utf-8")
    spec_reviewer = (ROOT / "prompts" / "canonical" / "spec-reviewer.md").read_text(encoding="utf-8")
    quality_reviewer = (ROOT / "prompts" / "canonical" / "quality-reviewer.md").read_text(encoding="utf-8")
    review_input_schema = (ROOT / "schemas" / "review-input.schema.json").read_text(encoding="utf-8")
    review_report_schema = (ROOT / "schemas" / "review-report.schema.json").read_text(encoding="utf-8")

    for required_text in [
        "standalone entrypoint",
        "`review-input.json`의 brief, evidence refs, target scope",
        "`security-review`, `ux-review`는 별도 stage가 아니라 `review-input.review_roles`",
    ]:
        assert required_text in workflow

    for required_text in [
        "URL / repo / diff / 파일 묶음 같은 입력만 받아 단독 실행",
        "`brief`: 무엇을 검토하는지",
        "`evidence`: URL, repo path, diff, file, artifact, note 같은 근거 ref",
        "최소 `verdict`, `findings`, `evidence_refs`, `next_action`, `blockers`",
    ]:
        assert required_text in review_model

    assert "`brief + evidence + target_scope`를 기준으로만 판단" in spec_reviewer
    assert "`spec-review`와 `quality-review`가 기본 role" in quality_reviewer

    for required_text in [
        '"mode"',
        '"standalone"',
        '"brief"',
        '"evidence"',
        '"target_scope"',
        '"review_roles"',
        '"security-review"',
        '"ux-review"',
    ]:
        assert required_text in review_input_schema

    for required_text in ['"evidence_refs"', '"next_action"', '"blockers"', '"security"', '"ux"']:
        assert required_text in review_report_schema
