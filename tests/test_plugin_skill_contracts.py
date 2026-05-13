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
    assert "output exactly one of `small`, `medium`, or `high`" in skill
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


def test_canonical_forgeflow_skills_default_to_artifact_first_mode() -> None:
    for skill_name in ["forgeflow", "clarify", "plan", "execute", "review", "ship"]:
        skill = (ROOT / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")

        assert "Default to **artifact-first mode**." in skill


def test_stage_skills_absorb_karpathy_discipline_without_new_stage() -> None:
    clarify = (ROOT / "skills" / "clarify" / "SKILL.md").read_text(encoding="utf-8")
    plan = (ROOT / "skills" / "plan" / "SKILL.md").read_text(encoding="utf-8")
    execute = (ROOT / "skills" / "execute" / "SKILL.md").read_text(encoding="utf-8")
    review = (ROOT / "skills" / "review" / "SKILL.md").read_text(encoding="utf-8")
    index = (ROOT / "skills" / "SKILLS.md").read_text(encoding="utf-8")

    assert "Surface confusion instead of guessing" in clarify
    assert "Do not silently pick one interpretation" in clarify
    assert "State assumptions and success criteria before proposing tasks" in plan
    assert "Prefer the smallest implementation that satisfies the acceptance criteria" in execute
    assert "Nothing speculative" in execute
    assert "Every changed line should trace directly to the user's request" in review
    assert "drive-by refactors" in review
    assert "andrej-karpathy-skills" in index
    assert "new canonical stage" not in index.lower()
    assert "Optional discipline, debugging, QA, and learning guidance belongs in docs" in index


def test_codex_plugin_accepts_forgeflow_slash_style_prompts() -> None:
    forgeflow = (ROOT / "skills" / "forgeflow" / "SKILL.md").read_text(encoding="utf-8")
    assert "Codex exposes plugin skills" in forgeflow

    expected = {
        "init": "/forgeflow:init",
        "clarify": "/forgeflow:clarify",
        "plan": "/forgeflow:plan",
        "execute": "/forgeflow:execute",
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
    skill = (ROOT / "skills" / "execute" / "SKILL.md").read_text(encoding="utf-8")

    assert "Route-aware exit requirements" in skill
    assert "run-state.json" in skill
    # Each route should have specific exit guidance
    assert "**small** route" in skill
    assert "**medium** route" in skill
    assert "**high** route" in skill
    # high must auto-chain to review
    assert "high route 실행 완료" in skill
    assert "/forgeflow:review를 자동으로 시작합니다" in skill
    # Must not end without run-state.json
    assert "Do not end the execute stage without writing `run-state.json`" in skill


def test_run_skill_initializes_run_state_before_editing() -> None:
    skill = (ROOT / "skills" / "execute" / "SKILL.md").read_text(encoding="utf-8")

    assert "Initialize `run-state.json`" in skill
    assert "current_stage: \"execute\"" in skill
    assert "status: \"in_progress\"" in skill


def test_forgeflow_stage_skills_support_non_interactive_approval_mode() -> None:
    for rel in [
        "skills/plan/SKILL.md",
        "skills/execute/SKILL.md",
        "skills/review/SKILL.md",
        ".claude-plugin/skills/plan.md",
        ".claude-plugin/skills/execute.md",
        ".claude-plugin/skills/review.md",
    ]:
        skill = (ROOT / rel).read_text(encoding="utf-8")
        assert "Automation / non-interactive approval mode" in skill
        assert "--auto-approve" in skill
        assert "--non-interactive" in skill
        assert "Do not pause at the normal stage-boundary y/n prompt" in skill


def test_worker_prompts_require_bounded_verification_fix_loop() -> None:
    for rel in [
        "skills/execute/SKILL.md",
        ".claude-plugin/skills/execute.md",
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


def test_claude_execute_surface_handles_worktree_preference() -> None:
    for rel in [
        ".claude-plugin/skills/execute.md",
        "adapters/targets/claude/agents/forgeflow-worker.md",
    ]:
        prompt = (ROOT / rel).read_text(encoding="utf-8")
        assert "Worktree isolation preference" in prompt
        assert "use_worktree" in prompt
        assert "worktree preference not set — ask user" in prompt
        assert "brief.json" in prompt
        assert "re-run `/forgeflow:execute`" in prompt


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
    assert "**high** route" in skill
    # high must produce separate spec + quality reports
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


def test_harness_absorption_decision_records_forgeflow_boundary() -> None:
    decision = (ROOT / "docs" / "decisions" / "0002-harness-absorption-boundary.md").read_text(
        encoding="utf-8"
    )
    task = (ROOT / "docs" / "tasks" / "2026-05-08-harness-absorption-reflection.md").read_text(
        encoding="utf-8"
    )

    for required_text in [
        "task instructions, status, and logs in one orchestration surface",
        "sample smoke or fixture",
        "reusable skills, templates, runtime modules, or contract tests",
        "No parallel workflow engine",
        "No hidden chat-memory source of truth",
        "No wholesale copy of external harness directory structures",
    ]:
        assert required_text in decision

    assert "Status: completed" in task
    assert "Obsidian: `Inbox/2026-05-08 [개발전] 하네스 흡수 반영.md`" in task
    assert "Hermes Follow-up Boundary" in task
