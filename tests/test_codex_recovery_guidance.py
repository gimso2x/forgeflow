from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "adapters/targets/codex/manifest.yaml"
GENERATED = ROOT / "adapters/generated/codex/CODEX.md"

REQUIRED_PHRASES = [
    "Codex recovery guidance",
    "After an edit/write failure, re-read the target file before retrying",
    "For large files or oversized output, use targeted search or chunked reads",
    "After three repeated command or tool failures, stop and change strategy",
    "Speed shortcuts such as /fast must not skip artifact gates",
]


def test_codex_manifest_contains_recovery_guidance_contract():
    text = MANIFEST.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        assert phrase in text


def test_generated_codex_adapter_includes_recovery_guidance_contract():
    text = GENERATED.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        assert phrase in text
