from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "adapters/targets/codex/manifest.yaml"
GENERATED = ROOT / "adapters/generated/codex/CODEX.md"
CONTRACT = ROOT / "policy/canonical/recovery.yaml"
DELIVERY_NOTE = "Codex delivers recovery through CODEX.md instruction guidance, not hooks."


def shared_rules() -> list[str]:
    text = CONTRACT.read_text(encoding="utf-8")
    return [line.removeprefix("  - ") for line in text.splitlines() if line.startswith("  - ")]


def test_codex_manifest_contains_adapter_specific_delivery_note():
    text = MANIFEST.read_text(encoding="utf-8")
    assert DELIVERY_NOTE in text


def test_generated_codex_adapter_includes_shared_recovery_contract_and_delivery_note():
    text = GENERATED.read_text(encoding="utf-8")
    assert "## Recovery contract" in text
    assert DELIVERY_NOTE in text
    for rule in shared_rules():
        assert rule in text
