from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_upstream_import_validation_accepts_committed_mirror_without_source(monkeypatch, capsys) -> None:
    validator = _load_module(ROOT / "scripts" / "validate_upstream_import.py", "validate_upstream_import")

    monkeypatch.setattr(validator, "SOURCE", ROOT / "definitely-missing-upstream-source")

    assert validator.main() == 0
    output = capsys.readouterr().out
    assert "UPSTREAM IMPORT VALIDATION: PASS" in output
    assert "source unavailable; checked committed mirror only" in output


def test_hoyeon_import_validation_accepts_committed_mirror_without_source(monkeypatch, capsys) -> None:
    validator = _load_module(ROOT / "scripts" / "validate_hoyeon_import.py", "validate_hoyeon_import")

    monkeypatch.setattr(validator, "CANDIDATE_SOURCES", [ROOT / "definitely-missing-hoyeon-source"])

    assert validator.main() == 0
    output = capsys.readouterr().out
    assert "HOYEON IMPORT VALIDATION: PASS" in output
    assert "source unavailable; checked committed mirror only" in output
