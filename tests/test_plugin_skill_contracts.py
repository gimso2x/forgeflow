from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} missing YAML frontmatter"
    end = text.find("\n---", 4)
    assert end != -1, f"{path} missing closing YAML frontmatter delimiter"
    return text[4:end]


def test_all_skill_frontmatter_is_valid_yaml() -> None:
    for skill_path in sorted((ROOT / "skills").glob("*/SKILL.md")):
        data = yaml.safe_load(_frontmatter(skill_path))
        assert isinstance(data, dict), skill_path
        assert data.get("name"), skill_path
        assert data.get("description"), skill_path
        assert data.get("validate_prompt"), skill_path


def test_clarify_label_only_rule_overrides_normal_brief_procedure() -> None:
    skill = (ROOT / "skills" / "clarify" / "SKILL.md").read_text(encoding="utf-8")

    assert "label-only route selection" in skill
    assert "Return only the selected route label" in skill
    assert "label only" in skill
    assert "output exactly one of `small`, `medium`, or `large_high_risk`" in skill
    assert "State the route and why, unless an exact-output/label-only instruction applies." in skill
    assert (
        "Produce the brief in a structured form the next skill can consume, "
        "unless an exact-output/label-only instruction applies."
    ) in skill


def test_review_evidence_discipline_distinguishes_observed_from_reported() -> None:
    skill = (ROOT / "skills" / "review" / "SKILL.md").read_text(encoding="utf-8")

    for required_text in [
        "Review evidence is not fan fiction.",
        "reported evidence",
        "Do not say lint/build/tests/dev-server/runtime verification passed unless you ran the command",
        "mark it as missing or reported",
        "Referenced repository paths must exist in the reviewed diff/worktree",
        "Path hallucination is a blocker, not a typo.",
        "Separate observed evidence from reported or missing evidence before choosing a verdict.",
    ]:
        assert required_text in skill


def test_init_skill_exposes_orchestrator_bootstrap_without_auto_chaining() -> None:
    skill_path = ROOT / "skills" / "init" / "SKILL.md"
    assert skill_path.exists()
    skill = skill_path.read_text(encoding="utf-8")

    for required_text in [
        "name: init",
        "scripts/run_orchestrator.py init",
        "--task-id",
        "--objective",
        "--risk low|medium|high",
        "bootstrap a new task workspace",
        "without overwriting existing artifacts",
        "Do not automatically continue into `/forgeflow:clarify`",
        "다음 스텝으로 `/forgeflow:clarify`를 진행하시겠습니까? (y/n)",
    ]:
        assert required_text in skill


def test_safe_commit_skill_locks_pre_commit_safety_contract() -> None:
    skill_path = ROOT / "skills" / "safe-commit" / "SKILL.md"
    assert skill_path.exists()
    skill = skill_path.read_text(encoding="utf-8")

    for required_text in [
        "name: safe-commit",
        "secret scan",
        "file-size and generated-file risk",
        "scope drift",
        "verification evidence",
        "request traceability",
        "final disposition: `SAFE` or `UNSAFE`",
        "Redact credentials as `[REDACTED]`.",
    ]:
        assert required_text in skill


def test_check_harness_skill_scores_core_harness_health_categories() -> None:
    skill_path = ROOT / "skills" / "check-harness" / "SKILL.md"
    assert skill_path.exists()
    skill = skill_path.read_text(encoding="utf-8")

    for required_text in [
        "name: check-harness",
        "total score out of 100",
        "Entry points",
        "Shared context",
        "Execution habits",
        "Verification",
        "Maintainability",
        "smallest sufficient fixes",
    ]:
        assert required_text in skill


def test_cross_cutting_so2x_skills_are_listed_in_skill_index() -> None:
    index = (ROOT / "skills" / "SKILLS.md").read_text(encoding="utf-8")

    for required_text in [
        "[`safe-commit`](safe-commit/SKILL.md)",
        "[`check-harness`](check-harness/SKILL.md)",
        "so2x-harness",
    ]:
        assert required_text in index


