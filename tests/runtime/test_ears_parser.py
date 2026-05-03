from __future__ import annotations

import pytest

from forgeflow_runtime.ears_parser import EARSType, Requirement, parse_ears


# ── helpers ────────────────────────────────────────────────────────────

def _ids(reqs: list[Requirement]) -> list[str]:
    return [r.id for r in reqs]


def _types(reqs: list[Requirement]) -> list[EARSType]:
    return [r.ears_type for r in reqs]


# ── pattern tests ─────────────────────────────────────────────────────

class TestOptionalPattern:
    def test_basic_optional(self) -> None:
        text = "The system SHALL optional provide an export feature."
        reqs = parse_ears(text)
        assert len(reqs) == 1
        assert reqs[0].ears_type is EARSType.OPTIONAL

    def test_optional_with_must(self) -> None:
        text = "The system MUST optional support dark mode."
        reqs = parse_ears(text)
        assert reqs[0].ears_type is EARSType.OPTIONAL


class TestEventDrivenPattern:
    def test_basic_event_driven(self) -> None:
        text = "WHEN the user clicks submit THEN the system SHALL save the form."
        reqs = parse_ears(text)
        assert len(reqs) == 1
        assert reqs[0].ears_type is EARSType.EVENT_DRIVEN

    def test_event_driven_with_should(self) -> None:
        text = "WHEN the alarm triggers THEN the system should notify the admin."
        reqs = parse_ears(text)
        assert reqs[0].ears_type is EARSType.EVENT_DRIVEN


class TestStateDrivenPattern:
    def test_basic_state_driven(self) -> None:
        text = "WHILE the system is in maintenance mode the system SHALL reject new logins."
        reqs = parse_ears(text)
        assert len(reqs) == 1
        assert reqs[0].ears_type is EARSType.STATE_DRIVEN

    def test_state_driven_with_must(self) -> None:
        text = "WHILE the connection is active the system must keep the heartbeat alive."
        reqs = parse_ears(text)
        assert reqs[0].ears_type is EARSType.STATE_DRIVEN


class TestUnwantedPattern:
    def test_basic_unwanted(self) -> None:
        text = "IF the password is weak THEN the system SHALL reject the login attempt."
        reqs = parse_ears(text)
        assert len(reqs) == 1
        assert reqs[0].ears_type is EARSType.UNWANTED

    def test_unwanted_with_should(self) -> None:
        text = "IF the input is malformed THEN the system should return a 400 error."
        reqs = parse_ears(text)
        assert reqs[0].ears_type is EARSType.UNWANTED


class TestUbiquitousPattern:
    def test_basic_ubiquitous(self) -> None:
        text = "The system SHALL display the dashboard within 2 seconds."
        reqs = parse_ears(text)
        assert len(reqs) == 1
        assert reqs[0].ears_type is EARSType.UBIQUITOUS

    def test_ubiquitous_with_must(self) -> None:
        text = "The system must encrypt all data at rest."
        reqs = parse_ears(text)
        assert reqs[0].ears_type is EARSType.UBIQUITOUS

    def test_korean_ubiquitous_shall(self) -> None:
        text = "시스템은 모든 데이터를 암호화해야 SHALL 한다."
        reqs = parse_ears(text)
        assert len(reqs) == 1
        assert reqs[0].ears_type is EARSType.UBIQUITOUS

    def test_korean_ubiquitous_haeya(self) -> None:
        text = "시스템은 모든 요청을 로깅해야 한다."
        reqs = parse_ears(text)
        assert len(reqs) == 1
        assert reqs[0].ears_type is EARSType.UBIQUITOUS


# ── auto ID generation ────────────────────────────────────────────────

class TestAutoIDGeneration:
    def test_single_requirement(self) -> None:
        reqs = parse_ears("The system SHALL do something.")
        assert _ids(reqs) == ["REQ-001"]

    def test_multiple_requirements(self) -> None:
        text = (
            "The system SHALL do A.\n"
            "WHEN X happens THEN the system SHALL do B.\n"
            "The system must do C."
        )
        reqs = parse_ears(text)
        assert _ids(reqs) == ["REQ-001", "REQ-002", "REQ-003"]

    def test_ids_reset_per_call(self) -> None:
        parse_ears("The system SHALL X.")
        reqs = parse_ears("The system SHALL Y.")
        assert _ids(reqs) == ["REQ-001"]


# ── mixed input with unknown lines ────────────────────────────────────

class TestMixedInput:
    def test_unknown_lines(self) -> None:
        text = (
            "The system SHALL display results.\n"
            "Something completely random and unrecognized.\n"
            "WHILE idle the system SHALL sleep."
        )
        reqs = parse_ears(text)
        assert _types(reqs) == [
            EARSType.UBIQUITOUS,
            EARSType.UNKNOWN,
            EARSType.STATE_DRIVEN,
        ]

    def test_all_unknown(self) -> None:
        text = "This is just a plain sentence.\nAnother plain line."
        reqs = parse_ears(text)
        assert all(r.ears_type is EARSType.UNKNOWN for r in reqs)
        assert len(reqs) == 2


# ── empty / blank input ───────────────────────────────────────────────

class TestEmptyInput:
    def test_empty_string(self) -> None:
        assert parse_ears("") == []

    def test_whitespace_only(self) -> None:
        assert parse_ears("   \n  \n\t\n") == []

    def test_only_comments(self) -> None:
        assert parse_ears("# comment\n# another") == []


# ── comment skipping ──────────────────────────────────────────────────

class TestCommentSkipping:
    def test_comments_between_requirements(self) -> None:
        text = (
            "# Header comment\n"
            "The system SHALL do A.\n"
            "# Inline comment\n"
            "The system must do B.\n"
        )
        reqs = parse_ears(text)
        assert len(reqs) == 2
        assert _ids(reqs) == ["REQ-001", "REQ-002"]

    def test_comment_not_counted_in_ids(self) -> None:
        text = (
            "# skip me\n"
            "The system SHALL X.\n"
            "# skip me too\n"
            "The system SHALL Y.\n"
        )
        reqs = parse_ears(text)
        assert _ids(reqs) == ["REQ-001", "REQ-002"]


# ── Requirement dataclass ─────────────────────────────────────────────

class TestRequirementDataclass:
    def test_raw_line_preserved(self) -> None:
        text = "  The system SHALL trim this.  "
        reqs = parse_ears(text)
        assert reqs[0].raw_line == text
        assert reqs[0].description == "The system SHALL trim this."

    def test_frozen(self) -> None:
        reqs = parse_ears("The system SHALL X.")
        with pytest.raises(AttributeError):
            reqs[0].id = "REQ-999"  # type: ignore[misc]
