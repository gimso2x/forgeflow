import dataclasses
import pytest

from forgeflow_runtime.adversarial_review import (
    AdversarialConfig,
    ReviewVerdict,
    ReviewerResult,
    compute_agreement,
    format_adversarial_report,
    resolve_verdict,
)


# -- helpers --

def _make_result(
    reviewer_id: str = "r1",
    model: str = "gpt-4",
    verdict: ReviewVerdict = ReviewVerdict.PASS,
    score: float = 0.9,
    findings: list[str] | None = None,
    confidence: float = 0.85,
) -> ReviewerResult:
    return ReviewerResult(
        reviewer_id=reviewer_id,
        model=model,
        verdict=verdict,
        score=score,
        findings=findings or [],
        confidence=confidence,
    )


# -- compute_agreement tests --


def test_agreement_same_verdict_returns_1() -> None:
    r1 = _make_result(verdict=ReviewVerdict.PASS)
    r2 = _make_result(verdict=ReviewVerdict.PASS)
    assert compute_agreement(r1, r2) == 1.0


def test_agreement_opposite_verdicts_returns_0() -> None:
    r1 = _make_result(verdict=ReviewVerdict.PASS)
    r2 = _make_result(verdict=ReviewVerdict.FAIL)
    assert compute_agreement(r1, r2) == 0.0


def test_agreement_needs_discussion_partial() -> None:
    r1 = _make_result(verdict=ReviewVerdict.PASS)
    r2 = _make_result(verdict=ReviewVerdict.NEEDS_DISCUSSION)
    assert compute_agreement(r1, r2) == 0.5


# -- resolve_verdict tests --


def test_resolve_two_agree() -> None:
    r1 = _make_result(reviewer_id="alice", verdict=ReviewVerdict.PASS, confidence=0.9)
    r2 = _make_result(reviewer_id="bob", verdict=ReviewVerdict.PASS, confidence=0.8)
    cfg = AdversarialConfig(primary_model="gpt-4", secondary_model="claude-3")
    result = resolve_verdict([r1, r2], cfg)
    assert result["verdict"] == ReviewVerdict.PASS
    assert result["needs_tiebreaker"] is False


def test_resolve_two_disagree_needs_tiebreaker() -> None:
    r1 = _make_result(reviewer_id="alice", verdict=ReviewVerdict.PASS, confidence=0.9)
    r2 = _make_result(reviewer_id="bob", verdict=ReviewVerdict.FAIL, confidence=0.8)
    cfg = AdversarialConfig(
        primary_model="gpt-4", secondary_model="claude-3", tiebreaker_model="o1"
    )
    result = resolve_verdict([r1, r2], cfg)
    assert result["verdict"] == ReviewVerdict.NEEDS_DISCUSSION
    assert result["needs_tiebreaker"] is True


def test_resolve_single_result() -> None:
    r1 = _make_result(reviewer_id="alice", verdict=ReviewVerdict.FAIL, confidence=0.95)
    cfg = AdversarialConfig(primary_model="gpt-4", secondary_model="claude-3")
    result = resolve_verdict([r1], cfg)
    assert result["verdict"] == ReviewVerdict.FAIL
    assert result["confidence"] == 0.95


def test_resolve_confidence_is_average() -> None:
    r1 = _make_result(reviewer_id="alice", verdict=ReviewVerdict.PASS, confidence=0.6)
    r2 = _make_result(reviewer_id="bob", verdict=ReviewVerdict.PASS, confidence=1.0)
    cfg = AdversarialConfig(primary_model="gpt-4", secondary_model="claude-3")
    result = resolve_verdict([r1, r2], cfg)
    assert result["confidence"] == pytest.approx(0.8)


# -- format_adversarial_report tests --


def test_report_contains_reviewer_ids_and_findings() -> None:
    r1 = _make_result(
        reviewer_id="alice",
        model="gpt-4",
        verdict=ReviewVerdict.PASS,
        findings=["No issues found", "Clean implementation"],
        confidence=0.9,
    )
    r2 = _make_result(
        reviewer_id="bob",
        model="claude-3",
        verdict=ReviewVerdict.FAIL,
        findings=["Missing type hints"],
        confidence=0.85,
    )
    cfg = AdversarialConfig(primary_model="gpt-4", secondary_model="claude-3")
    resolution = resolve_verdict([r1, r2], cfg)
    report = format_adversarial_report([r1, r2], resolution)
    assert "alice" in report
    assert "bob" in report
    assert "No issues found" in report
    assert "Missing type hints" in report


# -- immutability / defaults --


def test_reviewer_result_is_frozen() -> None:
    r = _make_result()
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.score = 0.0  # type: ignore[misc]


def test_adversarial_config_defaults() -> None:
    cfg = AdversarialConfig(primary_model="gpt-4", secondary_model="claude-3")
    assert cfg.min_confidence == 0.7
    assert cfg.agreement_threshold == 0.3
    assert cfg.tiebreaker_model is None
