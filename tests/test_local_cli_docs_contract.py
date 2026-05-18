import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
INSTALL = ROOT / "INSTALL.md"
CLI_REFERENCE = ROOT / "docs" / "reference" / "cli.md"
PYPROJECT = ROOT / "pyproject.toml"


def _console_scripts() -> dict[str, str]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return data["project"]["scripts"]


def test_local_cli_docs_reference_packaged_console_scripts() -> None:
    scripts = _console_scripts()
    docs = {
        "README.md": README.read_text(encoding="utf-8"),
        "INSTALL.md": INSTALL.read_text(encoding="utf-8"),
        "docs/reference/cli.md": CLI_REFERENCE.read_text(encoding="utf-8"),
    }

    assert scripts["forgeflow"] == scripts["forgeflow-runtime"]
    for name, text in docs.items():
        assert "forgeflow" in text, name
        assert "forgeflow-runtime" in text, name


def test_local_cli_quickstart_help_commands_use_packaged_entrypoints() -> None:
    scripts = set(_console_scripts())
    combined = README.read_text(encoding="utf-8") + "\n" + INSTALL.read_text(encoding="utf-8")
    help_commands = set(re.findall(r"^\s*(forgeflow(?:-runtime)?) --help\s*$", combined, flags=re.MULTILINE))

    assert help_commands
    assert help_commands <= scripts
