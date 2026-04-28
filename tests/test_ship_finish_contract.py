from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
INSTALL = ROOT / "INSTALL.md"
SHIP_SKILL = ROOT / "skills" / "ship" / "SKILL.md"
FINISH_SKILL = ROOT / "skills" / "finish" / "SKILL.md"
SKILLS_INDEX = ROOT / "skills" / "SKILLS.md"


def test_readme_and_install_explain_ship_and_finish_lifecycle_boundary():
    combined = README.read_text(encoding="utf-8") + "\n" + INSTALL.read_text(encoding="utf-8")

    assert "/forgeflow:ship" in combined
    assert "/forgeflow:finish" in combined
    assert "handoff" in combined
    assert "disposition" in combined
    assert "merge, PR, keep, or discard" in combined


def test_ship_skill_is_handoff_not_branch_disposition():
    ship_text = SHIP_SKILL.read_text(encoding="utf-8")
    finish_text = FINISH_SKILL.read_text(encoding="utf-8")

    assert "final handoff" in ship_text
    assert "does not merge" in ship_text
    assert "branch disposition" in finish_text
    assert "requires explicit user direction" in finish_text


def test_skills_index_keeps_ship_handoff_separate_from_finish_disposition():
    skills_index = SKILLS_INDEX.read_text(encoding="utf-8")

    assert "ship             → final handoff" in skills_index
    assert "finish           → branch disposition" in skills_index
    assert "ship             → PR + cleanup" not in skills_index
