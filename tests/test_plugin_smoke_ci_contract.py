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
    ]:
        assert required in smoke


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
