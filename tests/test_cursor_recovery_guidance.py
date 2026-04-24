from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "adapters/targets/cursor/manifest.yaml"
GENERATED = ROOT / "adapters/generated/cursor/HARNESS_CURSOR.md"

REQUIRED_PHRASES = [
    "Cursor recovery guidance",
    "After a failed edit or apply, re-read the target file and inspect the diff before retrying",
    "For large files or noisy editor context, use targeted search or chunked reads",
    "After three repeated failures, stop and change strategy before continuing",
    "Chat summaries must not replace required ForgeFlow artifacts",
    "Cursor fast/apply shortcuts must not bypass review gates",
]


def test_cursor_manifest_contains_recovery_guidance_contract():
    text = MANIFEST.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        assert phrase in text


def test_generated_cursor_adapter_includes_recovery_guidance_contract():
    text = GENERATED.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        assert phrase in text
