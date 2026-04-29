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

    command = "curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - -- --force"
    assert command in readme
    assert command in install
