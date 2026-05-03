"""Anti-rationalization checklists for ForgeFlow stages.

Detects common thought patterns where an LLM might rationalize skipping
required process steps, and provides corrective reality checks.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RationalizationPattern:
    """A known rationalization thought pattern paired with its reality check."""

    thought: str
    reality: str
    stage: str
    severity: str  # "low" | "medium" | "high"


@dataclass(frozen=True)
class AntiRationalizationCheck:
    """Result of scanning text against a single rationalization pattern."""

    pattern: RationalizationPattern
    detected: bool
    context: str


# ---------------------------------------------------------------------------
# Built-in patterns for every pipeline stage
# ---------------------------------------------------------------------------

BUILTIN_PATTERNS: list[RationalizationPattern] = [
    # clarify
    RationalizationPattern(
        thought="요구사항이 너무 명확해서 clarify가 필요 없다",
        reality="명확해 보여도 edge case와 trade-off가 숨어있을 수 있습니다",
        stage="clarify",
        severity="high",
    ),
    RationalizationPattern(
        thought="This is just a simple question",
        reality="Questions are tasks. Check for skills first.",
        stage="clarify",
        severity="medium",
    ),
    # plan
    RationalizationPattern(
        thought="너무 간단한 작업이라 plan이 필요 없다",
        reality="단순성 ≠ 프로세스 생략. 최소 계획이라도 필요합니다",
        stage="plan",
        severity="high",
    ),
    RationalizationPattern(
        thought="This is too simple for a plan",
        reality="Simplicity does not mean skip process.",
        stage="plan",
        severity="medium",
    ),
    RationalizationPattern(
        thought="I need more context first",
        reality="Skill check comes BEFORE clarifying questions.",
        stage="plan",
        severity="medium",
    ),
    # review
    RationalizationPattern(
        thought="코드가 간단하니 리뷰를 생략하겠다",
        reality="간단한 코드에도 버그와 보안 이슈가 있을 수 있습니다",
        stage="review",
        severity="high",
    ),
    RationalizationPattern(
        thought="이미 테스트가 통과해서 리뷰 불필요",
        reality="테스트 통과 ≠ 올바른 구현. 의도와 일치하는지 확인해야 합니다",
        stage="review",
        severity="high",
    ),
    # run
    RationalizationPattern(
        thought="plan 없이 바로 구현하겠다",
        reality="계획 없는 구현은 재작업의 가장 큰 원인입니다",
        stage="run",
        severity="high",
    ),
    RationalizationPattern(
        thought="This is just a quick fix",
        reality="Quick fixes accumulate into technical debt.",
        stage="run",
        severity="medium",
    ),
    # verify
    RationalizationPattern(
        thought="테스트가 통과했으니 검증은 필요 없다",
        reality="테스트 커버리지 ≠ 전체 검증. edge case를 확인하세요",
        stage="verify",
        severity="high",
    ),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_rationalization(
    text: str,
    patterns: list[RationalizationPattern] | None = None,
) -> list[AntiRationalizationCheck]:
    """Scan *text* for substring matches against rationalization patterns.

    Returns all matches with ``detected=True``.  Matching is case-insensitive.
    """
    if patterns is None:
        patterns = BUILTIN_PATTERNS

    text_lower = text.lower()
    checks: list[AntiRationalizationCheck] = []

    for pattern in patterns:
        if pattern.thought.lower() in text_lower:
            checks.append(
                AntiRationalizationCheck(
                    pattern=pattern,
                    detected=True,
                    context=text,
                )
            )

    return checks


def get_patterns_for_stage(
    stage: str,
    patterns: list[RationalizationPattern] | None = None,
) -> list[RationalizationPattern]:
    """Return patterns belonging to *stage*."""
    if patterns is None:
        patterns = BUILTIN_PATTERNS
    return [p for p in patterns if p.stage == stage]


def format_rationalization_report(
    checks: list[AntiRationalizationCheck],
) -> str:
    """Human-readable report of detected rationalization patterns."""
    if not checks:
        return "✅ No rationalization patterns detected."

    lines: list[str] = [
        f"🚩 {len(checks)} rationalization pattern(s) detected:",
    ]
    for check in checks:
        lines.append(
            f"  🚩 Thought: {check.pattern.thought} → Reality: {check.pattern.reality}"
        )
    return "\n".join(lines)
