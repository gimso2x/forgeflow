import os
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap_codex_plugin.py"


def make_fake_release_archive(tmp_path: Path) -> Path:
    source = tmp_path / "forgeflow-main"
    installer = source / "scripts" / "install_codex_plugin.py"
    installer.parent.mkdir(parents=True)
    installer.write_text(
        "\n".join(
            [
                "import json",
                "import os",
                "import sys",
                "from pathlib import Path",
                "record = Path(os.environ['FORGEFLOW_BOOTSTRAP_RECORD'])",
                "record.write_text(json.dumps({'cwd': os.getcwd(), 'argv': sys.argv[1:]}), encoding='utf-8')",
                "print('fake installer ran')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    archive = tmp_path / "forgeflow.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in source.rglob("*"):
            zf.write(path, path.relative_to(tmp_path))
    return archive


def test_codex_bootstrap_downloads_archive_and_runs_repo_installer(tmp_path):
    archive = make_fake_release_archive(tmp_path)
    record = tmp_path / "record.json"
    env = {**os.environ, "FORGEFLOW_BOOTSTRAP_RECORD": str(record)}

    result = subprocess.run(
        [
            sys.executable,
            str(BOOTSTRAP),
            "--archive-url",
            archive.as_uri(),
            "--",
            "--force",
            "--plugin-parent",
            str(tmp_path / "plugins"),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "fake installer ran" in result.stdout
    payload = __import__("json").loads(record.read_text(encoding="utf-8"))
    assert payload["argv"] == ["--force", "--plugin-parent", str(tmp_path / "plugins")]
    assert payload["cwd"].endswith("forgeflow-main")


def test_codex_bootstrap_passes_installer_flags_without_separator(tmp_path):
    archive = make_fake_release_archive(tmp_path)
    record = tmp_path / "record.json"
    env = {**os.environ, "FORGEFLOW_BOOTSTRAP_RECORD": str(record)}

    result = subprocess.run(
        [
            sys.executable,
            str(BOOTSTRAP),
            "--archive-url",
            archive.as_uri(),
            "--force",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = __import__("json").loads(record.read_text(encoding="utf-8"))
    assert payload["argv"] == ["--force"]


def test_install_docs_offer_clone_free_codex_bootstrap_command():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    codex_guide = (ROOT / "docs" / "guides" / "codex.md").read_text(encoding="utf-8")
    codex_desktop = (ROOT / "docs" / "codex-desktop.md").read_text(encoding="utf-8")
    scripts_readme = (ROOT / "scripts" / "README.md").read_text(encoding="utf-8")
    windows_doc = (ROOT / "docs" / "windows.md").read_text(encoding="utf-8")
    windows_guide = (ROOT / "docs" / "guides" / "windows.md").read_text(encoding="utf-8")

    bootstrap = "curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py"
    dry_run_command = f"{bootstrap} | python3 - --dry-run"
    force_command = f"{bootstrap} | python3 - --force"
    powershell_force_command = (
        "irm https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py "
        "| python - --force"
    )
    assert dry_run_command in readme
    assert force_command in readme
    assert dry_run_command in install
    assert force_command in install
    assert powershell_force_command in install
    assert force_command in scripts_readme
    assert force_command in codex_guide
    assert force_command in codex_desktop
    assert powershell_force_command in codex_guide
    assert powershell_force_command in codex_desktop
    assert powershell_force_command in windows_doc
    assert powershell_force_command in windows_guide
    assert "python3 - -- --force" not in codex_guide
    assert "python3 - -- --force" not in codex_desktop
    assert "python - -- --force" not in codex_guide
    assert "python - -- --force" not in codex_desktop
    assert "python3 - -- --dry-run" not in scripts_readme
    assert "python - -- --dry-run" not in scripts_readme
    assert "python - -- --dry-run" not in windows_doc
    assert "python - -- --dry-run" not in windows_guide
    assert "--force deletes ~/plugins/forgeflow" in install
