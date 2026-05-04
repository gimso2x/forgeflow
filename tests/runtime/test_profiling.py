"""Tests for forgeflow_runtime/profiling.py."""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Any

import pytest

from forgeflow_runtime.cost import BudgetConfig, CostEstimate
from forgeflow_runtime.executor import RunTaskResult
from forgeflow_runtime.profiling import (
    Bottleneck,
    ComparisonResult,
    PipelineProfile,
    ProfilingCollector,
    StageProfile,
    compare_profiles,
    detect_bottlenecks,
    format_comparison,
    format_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_result(
    status: str = "success",
    input_tokens: int = 100,
    output_tokens: int = 50,
    error: str | None = None,
) -> RunTaskResult:
    return RunTaskResult(
        status=status,
        token_usage={"input": input_tokens, "output": output_tokens},
        error=error,
    )


def _make_stage(
    stage: str = "clarify",
    model: str = "claude",
    status: str = "success",
    duration_s: float = 1.0,
    input_tokens: int = 100,
    output_tokens: int = 50,
    error: str | None = None,
) -> StageProfile:
    from forgeflow_runtime.cost import estimate_cost

    cost = estimate_cost(input_tokens, output_tokens, model=model)
    return StageProfile(
        stage=stage,
        model=model,
        status=status,
        duration_s=duration_s,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_usd=cost.total_cost_usd,
        error=error,
    )


def _make_profile(*stages: StageProfile, pipeline_id: str = "run-1", route: str = "small") -> PipelineProfile:
    return PipelineProfile(
        pipeline_id=pipeline_id,
        route=route,
        stages=tuple(stages),
        total_duration_s=sum(s.duration_s for s in stages),
        total_cost_usd=sum(s.cost_usd for s in stages),
        total_input_tokens=sum(s.input_tokens for s in stages),
        total_output_tokens=sum(s.output_tokens for s in stages),
    )


# ===========================================================================
# StageProfile
# ===========================================================================
class TestStageProfile:
    def test_frozen(self) -> None:
        s = _make_stage()
        with pytest.raises(AttributeError):
            s.stage = "plan"  # type: ignore[misc]

    def test_all_fields_accessible(self) -> None:
        s = _make_stage(error="boom")
        assert s.stage == "clarify"
        assert s.model == "claude"
        assert s.status == "success"
        assert s.error == "boom"


# ===========================================================================
# PipelineProfile
# ===========================================================================
class TestPipelineProfile:
    def test_empty_pipeline(self) -> None:
        p = _make_profile()
        assert p.stage_count == 0
        assert p.success_count == 0
        assert p.failure_count == 0
        assert p.total_duration_s == 0.0

    def test_stage_count(self) -> None:
        p = _make_profile(_make_stage(), _make_stage(stage="plan"))
        assert p.stage_count == 2

    def test_success_failure_counts(self) -> None:
        p = _make_profile(
            _make_stage(status="success"),
            _make_stage(status="failure"),
            _make_stage(status="success"),
            _make_stage(status="blocked"),
        )
        assert p.success_count == 2
        assert p.failure_count == 1


# ===========================================================================
# ProfilingCollector
# ===========================================================================
class TestProfilingCollector:
    def test_build_empty(self) -> None:
        c = ProfilingCollector(pipeline_id="empty", route="small")
        p = c.build()
        assert p.pipeline_id == "empty"
        assert p.route == "small"
        assert p.stage_count == 0

    def test_record_stage_from_result(self) -> None:
        c = ProfilingCollector(pipeline_id="r1", route="small")
        c._start_stage("clarify", "claude")
        time.sleep(0.01)  # small delay for measurable duration
        result = _make_result(input_tokens=200, output_tokens=100)
        c.record_stage(result)
        p = c.build()
        assert p.stage_count == 1
        assert p.stages[0].stage == "clarify"
        assert p.stages[0].model == "claude"
        assert p.stages[0].input_tokens == 200
        assert p.stages[0].output_tokens == 100
        assert p.stages[0].status == "success"
        assert p.stages[0].duration_s >= 0.01
        assert p.stages[0].cost_usd > 0

    def test_record_stage_with_explicit_duration(self) -> None:
        c = ProfilingCollector(pipeline_id="r2", route="small")
        c._start_stage("execute", "claude")
        result = _make_result()
        c.record_stage(result, duration_s=5.0)
        p = c.build()
        assert p.stages[0].duration_s == 5.0

    def test_record_stage_failure_with_error(self) -> None:
        c = ProfilingCollector(pipeline_id="r3", route="small")
        c._start_stage("execute", "codex")
        result = _make_result(status="failure", error="timeout")
        c.record_stage(result)
        p = c.build()
        assert p.stages[0].status == "failure"
        assert p.stages[0].error == "timeout"

    def test_record_raw(self) -> None:
        c = ProfilingCollector(pipeline_id="r4", route="medium")
        c.record_raw(
            stage="plan",
            model="claude",
            status="success",
            duration_s=2.5,
            input_tokens=500,
            output_tokens=200,
        )
        p = c.build()
        assert p.stage_count == 1
        assert p.stages[0].stage == "plan"
        assert p.stages[0].total_tokens == 700

    def test_multiple_stages_accumulate(self) -> None:
        c = ProfilingCollector(pipeline_id="r5", route="medium")
        for stage in ["clarify", "plan", "execute", "finalize"]:
            c._start_stage(stage, "claude")
            c.record_stage(_make_result(), duration_s=float(len(stage)))
        p = c.build()
        assert p.stage_count == 4
        assert p.total_duration_s == sum(float(len(s)) for s in ["clarify", "plan", "execute", "finalize"])
        assert p.total_input_tokens == 400  # 100 per stage

    def test_stage_context_manager(self) -> None:
        c = ProfilingCollector(pipeline_id="r6", route="small")
        with c.stage("clarify", model="claude"):
            time.sleep(0.01)
        c.record_stage(_make_result())
        p = c.build()
        assert p.stages[0].stage == "clarify"
        assert p.stages[0].model == "claude"
        assert p.stages[0].duration_s >= 0.01

    def test_build_sets_timestamps(self) -> None:
        c = ProfilingCollector(pipeline_id="r7", route="small")
        c.record_raw("clarify", "claude", "success", 1.0, 100, 50)
        p = c.build()
        assert p.started_at != ""
        assert p.finished_at != ""


# ===========================================================================
# detect_bottlenecks
# ===========================================================================
class TestDetectBottlenecks:
    def test_empty_profile(self) -> None:
        p = _make_profile()
        assert detect_bottlenecks(p) == []

    def test_single_stage(self) -> None:
        p = _make_profile(_make_stage(duration_s=5.0, input_tokens=1000, output_tokens=500))
        bns = detect_bottlenecks(p)
        assert len(bns) >= 1
        assert bns[0].stage == "clarify"

    def test_identifies_slowest_stage(self) -> None:
        p = _make_profile(
            _make_stage(stage="clarify", duration_s=1.0),
            _make_stage(stage="plan", duration_s=10.0),
            _make_stage(stage="execute", duration_s=5.0),
        )
        bns = detect_bottlenecks(p, top_n=1)
        assert len(bns) == 1
        assert bns[0].stage == "plan"
        assert bns[0].metric == "duration_s"
        assert bns[0].value == 10.0

    def test_identifies_most_expensive_stage(self) -> None:
        p = _make_profile(
            _make_stage(stage="clarify", input_tokens=100, output_tokens=50),
            _make_stage(stage="execute", input_tokens=10000, output_tokens=5000),
        )
        bns = detect_bottlenecks(p, top_n=3)
        cost_bns = [b for b in bns if b.metric == "cost_usd"]
        assert cost_bns[0].stage == "execute"

    def test_respects_top_n(self) -> None:
        stages = [_make_stage(stage=f"stage-{i}", duration_s=float(i + 1)) for i in range(10)]
        p = _make_profile(*stages)
        bns = detect_bottlenecks(p, top_n=2)
        assert len(bns) <= 2

    def test_bottleneck_percentile_rank(self) -> None:
        p = _make_profile(
            _make_stage(stage="a", duration_s=1.0),
            _make_stage(stage="b", duration_s=10.0),
        )
        bns = detect_bottlenecks(p, top_n=5)
        duration_bn = next(b for b in bns if b.metric == "duration_s")
        # Worst (b, 10.0s) should have high rank
        assert duration_bn.stage == "b"
        assert duration_bn.percentile_rank > 0.5


# ===========================================================================
# compare_profiles
# ===========================================================================
class TestCompareProfiles:
    def test_identical_profiles(self) -> None:
        s = _make_stage(duration_s=5.0, input_tokens=1000, output_tokens=500)
        baseline = _make_profile(s, pipeline_id="base")
        candidate = _make_profile(s, pipeline_id="cand")
        result = compare_profiles(baseline, candidate)
        assert result.duration_delta_s == 0.0
        assert result.cost_delta_usd == 0.0
        assert result.regressions == ()
        assert result.improvements == ()

    def test_candidate_slower(self) -> None:
        baseline = _make_profile(_make_stage(duration_s=5.0), pipeline_id="base")
        candidate = _make_profile(_make_stage(duration_s=10.0), pipeline_id="cand")
        result = compare_profiles(baseline, candidate)
        assert result.duration_delta_s == 5.0
        assert len(result.regressions) >= 1
        assert any("duration" in r for r in result.regressions)

    def test_candidate_faster(self) -> None:
        baseline = _make_profile(_make_stage(duration_s=10.0), pipeline_id="base")
        candidate = _make_profile(_make_stage(duration_s=5.0), pipeline_id="cand")
        result = compare_profiles(baseline, candidate)
        assert result.duration_delta_s == -5.0
        assert len(result.improvements) >= 1

    def test_more_tokens(self) -> None:
        baseline = _make_profile(_make_stage(input_tokens=100, output_tokens=50), pipeline_id="base")
        candidate = _make_profile(_make_stage(input_tokens=200, output_tokens=100), pipeline_id="cand")
        result = compare_profiles(baseline, candidate)
        assert result.token_input_delta == 100
        assert result.token_output_delta == 50

    def test_multiple_regressions(self) -> None:
        baseline = _make_profile(_make_stage(duration_s=5.0, input_tokens=100), pipeline_id="base")
        candidate = _make_profile(_make_stage(duration_s=10.0, input_tokens=200), pipeline_id="cand")
        result = compare_profiles(baseline, candidate)
        assert len(result.regressions) >= 2  # duration + input tokens


# ===========================================================================
# format_summary
# ===========================================================================
class TestFormatSummary:
    def test_empty_pipeline(self) -> None:
        p = _make_profile()
        text = format_summary(p)
        assert "Pipeline: run-1" in text
        assert "Stages: 0" in text

    def test_with_stages(self) -> None:
        p = _make_profile(
            _make_stage(stage="clarify", duration_s=1.0),
            _make_stage(stage="plan", duration_s=2.0, status="failure", error="bad"),
        )
        text = format_summary(p)
        assert "clarify" in text
        assert "plan" in text
        assert "✓" in text
        assert "✗" in text
        assert "bad" in text

    def test_shows_bottlenecks(self) -> None:
        p = _make_profile(
            _make_stage(stage="fast", duration_s=0.1),
            _make_stage(stage="slow", duration_s=10.0),
        )
        text = format_summary(p)
        assert "Bottlenecks" in text
        assert "slow" in text


# ===========================================================================
# format_comparison
# ===========================================================================
class TestFormatComparison:
    def test_identical(self) -> None:
        s = _make_stage()
        result = compare_profiles(
            _make_profile(s, pipeline_id="a"),
            _make_profile(s, pipeline_id="b"),
        )
        text = format_comparison(result)
        assert "no significant difference" in text

    def test_regression_text(self) -> None:
        result = compare_profiles(
            _make_profile(_make_stage(duration_s=5.0), pipeline_id="base"),
            _make_profile(_make_stage(duration_s=10.0), pipeline_id="cand"),
        )
        text = format_comparison(result)
        assert "Regressions" in text
        assert "↗" in text

    def test_improvement_text(self) -> None:
        result = compare_profiles(
            _make_profile(_make_stage(duration_s=10.0), pipeline_id="base"),
            _make_profile(_make_stage(duration_s=5.0), pipeline_id="cand"),
        )
        text = format_comparison(result)
        assert "Improvements" in text
        assert "↘" in text
