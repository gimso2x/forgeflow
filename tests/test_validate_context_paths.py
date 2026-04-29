import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_context_paths.py"


def _load_validator_module():
    spec = importlib.util.spec_from_file_location("validate_context_paths", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_context_path_validator_passes_current_repo() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_context_paths.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "CONTEXT PATH VALIDATION: PASS" in result.stdout


def test_context_path_validator_reports_broken_repo_local_refs(tmp_path: Path) -> None:
    validator = _load_validator_module()
    (tmp_path / "README.md").write_text(
        "Use `docs/missing-guide.md`, but `/path/to/your-project/CLAUDE.md` is an install target.\n",
        encoding="utf-8",
    )

    broken = validator.find_broken_references(tmp_path)

    assert [item.render() for item in broken] == ["README.md:1: docs/missing-guide.md"]


def test_context_path_validator_reports_broken_hidden_dir_refs(tmp_path: Path) -> None:
    validator = _load_validator_module()
    (tmp_path / "README.md").write_text(
        "CI lives in `.github/workflows/missing.yml`.\n",
        encoding="utf-8",
    )

    broken = validator.find_broken_references(tmp_path)

    assert [item.render() for item in broken] == ["README.md:1: .github/workflows/missing.yml"]


def test_context_path_validator_ignores_url_paths(tmp_path: Path) -> None:
    validator = _load_validator_module()
    (tmp_path / "README.md").write_text(
        "Install with https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py.\n"
        "Docs live at https://example.com/docs/guide.md.\n",
        encoding="utf-8",
    )

    assert validator.find_broken_references(tmp_path) == []


def test_context_path_validator_accepts_existing_hidden_dir_refs(tmp_path: Path) -> None:
    validator = _load_validator_module()
    workflow = tmp_path / ".github" / "workflows" / "validate.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("name: validate\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "CI lives in `.github/workflows/validate.yml`.\n",
        encoding="utf-8",
    )

    assert validator.find_broken_references(tmp_path) == []


def test_context_path_validator_ignores_generated_and_upstream_context(tmp_path: Path) -> None:
    validator = _load_validator_module()
    generated = tmp_path / "adapters" / "generated" / "claude"
    upstream = tmp_path / "docs" / "upstream" / "hoyeon"
    generated.mkdir(parents=True)
    upstream.mkdir(parents=True)
    (generated / "CLAUDE.md").write_text("Broken `adapters/nope.md`.\n", encoding="utf-8")
    (upstream / "README.md").write_text("Broken `skills/nope/SKILL.md`.\n", encoding="utf-8")

    assert validator.find_broken_references(tmp_path) == []