def test_to_issues_skill_absorbs_mattpocock_pattern_as_optional_helper() -> None:
    skill_path = ROOT / "skills" / "to-issues" / "SKILL.md"
    assert skill_path.exists()
    skill = skill_path.read_text(encoding="utf-8")
    index = (ROOT / "skills" / "SKILLS.md").read_text(encoding="utf-8")

    for required_text in [
        "name: to-issues",
        "Input Artifacts",
        "Output Artifacts",
        "schemas/issue-drafts.schema.json",
        "vertical, issue-ready draft slices",
        "Do not call the GitHub API",
        "plan.json` owns scope",
        "AFK` and `HITL` are upstream commentary only",
        ".forgeflow/tasks/<task-id>/",
    ]:
        assert required_text in skill

    assert "[`to-issues`](to-issues/SKILL.md)" in index
    assert "mattpocock/skills" in index


def test_design_interface_skill_absorbs_contract_first_pattern_as_optional_helper() -> None:
    skill_path = ROOT / "skills" / "design-interface" / "SKILL.md"
    assert skill_path.exists()
    skill = skill_path.read_text(encoding="utf-8")
    index = (ROOT / "skills" / "SKILLS.md").read_text(encoding="utf-8")

    for required_text in [
        "name: design-interface",
        "Input Artifacts",
        "Output Artifacts",
        "contracts.md",
        "schemas/interface-spec.schema.json",
        "at least two materially different interface options",
        "No new canonical `/forgeflow:design` stage",
        "Do not create a parallel design source of truth",
        ".forgeflow/tasks/<task-id>/",
    ]:
        assert required_text in skill

    assert "[`design-interface`](design-interface/SKILL.md)" in index
    assert "mattpocock/skills" in index


