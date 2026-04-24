from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_clarify_skill_requires_minimal_blocker_only_questions() -> None:
    text = (ROOT / "skills" / "clarify" / "SKILL.md").read_text(encoding="utf-8")

    assert "Ask at most 2 clarifying questions" in text
    assert "only for true blockers" in text
    assert "Do not ask the user to write the plan for you." in text
    assert "route=medium. 바로 plan으로 간다." in text
    assert "승인해 주세요" in text


def test_plan_and_run_skills_forbid_reapproval_ceremony() -> None:
    plan_text = (ROOT / "skills" / "plan" / "SKILL.md").read_text(encoding="utf-8")
    run_text = (ROOT / "skills" / "run" / "SKILL.md").read_text(encoding="utf-8")

    assert 'do not ask for a second "plan approval" by default' in plan_text
    assert "내가 계획을 세워?" in plan_text
    assert "계획은 내가 세운다" in plan_text
    assert "Do not pause just to reconfirm the same plan before editing files." in run_text
    assert "승인된 계획대로 실행하겠습니다." in run_text


def test_canonical_prompts_push_agent_owned_handoff_not_user_reapproval() -> None:
    coordinator = (ROOT / "prompts" / "canonical" / "coordinator.md").read_text(encoding="utf-8")
    planner = (ROOT / "prompts" / "canonical" / "planner.md").read_text(encoding="utf-8")
    worker = (ROOT / "prompts" / "canonical" / "worker.md").read_text(encoding="utf-8")

    assert "불필요하게 사용자 승인 단계로 바꾸지 않는다" in coordinator
    assert "사용자가 plan을 대신 세우거나 재승인하게 만들기" in planner
    assert "불필요한 재승인 요구" in worker


def test_docs_explain_users_should_not_operate_each_stage_manually() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

    assert "사용자가 stage 명령을 하나하나 대신 운영하라는 뜻은 아니다" in readme
    assert "계획을 세워주세요" in readme
    assert "agent-owned decomposition" in readme
    assert "사용자가 매번 workflow 운영자가 될 필요는 없습니다" in install
    assert "agent가 intake→plan→run을 자연스럽게 이어받는 쪽이 정본 UX입니다" in install


def test_make_validate_runs_ux_contract_tests() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "tests/test_forgeflow_ux_contract.py" in makefile
