"""EARS (Easy Approach to Requirements Syntax) parser.

Parses requirement text line-by-line and classifies each line into one
of the five EARS pattern types, or UNKNOWN if no pattern matches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Final


class EARSType(Enum):
    """Classification of a requirement per the EARS notation."""

    OPTIONAL = "optional"
    EVENT_DRIVEN = "event_driven"
    STATE_DRIVEN = "state_driven"
    UNWANTED = "unwanted"
    UBIQUITOUS = "ubiquitous"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Requirement:
    """A single parsed requirement."""

    id: str
    ears_type: EARSType
    description: str
    raw_line: str


# Keyword variants for the modal verb (case-insensitive in patterns).
_MODAL: Final = r"(?:SHALL|shall|must|should|MUST|SHOULD)"

# Pre-compiled patterns (order matters: more specific patterns first).

# Event-Driven: WHEN … THEN the system SHALL …
_RE_EVENT_DRIVEN = re.compile(
    r"^\s*WHEN\s+.+\s+THEN\s+the\s+system\s+" + _MODAL + r"\b",
    re.IGNORECASE,
)

# State-Driven: WHILE … the system SHALL …
_RE_STATE_DRIVEN = re.compile(
    r"^\s*WHILE\s+.+\s+the\s+system\s+" + _MODAL + r"\b",
    re.IGNORECASE,
)

# Unwanted: IF … THEN the system SHALL …
_RE_UNWANTED = re.compile(
    r"^\s*IF\s+.+\s+THEN\s+the\s+system\s+" + _MODAL + r"\b",
    re.IGNORECASE,
)

# Ubiquitous (Korean): 시스템은 … SHALL …  or  시스템은 … 해야 한다
_RE_KOREAN_UBIQUITOUS = re.compile(
    r"시스템은\s*.+(?:SHALL|shall|해야\s*한다)",
    re.IGNORECASE,
)

# Ubiquitous (English): The system SHALL … (with no WHEN/WHILE/IF prefix)
_RE_UBIQUITOUS = re.compile(
    r"^\s*The\s+system\s+" + _MODAL + r"\b",
    re.IGNORECASE,
)

# Optional: The system SHALL [optional] … — distinguished by containing
# "optional" (case-insensitive) near the modal.
_RE_OPTIONAL = re.compile(
    r"^\s*The\s+system\s+" + _MODAL + r"\s+optional\b",
    re.IGNORECASE,
)


def _classify(line: str) -> EARSType:
    """Return the EARS type for a single non-blank, non-comment line."""
    if _RE_EVENT_DRIVEN.match(line):
        return EARSType.EVENT_DRIVEN
    if _RE_STATE_DRIVEN.match(line):
        return EARSType.STATE_DRIVEN
    if _RE_UNWANTED.match(line):
        return EARSType.UNWANTED
    if _RE_OPTIONAL.match(line):
        return EARSType.OPTIONAL
    if _RE_KOREAN_UBIQUITOUS.match(line):
        return EARSType.UBIQUITOUS
    if _RE_UBIQUITOUS.match(line):
        return EARSType.UBIQUITOUS
    return EARSType.UNKNOWN


def parse_ears(text: str) -> list[Requirement]:
    """Parse *text* into a list of :class:`Requirement` objects.

    Blank lines and lines starting with ``#`` are skipped.
    Requirements that do not match any EARS pattern are assigned
    :attr:`EARSType.UNKNOWN`.  IDs are auto-generated as ``REQ-001``,
    ``REQ-002``, …
    """
    results: list[Requirement] = []
    counter = 0

    for raw in text.splitlines():
        stripped = raw.strip()

        # Skip blank / comment lines
        if not stripped or stripped.startswith("#"):
            continue

        counter += 1
        req_id = f"REQ-{counter:03d}"
        ears_type = _classify(stripped)
        results.append(
            Requirement(
                id=req_id,
                ears_type=ears_type,
                description=stripped,
                raw_line=raw,
            )
        )

    return results