def test_canonical_forgeflow_skills_default_to_artifact_first_mode() -> None:
    for skill_name in ["forgeflow", "clarify", "specify", "plan", "run", "review", "ship"]:
        skill = (ROOT / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")

        assert "Default to **artifact-first mode**." in skill


def test_codex_plugin_accepts_forgeflow_slash_style_prompts() -> None:
    forgeflow = (ROOT / "skills" / "forgeflow" / "SKILL.md").read_text(encoding="utf-8")
    assert "Codex exposes plugin skills" in forgeflow

    expected = {
        "init": "/forgeflow:init",
        "clarify": "/forgeflow:clarify",
        "specify": "/forgeflow:specify",
        "plan": "/forgeflow:plan",
        "run": "/forgeflow:run",
        "review": "/forgeflow:review",
        "ship": "/forgeflow:ship",
        "finish": "/forgeflow:finish",
    }
    for skill_name, slash_prompt in expected.items():
        skill = (ROOT / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        assert slash_prompt in skill
        assert "response-only mode" not in skill
        assert "return their content in the chat response" not in skill
        assert "work/my-task" not in skill
        if skill_name == "init":
            assert "Plugin-cache safety rule" in skill
        else:
            assert "Never write inside the plugin installation directory, marketplace cache" in skill
        if skill_name != "init":
            assert "explicitly asks for a dry run" in skill
        assert ".forgeflow/tasks/<task-id>" in skill


# --- Route-aware enforcement contracts ---


def test_run_skill_has_route_aware_exit_requirements() -> None:
    skill = (ROOT / "skills" / "run" / "SKILL.md").read_text(encoding="utf-8")

    assert "Route-aware exit requirements" in skill
    assert "run-state.json" in skill
    # Each route should have specific exit guidance
    assert "**small** route" in skill
    assert "**medium** route" in skill
    assert "**large_high_risk** route" in skill
    # large_high_risk must auto-chain to review
    assert "large_high_risk route 실행 완료" in skill
    assert "/forgeflow:review를 자동으로 시작합니다" in skill
    # Must not end without run-state.json
    assert "Do not end the run stage without writing `run-state.json`" in skill


def test_run_skill_initializes_run_state_before_editing() -> None:
    skill = (ROOT / "skills" / "run" / "SKILL.md").read_text(encoding="utf-8")

    assert "Initialize `run-state.json`" in skill
    assert "current_stage: \"execute\"" in skill
    assert "status: \"in_progress\"" in skill


def test_forgeflow_stage_skills_support_non_interactive_approval_mode() -> None:
    for rel in [
        "skills/plan/SKILL.md",
        "skills/run/SKILL.md",
        "skills/review/SKILL.md",
        ".claude-plugin/skills/plan.md",
        ".claude-plugin/skills/run.md",
        ".claude-plugin/skills/review.md",
    ]:
        skill = (ROOT / rel).read_text(encoding="utf-8")
        assert "Automation / non-interactive approval mode" in skill
        assert "--auto-approve" in skill
        assert "--non-interactive" in skill
        assert "Do not pause at the normal stage-boundary y/n prompt" in skill


def test_worker_prompts_require_bounded_verification_fix_loop() -> None:
    for rel in [
        "skills/run/SKILL.md",
        ".claude-plugin/skills/run.md",
        "adapters/targets/claude/agents/forgeflow-worker.md",
        "adapters/targets/codex/agents/forgeflow-worker.md",
    ]:
        prompt = (ROOT / rel).read_text(encoding="utf-8")
        assert "Bounded verification fix loop" in prompt
        assert "Repeat for at most 3 attempts" in prompt
        assert "Mark work complete only after the latest required verification passes" in prompt
        assert "run-state.json.evidence_refs" in prompt
        assert "run-state.retries.execute" in prompt
        assert "verification:FAIL" in prompt
        assert "verification:PASS" in prompt
        assert "react-hooks/set-state-in-effect" in prompt
        assert "set `run-state.status` to `blocked`" in prompt
        assert "if failures remain, set `run-state.status` to `blocked` or `failed`" not in prompt


def test_codex_prompts_require_minimum_artifact_contract_for_small_tasks() -> None:
    for rel in [
        "adapters/targets/codex/agents/forgeflow-coordinator.md",
        "adapters/targets/codex/agents/forgeflow-worker.md",
        "adapters/targets/codex/rules/forgeflow-nextjs-worker.mdc",
    ]:
        prompt = (ROOT / rel).read_text(encoding="utf-8")
        assert "Minimum artifact contract" in prompt
        assert "A small task is incomplete unless it writes at least `brief.json` and `run-state.json`" in prompt
        assert "Do not rely on the user prompt to restate this requirement" in prompt


def test_review_skill_has_route_aware_behavior() -> None:
    skill = (ROOT / "skills" / "review" / "SKILL.md").read_text(encoding="utf-8")

    assert "Route-aware review behavior" in skill
    assert "**small** route" in skill
    assert "**medium** route" in skill
    assert "**large_high_risk** route" in skill
    # large_high_risk must produce separate spec + quality reports
    assert "review-report-spec.json" in skill
    assert "review-report-quality.json" in skill
    assert "Two separate reviews are **required**" in skill
    # Must not leave review without artifact
    assert "A review that leaves no `review-report.json` is incomplete" in skill


def test_review_skill_writes_verdict_to_file_not_chat() -> None:
    skill = (ROOT / "skills" / "review" / "SKILL.md").read_text(encoding="utf-8")

    assert "The verdict in the file is the only valid verdict" in skill
    assert "The verdict exists only in the artifact, not in chat sentiment" in skill


def test_clarify_skill_sets_min_verification() -> None:
    skill = (ROOT / "skills" / "clarify" / "SKILL.md").read_text(encoding="utf-8")

    assert "min_verification" in skill
    # Each route should have defined minimum verification
    assert "build" in skill and "lint" in skill and "type_check" in skill
    # min_verification should be in brief output spec
    assert "min_verification: list of required verification steps" in skill


def test_ouroboros_handoff_strengthens_clarify_ambiguity_contract() -> None:
    skill = (ROOT / "skills" / "clarify" / "SKILL.md").read_text(encoding="utf-8")

    assert "Socratic clarification" in skill
    assert "ambiguity score" in skill
    assert "hidden assumptions" in skill
    assert "non-goals" in skill
    assert "blocker questions" in skill


def test_ouroboros_handoff_strengthens_plan_traceability_contract() -> None:
    skill = (ROOT / "skills" / "plan" / "SKILL.md").read_text(encoding="utf-8")

    assert "Assign stable requirement IDs" in skill
    assert "Every acceptance criterion from the brief" in skill
    assert "do not silently create orphan work" in skill
    assert "adapter limitation" in skill


def test_ouroboros_handoff_strengthens_review_evidence_contract() -> None:
    skill = (ROOT / "skills" / "review" / "SKILL.md").read_text(encoding="utf-8")

    assert "blocker-first verdict" in skill
    assert "observed evidence" in skill
    assert "reported evidence" in skill
    assert "uninspected claimed evidence prevents approval" in skill


def test_runtime_adapter_document_captures_backend_boundary() -> None:
    doc = (ROOT / "docs" / "runtime-adapters.md").read_text(encoding="utf-8")

    assert "ForgeFlow keeps workflow contracts separate from execution backends" in doc
    assert "Capability matrix" in doc
    assert "Claude Code" in doc
    assert "Codex" in doc
    assert "Hermes" in doc
    assert "OpenCode" in doc
