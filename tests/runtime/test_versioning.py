from __future__ import annotations

import pytest

from forgeflow_runtime.versioning import (
    ChangelogEntry,
    SemVer,
    bump_major,
    bump_minor,
    bump_patch,
    classify_change,
    format_changelog,
    parse_semver,
    semver_to_string,
    suggest_next_version,
)


# -- parse_semver --


def test_parse_semver_basic() -> None:
    result = parse_semver("1.2.3")
    assert result == SemVer(1, 2, 3)


def test_parse_semver_with_prerelease() -> None:
    result = parse_semver("1.2.3-alpha.1")
    assert result == SemVer(1, 2, 3, "alpha.1")


def test_parse_semver_invalid() -> None:
    with pytest.raises(ValueError):
        parse_semver("not-a-version")
    with pytest.raises(ValueError):
        parse_semver("1.2")
    with pytest.raises(ValueError):
        parse_semver("")


# -- semver_to_string --


def test_semver_to_string_roundtrip() -> None:
    assert semver_to_string(parse_semver("1.2.3")) == "1.2.3"
    assert semver_to_string(parse_semver("1.2.3-alpha.1")) == "1.2.3-alpha.1"
    assert semver_to_string(parse_semver("0.0.0")) == "0.0.0"


# -- bump functions --


def test_bump_major_resets() -> None:
    assert bump_major(SemVer(1, 2, 3, "alpha.1")) == SemVer(2, 0, 0)
    assert bump_major(SemVer(0, 5, 9)) == SemVer(1, 0, 0)


def test_bump_minor_resets() -> None:
    assert bump_minor(SemVer(1, 2, 3, "beta")) == SemVer(1, 3, 0)
    assert bump_minor(SemVer(1, 0, 9)) == SemVer(1, 1, 0)


def test_bump_patch_resets_prerelease() -> None:
    assert bump_patch(SemVer(1, 2, 3, "rc.1")) == SemVer(1, 2, 4)
    assert bump_patch(SemVer(0, 0, 0)) == SemVer(0, 0, 1)


# -- classify_change --


def test_classify_change_feat() -> None:
    assert classify_change("feat: add new widget") == "minor"


def test_classify_change_breaking() -> None:
    assert classify_change("feat!: remove old API") == "major"
    assert classify_change("feat: some change\nBREAKING: removed endpoint") == "major"


def test_classify_change_fix() -> None:
    assert classify_change("fix: resolve crash on startup") == "patch"


def test_classify_change_docs() -> None:
    assert classify_change("docs: update README") == "patch"


def test_classify_change_default() -> None:
    assert classify_change("refactor: clean up internals") == "patch"


# -- suggest_next_version --


def test_suggest_next_version_feat_commits() -> None:
    current = SemVer(1, 2, 3)
    result = suggest_next_version(current, ["feat: add search", "fix: typo"])
    assert result == SemVer(1, 3, 0)


def test_suggest_next_version_fix_commits() -> None:
    current = SemVer(1, 2, 3)
    result = suggest_next_version(current, ["fix: null pointer", "docs: readme"])
    assert result == SemVer(1, 2, 4)


def test_suggest_next_version_breaking() -> None:
    current = SemVer(1, 2, 3)
    result = suggest_next_version(current, ["feat!: drop old API", "fix: typo"])
    assert result == SemVer(2, 0, 0)


def test_suggest_next_version_no_commits() -> None:
    current = SemVer(1, 2, 3)
    result = suggest_next_version(current, [])
    assert result == SemVer(1, 2, 4)


# -- format_changelog --


def test_format_changelog_contains_version_and_changes() -> None:
    entries = [
        ChangelogEntry(
            version="1.2.0",
            date="2026-05-03",
            changes=["feat: add search", "fix: crash on load"],
            breaking=["removed legacy endpoint"],
        ),
    ]
    output = format_changelog(entries)
    assert "# Changelog" in output
    assert "[1.2.0] - 2026-05-03" in output
    assert "feat: add search" in output
    assert "fix: crash on load" in output
    assert "removed legacy endpoint" in output
    assert "### Breaking" in output
    assert "### Changed" in output
    assert "### Fixed" in output


# -- SemVer comparison --


def test_semver_lt() -> None:
    assert SemVer(1, 0, 0) < SemVer(2, 0, 0)
    assert SemVer(1, 1, 0) < SemVer(1, 2, 0)
    assert SemVer(1, 1, 1) < SemVer(1, 1, 2)
    assert not (SemVer(2, 0, 0) < SemVer(1, 0, 0))


def test_semver_lt_prerelease() -> None:
    assert SemVer(1, 2, 3, "alpha") < SemVer(1, 2, 3)
    assert SemVer(1, 2, 3, "alpha") < SemVer(1, 2, 3, "beta")
    assert not (SemVer(1, 2, 3) < SemVer(1, 2, 3, "alpha"))


def test_semver_eq() -> None:
    assert SemVer(1, 2, 3) == SemVer(1, 2, 3)
    assert SemVer(1, 2, 3, "alpha") == SemVer(1, 2, 3, "alpha")
    assert SemVer(1, 2, 3) != SemVer(1, 2, 4)
    assert SemVer(1, 2, 3) != SemVer(1, 2, 3, "alpha")
