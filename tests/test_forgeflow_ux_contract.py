from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_clarify_skill_allows_focused_requirement_questions() -> None:
    text = (ROOT / "skills" / "clarify" / "SKILL.md").read_text(encoding="utf-8")

    assert "Ask up to 5 clarifying questions" in text
    assert "materially improve requirements" in text
    assert "do not pad the list" in text
    assert "product behavior, user/audience, success criteria" in text
    assert "implementation chores the agent should infer from repo inspection" in text
    assert "Ask at most 2 clarifying questions" not in text
    assert "only for true blockers" not in text
    assert "blocker-only" not in text
    assert "artifact notes, not questions the user must answer" in text
    assert "Do not ask the user to write the plan for you." in text
    assert "다음 스텝으로 `/forgeflow:plan`을 진행하시겠습니까? (y/n)" in text
    assert "바로 plan으로 간다" not in text


def test_plan_and_run_skills_separate_stage_boundary_approval_from_reapproval() -> None:
    plan_text = (ROOT / "skills" / "plan" / "SKILL.md").read_text(encoding="utf-8")
    run_text = (ROOT / "skills" / "run" / "SKILL.md").read_text(encoding="utf-8")

    assert "계획 내용 재승인" in plan_text
    assert "다음 스텝으로 `/forgeflow:run`을 진행하시겠습니까? (y/n)" in plan_text
    assert "계획 확정. 바로 run." not in plan_text
    assert "이미 승인된 run scope 안에서는" in run_text
    assert "Do not pause just to reconfirm the same plan before editing files." in run_text


def test_canonical_prompts_require_stage_boundary_approval_without_reapproval_loops() -> None:
    coordinator = (ROOT / "prompts" / "canonical" / "coordinator.md").read_text(encoding="utf-8")
    planner = (ROOT / "prompts" / "canonical" / "planner.md").read_text(encoding="utf-8")
    worker = (ROOT / "prompts" / "canonical" / "worker.md").read_text(encoding="utf-8")

    assert "stage 경계를 넘을 때는" in coordinator
    assert "사용자 승인 질문으로 멈춘다" in planner
    assert "이미 승인된 run scope 안에서는" in worker
    assert "불필요하게 사용자 승인 단계로 바꾸지 않는다" not in coordinator


def test_docs_explain_stage_boundaries_are_user_approved_not_manual_operation() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

    assert "사용자가 stage 명령을 하나하나 대신 운영하라는 뜻은 아니다" in readme
    assert "계획을 세워주세요" in readme
    assert "agent-owned decomposition" in readme
    assert "stage 경계를 넘을 때는 닫힌 질문으로 멈춘다" in readme
    assert "다음 스텝으로 `/forgeflow:run`을 진행하시겠습니까? (y/n)" in install
    assert "자연스럽게 이어받는 쪽이 정본 UX입니다" not in install


def test_make_validate_runs_ux_contract_tests() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "tests/test_forgeflow_ux_contract.py" in makefile
