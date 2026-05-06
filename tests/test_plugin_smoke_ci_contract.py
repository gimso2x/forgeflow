from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"
SMOKE = ROOT / "scripts" / "ci_plugin_smoke_matrix.py"
README = ROOT / "README.md"


def test_validate_workflow_has_plugin_smoke_matrix_job() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "plugin-smoke-matrix:" in workflow
    assert "os: [ubuntu-latest, windows-latest]" in workflow
    assert "surface: [claude, codex]" in workflow
    assert "route_label: [small, medium, large_high_risk]" in workflow
    assert "scripts/ci_plugin_smoke_matrix.py" in workflow


def test_ci_plugin_smoke_script_documents_non_mutating_route_matrix() -> None:
    smoke = SMOKE.read_text(encoding="utf-8")
    for required in [
        "small",
        "medium",
        "large_high_risk",
        "project_snapshot",
        "git status --short",
        "install_agent_presets.py",
        "codex_plugin_doctor.py",
        "smoke_codex_plugin.py",
        "smoke_claude_plugin.py",
        "Final answer must be exactly one label and nothing else: no prefix, no rationale, no dry-run note.",
        "nothing else: no prefix, no rationale, no dry-run note.",
    ]:
        assert required in smoke


def test_coordinator_rejects_adapter_synonyms_for_route_labels() -> None:
    coordinator = (ROOT / "prompts" / "canonical" / "coordinator.md").read_text(encoding="utf-8")
    codex = (ROOT / "adapters" / "generated" / "codex" / "CODEX.md").read_text(encoding="utf-8")

    for text in [coordinator, codex]:
        assert "ForgeFlow route labels are exactly `small`, `medium`, and `large_high_risk`" in text
        assert "adapter/team-size synonyms" in text
        assert "`solo`" in text


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
