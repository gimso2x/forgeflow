from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"
SMOKE = ROOT / "scripts" / "ci_plugin_smoke_matrix.py"
REAL_E2E = ROOT / "scripts" / "real_plugin_e2e.py"
README = ROOT / "README.md"


def test_validate_workflow_has_plugin_smoke_matrix_job() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "plugin-smoke-matrix:" in workflow
    assert "os: [ubuntu-latest, windows-latest]" in workflow
    assert "surface: [claude, codex]" in workflow
    assert "route_label: [small, medium, high]" in workflow
    assert "scripts/ci_plugin_smoke_matrix.py" in workflow


def test_validate_workflow_opts_into_node24_actions_runtime() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true" in workflow


def test_ci_plugin_smoke_script_documents_non_mutating_route_matrix() -> None:
    smoke = SMOKE.read_text(encoding="utf-8")
    for required in [
        "small",
        "medium",
        "high",
        "project_snapshot",
        "git status --short",
        "install_agent_presets.py",
        "codex_plugin_doctor.py",
        "smoke_codex_plugin.py",
        "smoke_claude_plugin.py",
        "Final answer must be exactly {route_label} and nothing else: no prefix, no rationale, no dry-run note.",
        "nothing else: no prefix, no rationale, no dry-run note.",
    ]:
        assert required in smoke


def test_coordinator_rejects_adapter_synonyms_for_route_labels() -> None:
    coordinator = (ROOT / "prompts" / "canonical" / "coordinator.md").read_text(encoding="utf-8")
    codex = (ROOT / "adapters" / "generated" / "codex" / "CODEX.md").read_text(encoding="utf-8")
    codex_project_coordinator = (ROOT / "adapters" / "targets" / "codex" / "agents" / "forgeflow-coordinator.md").read_text(encoding="utf-8")

    for text in [coordinator, codex, codex_project_coordinator]:
        assert "ForgeFlow route labels are exactly `small`, `medium`, and `high`" in text
        assert "adapter/team-size synonyms" in text
        assert "`solo`" in text


def test_plugin_smoke_prompts_block_non_canonical_route_labels() -> None:
    smoke = SMOKE.read_text(encoding="utf-8")
    assert "Valid labels: small, medium, high." in smoke
    assert "Invalid answers: solo, team, pipeline, supervisor, security review." in smoke
    assert "Do not translate route labels." in smoke
    assert "Final answer must be exactly {route_label}" in smoke


def test_readme_documents_local_disposable_nextjs_plugin_smoke() -> None:
    readme = README.read_text(encoding="utf-8")
    for required in [
        "Plugin smoke matrix",
        "npx create-next-app@latest",
        "scripts/ci_plugin_smoke_matrix.py --surface codex --route-label medium",
        "scripts/ci_plugin_smoke_matrix.py --surface claude --route-label small",
        "non-mutating",
    ]:
        assert required in readme


def test_real_plugin_e2e_documents_mutating_live_agent_boundary() -> None:
    script = REAL_E2E.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    scripts_readme = (ROOT / "scripts" / "README.md").read_text(encoding="utf-8")

    for required in [
        "TASKS",
        "small",
        "medium",
        "high",
        "needle.casefold() not in text.casefold()",
        "--dangerously-bypass-approvals-and-sandbox",
        "RTM_NEWADDR: Operation not permitted",
        "Do not copy this flag into real user repos",
    ]:
        assert required in script

    for text in [readme, scripts_readme]:
        assert "real_plugin_e2e.py" in text
        assert "bubblewrap" in text
        assert "disposable" in text


def test_make_validate_is_the_single_deterministic_validation_entrypoint() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    scripts_readme = (ROOT / "scripts" / "README.md").read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

    assert "validate: check-env" in makefile
    assert "scripts/ci_plugin_smoke_matrix.py" in makefile
    assert "smoke-claude-plugin:" in makefile
    assert "make setup\nmake validate" in install
    assert "make check-env\nmake validate" not in install
    assert "make setup\nmake validate" in scripts_readme
    assert "make check-env\nmake validate" not in scripts_readme
    assert "deterministic validation entry point" in install
    assert "live smoke" in install
    assert "make smoke-claude-plugin" in install


def test_post_install_smoke_entrypoint_is_documented_and_actionable() -> None:
    smoke = ROOT / "scripts" / "smoke.sh"
    assert smoke.exists()
    text = smoke.read_text(encoding="utf-8")
    for required in [
        "CLAUDE PLUGIN POST-INSTALL SMOKE: PASS",
        ".claude-plugin/plugin.json",
        "adapters/generated/claude/CLAUDE.md",
        "Valid labels: small, medium, high",
        "scripts/smoke_claude_plugin.py",
        "claude plugin validate",
        "reinstall/restart",
    ]:
        assert required in text

    readme = README.read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    for text in [readme, install]:
        assert "scripts/smoke.sh" in text
        assert "post-install" in text.lower()


def test_current_user_facing_docs_use_execute_and_high_labels() -> None:
    current_docs = [
        ROOT / "README.md",
        ROOT / "INSTALL.md",
        ROOT / "SKILL.md",
        ROOT / "AGENTS.md",
        ROOT / "docs" / "runtime-adapters.md",
        ROOT / "docs" / "architecture.md",
        ROOT / "docs" / "artifact-model.md",
        ROOT / "docs" / "checkpoint-model.md",
        ROOT / "docs" / "workflow.md",
        ROOT / ".claude-plugin" / "skills" / "clarify.md",
        ROOT / "skills" / "execute" / "SKILL.md",
        ROOT / "skills" / "plan" / "SKILL.md",
    ]
    forbidden_live_route_phrases = [
        "large_high_risk",
        "route=large",
        "Route `medium` or `large`",
        "`large` route",
        "large route",
        "medium/large route",
        "medium/large routes",
        "small/medium/large",
        "clarify → run",
        "plan → run",
    ]
    for path in current_docs:
        text = path.read_text(encoding="utf-8")
        for phrase in forbidden_live_route_phrases:
            assert phrase not in text, f"{path} contains stale live route vocabulary: {phrase}"
        if path.name == "SKILL.md" and "skills/execute" in path.as_posix():
            assert "execute stage" in text
            assert "run stage" not in text
