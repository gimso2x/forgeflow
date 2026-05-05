import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "scripts" / "codex_plugin_doctor.py"


def run_doctor(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(DOCTOR), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_plugin_root(path: Path) -> None:
    (path / ".codex-plugin").mkdir(parents=True)
    (path / "skills").mkdir()
    (path / ".codex-plugin" / "plugin.json").write_text('{"name":"forgeflow"}\n', encoding="utf-8")


def test_codex_plugin_doctor_reports_pass_for_installed_marketplace_and_project(tmp_path):
    plugin_root = tmp_path / "plugins" / "forgeflow"
    marketplace = tmp_path / ".agents" / "plugins" / "marketplace.json"
    project = tmp_path / "project"
    _write_plugin_root(plugin_root)
    marketplace.parent.mkdir(parents=True)
    marketplace.write_text(
        json.dumps({"plugins": [{"name": "forgeflow", "source": {"source": "local", "path": "./plugins/forgeflow"}}]}) + "\n",
        encoding="utf-8",
    )
    project.mkdir()
    (project / ".forgeflow").mkdir()
    (project / ".codex" / "forgeflow").mkdir(parents=True)
    (project / "CODEX.md").write_text("Use .forgeflow/tasks/<task-id>/ and update run-state.json.\n", encoding="utf-8")

    result = run_doctor(
        "--marketplace-path",
        str(marketplace),
        "--plugin-root",
        str(plugin_root),
        "--project",
        str(project),
        "--json",
    )

    assert result.returncode in {0, 1}
    payload = json.loads(result.stdout)
    by_name = {check["name"]: check for check in payload["checks"]}
    assert by_name["marketplace"]["status"] == "PASS"
    assert by_name["plugin_root"]["status"] == "PASS"
    assert by_name["project_CODEX"]["status"] == "PASS"
    assert by_name["artifact_policy"]["status"] == "PASS"


def test_codex_plugin_doctor_fails_missing_marketplace_and_plugin_root(tmp_path):
    result = run_doctor(
        "--marketplace-path",
        str(tmp_path / "missing-marketplace.json"),
        "--plugin-root",
        str(tmp_path / "missing-plugin"),
    )

    assert result.returncode == 1
    assert "ForgeFlow Codex doctor: FAIL" in result.stdout
    assert "[FAIL] marketplace" in result.stdout
    assert "[FAIL] plugin_root" in result.stdout
