from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "adapters/targets/cursor/manifest.yaml"
GENERATED = ROOT / "adapters/generated/cursor/HARNESS_CURSOR.md"
CONTRACT = ROOT / "policy/canonical/recovery.yaml"
DELIVERY_NOTE = "Cursor delivers recovery through .cursor/rules guidance, not hooks."


def shared_rules() -> list[str]:
    text = CONTRACT.read_text(encoding="utf-8")
    return [line.removeprefix("  - ") for line in text.splitlines() if line.startswith("  - ")]


def test_cursor_manifest_contains_adapter_specific_delivery_note():
    text = MANIFEST.read_text(encoding="utf-8")
    assert DELIVERY_NOTE in text


def test_generated_cursor_adapter_includes_shared_recovery_contract_and_delivery_note():
    text = GENERATED.read_text(encoding="utf-8")
    assert "## Recovery contract" in text
    assert DELIVERY_NOTE in text
    for rule in shared_rules():
        assert rule in text
