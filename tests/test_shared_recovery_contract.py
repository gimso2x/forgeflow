from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "policy/canonical/recovery.yaml"
GENERATED = {
    "claude": ROOT / "adapters/generated/claude/CLAUDE.md",
    "codex": ROOT / "adapters/generated/codex/CODEX.md",
}
MANIFESTS = {
    "claude": ROOT / "adapters/targets/claude/manifest.yaml",
    "codex": ROOT / "adapters/targets/codex/manifest.yaml",
}
DELIVERY_NOTES = {
    "claude": "Claude may deliver recovery through optional adapter hooks plus generated instructions.",
    "codex": "Codex delivers recovery through CODEX.md instruction guidance, not hooks.",
}

def shared_rules() -> list[str]:
    text = CONTRACT.read_text(encoding="utf-8")
    return [line.removeprefix("  - ") for line in text.splitlines() if line.startswith("  - ")]


def test_canonical_recovery_contract_exists_with_required_rules():
    text = CONTRACT.read_text(encoding="utf-8")
    rules = shared_rules()
    assert "title: ForgeFlow Recovery Contract" in text
    assert rules
    for rule in rules:
        assert rule in text


def test_generated_adapters_include_shared_recovery_contract():
    for target, path in GENERATED.items():
        text = path.read_text(encoding="utf-8")
        assert "## Recovery contract" in text, target
        for rule in shared_rules():
            assert rule in text, f"{target} missing {rule}"


def test_adapter_delivery_notes_stay_target_specific():
    for target, note in DELIVERY_NOTES.items():
        manifest = MANIFESTS[target].read_text(encoding="utf-8")
        generated = GENERATED[target].read_text(encoding="utf-8")
        assert note in manifest
        assert note in generated


def test_tooling_constraints_do_not_duplicate_recovery_contract_sections():
    for target, path in MANIFESTS.items():
        text = path.read_text(encoding="utf-8")
        tooling_block = text.split("tooling_constraints:", 1)[1]
        generated = GENERATED[target].read_text(encoding="utf-8")
        assert f"{target.title()} recovery guidance" not in tooling_block
        for rule in shared_rules():
            assert rule not in tooling_block, f"{target} duplicates canonical recovery rule: {rule}"
            assert generated.count(rule) == 1, f"{target} should render canonical recovery rule exactly once: {rule}"
