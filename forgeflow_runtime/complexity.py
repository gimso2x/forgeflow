"""Adaptive task complexity assessment for route selection.

Provides heuristic-based scoring of brief/plan content to automatically
select the appropriate complexity route (small / medium / large_high_risk).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

_RISK_KEYWORDS = frozenset({
    "production", "deploy", "deployment", "migration", "schema",
    "database", "auth", "authentication", "authorization", "security",
    "breaking", "infra", "infrastructure", "architecture",
})

_LEVEL_TO_ROUTE: dict[str, str] = {
    "LOW": "small",
    "MEDIUM": "medium",
    "HIGH": "large_high_risk",
}


@dataclass(frozen=True)
class ComplexityFactors:
    """Heuristically extracted complexity signals from brief/plan text."""

    file_count: int = 0
    estimated_lines: int = 0
    requirement_count: int = 0
    dependency_count: int = 0
    risk_keywords: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ComplexityWeights:
    """Tuneable weights and thresholds for complexity scoring."""

    file_count: float = 1.0
    estimated_lines: float = 0.1
    requirement_count: float = 2.0
    dependency_count: float = 1.5
    risk_keyword: float = 3.0
    low_threshold: float = 10.0
    high_threshold: float = 25.0


@dataclass(frozen=True)
class ComplexityScore:
    """Result of an adaptive complexity assessment."""

    raw_score: float
    level: str  # "LOW" | "MEDIUM" | "HIGH"
    route_name: str  # "small" | "medium" | "large_high_risk"
    factors: ComplexityFactors
    rationale: str


# ---------------------------------------------------------------------------
# Factor extraction
# ---------------------------------------------------------------------------

_FILE_PATH_RE = re.compile(
    r"(?:^|[\s(\"\',\[:])"
    r"(?:[A-Za-z0-9_\-./]+/(?:[A-Za-z0-9_\-.*]+\.[A-Za-z0-9]+)"
    r"|(?:[A-Za-z0-9_\-.*]+\.[A-Za-z0-9]+))"
    r"(?:[\s)\]\",;:]|$)",
)

_REQUIREMENT_RE = re.compile(
    r"\b(must|should|shall|require|required|need)\b",
    re.IGNORECASE,
)

_NUMBERED_ITEM_RE = re.compile(
    r"(?:^|\n)\s*(?:\d+[\.\)]\s|[-*]\s+\[[ x]\]\s)",
)

_DEPENDENCY_RE = re.compile(
    r"from\s+[A-Za-z_][A-Za-z0-9_.]*\s+import"
    r"|import\s+[A-Za-z_][A-Za-z0-9_.]*"
    r"|module\s+[\"\'][A-Za-z_][A-Za-z0-9_./]*[\"\']"
    r"|(?:api|endpoint)\s*[:(]",
)

_STEP_RE = re.compile(
    r"(?:^|\n)\s*(?:\d+[\.\)]\s+(?:step|task|phase)\b|(?:step|task|phase)\s+\d+[\.\)])",
    re.IGNORECASE,
)

_LOC_RE = re.compile(
    r"(?:\b(\d+)\s*(?:LOC|lines?\s(?:of\s+code|changed|added|new))\b)",
    re.IGNORECASE,
)


def extract_factors(brief_text: str, plan_text: str | None = None) -> ComplexityFactors:
    """Extract complexity factors from brief and optional plan text."""
    combined = brief_text
    if plan_text:
        combined = f"{brief_text}\n{plan_text}"

    # File path patterns
    file_matches = _FILE_PATH_RE.findall(combined)
    file_count = len(file_matches)

    # Estimated lines: look for explicit LOC mentions or step-based estimation
    estimated_lines = 0
    loc_matches = _LOC_RE.findall(combined)
    for m in loc_matches:
        estimated_lines += int(m)
    if estimated_lines == 0:
        step_count = len(_STEP_RE.findall(combined))
        if step_count > 0:
            estimated_lines = step_count * 20

    # Requirements: must/should/require + numbered items / checkboxes
    req_kw_matches = _REQUIREMENT_RE.findall(combined)
    numbered_matches = _NUMBERED_ITEM_RE.findall(combined)
    requirement_count = len(req_kw_matches) + len(numbered_matches)

    # Dependencies: import statements, module refs, API refs
    dependency_count = len(_DEPENDENCY_RE.findall(combined))

    # Risk keywords
    lower = combined.lower()
    risk_keywords = sorted(kw for kw in _RISK_KEYWORDS if kw in lower)

    return ComplexityFactors(
        file_count=file_count,
        estimated_lines=estimated_lines,
        requirement_count=requirement_count,
        dependency_count=dependency_count,
        risk_keywords=risk_keywords,
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def assess_complexity(
    brief_text: str,
    plan_text: str | None = None,
    weights: ComplexityWeights | None = None,
) -> ComplexityScore:
    """Score complexity and determine route."""
    w = weights or ComplexityWeights()
    factors = extract_factors(brief_text, plan_text)

    raw_score = (
        factors.file_count * w.file_count
        + factors.estimated_lines * w.estimated_lines
        + factors.requirement_count * w.requirement_count
        + factors.dependency_count * w.dependency_count
        + len(factors.risk_keywords) * w.risk_keyword
    )

    if raw_score < w.low_threshold:
        level = "LOW"
    elif raw_score >= w.high_threshold:
        level = "HIGH"
    else:
        level = "MEDIUM"

    route_name = _LEVEL_TO_ROUTE[level]

    parts = [f"raw_score={raw_score:.1f} ({level})"]
    if factors.file_count:
        parts.append(f"{factors.file_count} files")
    if factors.requirement_count:
        parts.append(f"{factors.requirement_count} requirements")
    if factors.risk_keywords:
        parts.append(f"risk keywords: {', '.join(factors.risk_keywords)}")
    if factors.dependency_count:
        parts.append(f"{factors.dependency_count} dependencies")
    rationale = "Adaptive assessment: " + "; ".join(parts) + f" → {route_name}"

    return ComplexityScore(
        raw_score=raw_score,
        level=level,
        route_name=route_name,
        factors=factors,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# Route selection
# ---------------------------------------------------------------------------

def select_route(
    score: ComplexityScore,
    manual_route: str | None = None,
    *,
    adaptive_enabled: bool = True,
) -> str:
    """Select route name.

    If *adaptive_enabled* is ``True`` the score's ``route_name`` is used.
    Otherwise *manual_route* is returned, defaulting to ``"medium"``.
    """
    if adaptive_enabled:
        return score.route_name
    return manual_route or "medium"


# ---------------------------------------------------------------------------
# Policy helpers
# ---------------------------------------------------------------------------

def weights_from_policy(adaptive_routing: dict[str, Any]) -> ComplexityWeights:
    """Build a :class:`ComplexityWeights` from an ``adaptive_routing`` config dict."""
    w_map = adaptive_routing.get("weights", {})
    thresholds = adaptive_routing.get("thresholds", {})
    return ComplexityWeights(
        file_count=float(w_map.get("file_count", 1.0)),
        estimated_lines=float(w_map.get("estimated_lines", 0.1)),
        requirement_count=float(w_map.get("requirement_count", 2.0)),
        dependency_count=float(w_map.get("dependency_count", 1.5)),
        risk_keyword=float(w_map.get("risk_keyword", 3.0)),
        low_threshold=float(thresholds.get("low", 10.0)),
        high_threshold=float(thresholds.get("high", 25.0)),
    )
