from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_vocabulary_drift.py"


def test_vocabulary_drift_validator_exists_and_is_wired_into_make_validate_structure() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert SCRIPT.exists()
    assert "scripts/validate_vocabulary_drift.py" in makefile


def test_validator_scans_gemini_and_current_concept_docs() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for required in [
        "adapters/targets/gemini/agents/forgeflow-coordinator.md",
        "docs/implementation-plan.md",
        "docs/concepts/route-model.md",
        "docs/concepts/review-model.md",
        "schema_version 0.1",
        "legacy/example",
        "medium/large",
    ]:
        assert required in text


def test_validator_has_no_current_route_vocabulary_exceptions() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "FORBIDDEN_ROUTE_PHRASE_EXCEPTIONS" not in text
    assert '\"large_high_risk\": {\"README.md\", \"INSTALL.md\"}' not in text
