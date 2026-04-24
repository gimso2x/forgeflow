from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "policy/canonical/recovery.yaml"
GENERATED = {
    "claude": ROOT / "adapters/generated/claude/CLAUDE.md",
    "codex": ROOT / "adapters/generated/codex/CODEX.md",
    "cursor": ROOT / "adapters/generated/cursor/HARNESS_CURSOR.md",
}
MANIFESTS = {
    "claude": ROOT / "adapters/targets/claude/manifest.yaml",
    "codex": ROOT / "adapters/targets/codex/manifest.yaml",
    "cursor": ROOT / "adapters/targets/cursor/manifest.yaml",
}
REQUIRED_RULES = [
    "After an edit/write/apply failure, re-read the target file before retrying.",
    "For large files, noisy context, or oversized output, use targeted search or chunked reads.",
    "After three repeated failures, stop and change strategy before continuing.",
    "Fast/apply shortcuts must not skip artifact gates or review gates.",
    "Chat, terminal, or worker summaries must not replace required ForgeFlow artifacts.",
]
DELIVERY_NOTES = {
    "claude": "Claude may deliver recovery through optional adapter hooks plus generated instructions.",
    "codex": "Codex delivers recovery through CODEX.md instruction guidance, not hooks.",
    "cursor": "Cursor delivers recovery through .cursor/rules guidance, not hooks.",
}


def test_canonical_recovery_contract_exists_with_required_rules():
    text = CONTRACT.read_text(encoding="utf-8")
    assert "title: ForgeFlow Recovery Contract" in text
    for rule in REQUIRED_RULES:
        assert rule in text


def test_generated_adapters_include_shared_recovery_contract():
    for target, path in GENERATED.items():
        text = path.read_text(encoding="utf-8")
        assert "## Recovery contract" in text, target
        for rule in REQUIRED_RULES:
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
        for rule in REQUIRED_RULES:
            assert rule not in tooling_block, f"{target} duplicates canonical recovery rule: {rule}"
            assert generated.count(rule) == 1, f"{target} should render canonical recovery rule exactly once: {rule}"
