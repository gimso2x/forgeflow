from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY_SKILL = ROOT / "skills" / "verify" / "SKILL.md"
VALIDATOR = ROOT / "scripts" / "validate_skill_contracts.py"


def test_verify_skill_exists_and_defines_fresh_evidence_gate():
    text = VERIFY_SKILL.read_text(encoding="utf-8")

    assert "name: verify" in text
    assert "NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE" in text
    assert "fresh command output" in text
    assert "exit code" in text
    assert "artifact" in text
    assert "gate" in text


def test_verify_skill_requires_independent_subagent_verification():
    text = VERIFY_SKILL.read_text(encoding="utf-8")

    assert "Subagent reports are not evidence" in text
    assert "git diff" in text
    assert "run the relevant verification command" in text


def test_verify_skill_is_part_of_canonical_skill_validation():
    text = VALIDATOR.read_text(encoding="utf-8")

    assert "skills/verify/SKILL.md" in text
