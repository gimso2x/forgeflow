from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
