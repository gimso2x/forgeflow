from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_clarify_skill_allows_focused_requirement_questions() -> None:
    text = (ROOT / "skills" / "clarify" / "SKILL.md").read_text(encoding="utf-8")

    assert "Ask up to 5 clarifying questions" in text
    assert "materially improve requirements" in text
    assert "do not pad the list" in text
    assert "product behavior, user/audience, success criteria" in text
    assert "implementation chores the agent should infer from repo inspection" in text
    assert "confirmations that can be recorded as bounded assumptions" in text
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


def test_canonical_workflow_skills_are_artifact_first_by_default() -> None:
    clarify = (ROOT / "skills" / "clarify" / "SKILL.md").read_text(encoding="utf-8")
    plan = (ROOT / "skills" / "plan" / "SKILL.md").read_text(encoding="utf-8")
    run = (ROOT / "skills" / "run" / "SKILL.md").read_text(encoding="utf-8")
    review = (ROOT / "skills" / "review" / "SKILL.md").read_text(encoding="utf-8")
    ship = (ROOT / "skills" / "ship" / "SKILL.md").read_text(encoding="utf-8")
    forgeflow = (ROOT / "skills" / "forgeflow" / "SKILL.md").read_text(encoding="utf-8")

    for text in [clarify, plan, run, review, ship, forgeflow]:
        assert "Default to **artifact-first mode**." in text
        assert "response-only mode" not in text
        assert ".forgeflow/tasks/<task-id>/" in text
        assert "dry run" in text

    assert "write `brief.json` under the active task directory" in clarify
    assert "write `plan.json` under the active task directory" in plan
    assert "update `run-state.json` before and after code changes" in run
    assert "write `review-report.json` under the active task directory" in review
    assert "Preserve artifacts/evidence instead of burying them in chat." in ship


def test_canonical_prompts_require_stage_boundary_approval_without_reapproval_loops() -> None:
    coordinator = (ROOT / "prompts" / "canonical" / "coordinator.md").read_text(encoding="utf-8")
    planner = (ROOT / "prompts" / "canonical" / "planner.md").read_text(encoding="utf-8")
    worker = (ROOT / "prompts" / "canonical" / "worker.md").read_text(encoding="utf-8")

    assert "stage 경계를 넘을 때는" in coordinator
    assert "사용자 승인 질문으로 멈춘다" in planner
    assert "이미 승인된 run scope 안에서는" in worker
    assert "불필요하게 사용자 승인 단계로 바꾸지 않는다" not in coordinator


def test_canonical_prompts_embed_karpathy_execution_discipline() -> None:
    planner = (ROOT / "prompts" / "canonical" / "planner.md").read_text(encoding="utf-8")
    worker = (ROOT / "prompts" / "canonical" / "worker.md").read_text(encoding="utf-8")
    reviewer = (ROOT / "prompts" / "canonical" / "spec-reviewer.md").read_text(encoding="utf-8")
    review_skill = (ROOT / "skills" / "review" / "SKILL.md").read_text(encoding="utf-8")

    assert "success condition" in planner
    assert "simplest sufficient plan" in planner
    assert "assumptions" in planner
    assert "Every changed line should trace directly to the approved request" in worker
    assert "no drive-by refactors" in worker
    assert "silent fallback, dual write, shadow path" in worker
    assert "smallest safe change" in reviewer
    assert "silent fallback, dual write, shadow path" in reviewer
    assert "unverified assumptions" in reviewer
    assert "Every changed line should trace directly to the approved request" in review_skill
    assert "silent fallback, dual write, and shadow-path ownership drift" in review_skill


def test_docs_explain_stage_boundaries_are_user_approved_not_manual_operation() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

    assert "사용자가 stage 명령을 하나하나 대신 운영하라는 뜻은 아니다" in readme
    assert "계획을 세워주세요" in readme
    assert "agent-owned decomposition" in readme
    assert "stage 경계를 넘을 때는 닫힌 질문으로 멈춘다" in readme
    assert "다음 스텝으로 `/forgeflow:run`을 진행하시겠습니까? (y/n)" in install
    assert "자연스럽게 이어받는 쪽이 정본 UX입니다" not in install


