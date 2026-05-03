from __future__ import annotations

import re
from dataclasses import dataclass

_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([a-zA-Z0-9.]+))?$"
)

_BUMP_PRIORITY = {"major": 3, "minor": 2, "patch": 1}


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: str | None = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __lt__(self, other: SemVer) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        # prerelease versions sort before release
        if self.prerelease is None and other.prerelease is not None:
            return False
        if self.prerelease is not None and other.prerelease is None:
            return True
        if self.prerelease is not None and other.prerelease is not None:
            return self.prerelease < other.prerelease
        return False


def parse_semver(version_string: str) -> SemVer:
    match = _SEMVER_RE.match(version_string.strip())
    if not match:
        raise ValueError(f"Invalid semver format: {version_string!r}")
    return SemVer(
        major=int(match.group(1)),
        minor=int(match.group(2)),
        patch=int(match.group(3)),
        prerelease=match.group(4),
    )


def semver_to_string(ver: SemVer) -> str:
    base = f"{ver.major}.{ver.minor}.{ver.patch}"
    if ver.prerelease:
        base += f"-{ver.prerelease}"
    return base


def bump_major(ver: SemVer) -> SemVer:
    return SemVer(major=ver.major + 1, minor=0, patch=0)


def bump_minor(ver: SemVer) -> SemVer:
    return SemVer(major=ver.major, minor=ver.minor + 1, patch=0)


def bump_patch(ver: SemVer) -> SemVer:
    return SemVer(major=ver.major, minor=ver.minor, patch=ver.patch + 1)


@dataclass(frozen=True)
class ChangelogEntry:
    version: str
    date: str
    changes: list[str]
    breaking: list[str]


def classify_change(commit_message: str) -> str:
    msg = commit_message.strip()
    if msg.startswith("feat!") or "BREAKING" in msg:
        return "major"
    if msg.startswith("feat"):
        return "minor"
    if msg.startswith("fix"):
        return "patch"
    if msg.startswith(("docs", "chore", "test")):
        return "patch"
    return "patch"


def suggest_next_version(current: SemVer, commit_messages: list[str]) -> SemVer:
    highest = "patch"
    for msg in commit_messages:
        bump = classify_change(msg)
        if _BUMP_PRIORITY[bump] > _BUMP_PRIORITY[highest]:
            highest = bump
    if highest == "major":
        return bump_major(current)
    if highest == "minor":
        return bump_minor(current)
    return bump_patch(current)


def format_changelog(entries: list[ChangelogEntry]) -> str:
    lines = ["# Changelog", ""]
    for entry in entries:
        lines.append(f"## [{entry.version}] - {entry.date}")
        lines.append("")
        if entry.breaking:
            lines.append("### Breaking")
            for item in entry.breaking:
                lines.append(f"- {item}")
            lines.append("")
        changed = [c for c in entry.changes if not c.startswith("fix")]
        fixed = [c for c in entry.changes if c.startswith("fix")]
        if changed:
            lines.append("### Changed")
            for item in changed:
                lines.append(f"- {item}")
            lines.append("")
        if fixed:
            lines.append("### Fixed")
            for item in fixed:
                lines.append(f"- {item}")
            lines.append("")
    return "\n".join(lines)
