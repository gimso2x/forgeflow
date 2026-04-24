from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINISH_SKILL = ROOT / "skills" / "finish" / "SKILL.md"
VALIDATOR = ROOT / "scripts" / "validate_skill_contracts.py"


def test_finish_skill_exists_with_four_safe_branch_outcomes():
    text = FINISH_SKILL.read_text(encoding="utf-8")

    assert "name: finish" in text
    assert "Merge locally" in text
    assert "Push and create a Pull Request" in text
    assert "Keep the branch as-is" in text
    assert "Discard this work" in text
    assert "Implementation complete. What would you like to do?" in text


def test_finish_skill_requires_fresh_verification_and_scope_check():
    text = FINISH_SKILL.read_text(encoding="utf-8")

    assert "fresh verification" in text
    assert "git status" in text
    assert "git diff" in text
    assert "review-report" in text
    assert "residual risks" in text


def test_finish_skill_protects_destructive_actions():
    text = FINISH_SKILL.read_text(encoding="utf-8")

    assert "Type 'discard' to confirm" in text
    assert "Never delete" in text
    assert "unrelated dirty working tree" in text


def test_finish_skill_is_part_of_canonical_skill_validation():
    text = VALIDATOR.read_text(encoding="utf-8")

    assert "skills/finish/SKILL.md" in text