def test_readme_documents_plugin_init_cache_guard_and_release_smoke() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Claude/Codex plugin cache" in readme
    assert "cache 아래에 `.forgeflow/tasks/...`를 만들지 않고 실패" in readme
    assert "traceback 없이 `ERROR:`" in readme
    assert "일반 프로젝트 경로에 `plugin/marketplace`" in readme
    assert "--task-dir /path/to/your-project/.forgeflow/tasks/<task-id>" in readme
    assert "Maintainer verification before release or plugin update" in readme
    assert "make smoke-claude-plugin" in readme
    assert "writes starter artifacts through `/forgeflow:init`" in readme


def test_makefile_defines_policy_scan_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "policy-scan:" in makefile
    assert "scripts/policy_scan.py" in makefile


def test_plan_skill_documents_refactor_mode_without_new_stage_or_schema() -> None:
    plan = (ROOT / "skills" / "plan" / "SKILL.md").read_text(encoding="utf-8")
    decision = (ROOT / "docs" / "refactor-planning-decision.md").read_text(encoding="utf-8")

    for required_text in [
        "## Refactor mode",
        "behavior-preserving structural change across an existing public surface",
        "migration-sensitive internal reorganization",
        "test-sensitive decomposition work",
        "removal/replacement of implementation machinery while preserving user-visible behavior",
        "not a new `/forgeflow:refactor-plan` command",
        "`schemas/plan.schema.json` remains authoritative",
        "preserved public behavior statement",
        "explicit non-goals",
        "migration boundary",
        "rollback, escape hatch, or explicit not-applicable note",
        "tiny always-green implementation steps",
        "regression verification strategy focused on public behavior",
        "Existing coverage",
        "docs/refactor-planning-decision.md",
    ]:
        assert required_text in plan

    assert "Status: accepted" in decision
    assert "`schemas/plan.schema.json` is unchanged" in decision
    assert "does not create `/forgeflow:refactor-plan`" in decision


def test_issue_readiness_and_git_safety_policy_have_single_owners() -> None:
    to_issues = (ROOT / "docs" / "to-issues-model.md").read_text(encoding="utf-8")
    review_model = (ROOT / "docs" / "review-model.md").read_text(encoding="utf-8")
    review_skill = (ROOT / "skills" / "review" / "SKILL.md").read_text(encoding="utf-8")

    for required_text in [
        "## Issue readiness policy",
        "human-gated work from agent-ready work",
        "user-facing behavior from implementation guesses",
        "Root cause should be investigated before filing fix-oriented issues",
        "GitHub labels and milestones are publication metadata",
        "does not create a runtime issue state machine",
    ]:
        assert required_text in to_issues

    for required_text in [
        "## Git safety and diff-scope policy",
        "Broad staging is forbidden unless explicitly justified",
        "Destructive git actions require explicit user approval",
        "Dirty user work is preserved by default",
        "Reviews must name the exact diff scope and verification evidence",
        "adapter-neutral",
    ]:
        assert required_text in review_model

    assert "docs/review-model.md owns git-safety policy" in review_skill
    assert "Do not redefine git safety in this skill" in review_skill
    assert "Claude-specific hook setup" not in review_model
    assert "safe-commit" not in review_model


def test_so2x_minimum_spec_and_plan_gates_are_documented() -> None:
    specify = (ROOT / "skills" / "specify" / "SKILL.md").read_text(encoding="utf-8")
    plan = (ROOT / "skills" / "plan" / "SKILL.md").read_text(encoding="utf-8")

    for required_text in [
        "Minimum requirements gate",
        "`Goal`",
        "`Requirements`",
        "`Implementation Constraints`",
        "`Verification`",
    ]:
        assert required_text in specify

    for required_text in [
        "Minimum plan gate",
        "`Goal`",
        "`Requirements`",
        "`Implementation Steps`",
        "`Verification`",
        "Requirement traceability",
        "Each non-trivial step must include `fulfills`",
        "Every `fulfills` target must have a matching `verify_plan` entry",
        "Do not proceed to `/forgeflow:run` if one of those is missing for non-trivial work.",
    ]:
        assert required_text in plan
