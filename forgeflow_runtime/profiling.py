"""Agent performance profiling for ForgeFlow pipelines.

Provides stage-level and model-level timing, token usage, cost estimation,
bottleneck detection, and session comparison.  Builds on ``cost`` and
``telemetry`` modules — no external dependencies (stdlib only).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StageProfile:
    """Performance snapshot for a single stage execution."""

    stage: str
    model: str  # adapter_target, e.g. "claude", "codex"
    status: str  # "success", "failure", "blocked"
    duration_s: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    error: str | None = None


@dataclass(frozen=True)
class PipelineProfile:
    """Aggregated performance profile for an entire pipeline run."""

    pipeline_id: str
    route: str
    stages: tuple[StageProfile, ...] = ()
    total_duration_s: float = 0.0
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    started_at: str = ""
    finished_at: str = ""

    @property
    def stage_count(self) -> int:
        return len(self.stages)

    @property
    def success_count(self) -> int:
        return sum(1 for s in self.stages if s.status == "success")

    @property
    def failure_count(self) -> int:
        return sum(1 for s in self.stages if s.status == "failure")


@dataclass
class Bottleneck:
    """Identified performance bottleneck."""

    label: str  # human-readable description
    stage: str
    metric: str  # "duration_s", "cost_usd", "total_tokens"
    value: float
    percentile_rank: float  # 0.0–1.0 within the pipeline


@dataclass(frozen=True)
class ComparisonResult:
    """Result of comparing two pipeline profiles."""

    baseline_id: str
    candidate_id: str
    duration_delta_s: float  # positive = candidate is slower
    cost_delta_usd: float  # positive = candidate is more expensive
    token_input_delta: int
    token_output_delta: int
    regressions: tuple[str, ...] = ()  # human-readable regression lines
    improvements: tuple[str, ...] = ()  # human-readable improvement lines


# ---------------------------------------------------------------------------
# Profiling collector
# ---------------------------------------------------------------------------
class ProfilingCollector:
    """Collects stage profiles during pipeline execution.

    Usage::

        collector = ProfilingCollector(pipeline_id="run-1", route="small")
        with collector.stage("clarify", model="claude"):
            result = execute_stage(...)
        collector.record_stage(result)
        profile = collector.build()
    """

    def __init__(self, pipeline_id: str, route: str) -> None:
        self.pipeline_id = pipeline_id
        self.route = route
        self._stages: list[StageProfile] = []
        self._current_start: float | None = None
        self._current_stage: str | None = None
        self._current_model: str | None = None
        self._started_at: str = _utc_now_iso()
        self._finished_at: str = ""

    def stage(self, stage_name: str, model: str = "claude") -> _StageTimer:
        """Context manager for timing a single stage execution.

        Returns a :class:`_StageTimer` that must be used with
        :meth:`record_stage` after the stage completes::

            with collector.stage("clarify", model="claude") as timer:
                result = execute_stage(...)
            collector.record_stage(result)
        """
        return _StageTimer(self, stage_name, model)

    def _start_stage(self, stage_name: str, model: str) -> None:
        self._current_stage = stage_name
        self._current_model = model
        self._current_start = time.monotonic()

    def record_stage(self, result: Any, *, duration_s: float | None = None) -> None:
        """Record a completed stage from a RunTaskResult.

        If *duration_s* is not provided, uses the time measured by the
        :meth:`stage` context manager.
        """
        from forgeflow_runtime.cost import estimate_cost

        stage_name = self._current_stage or getattr(result, "stage", "unknown")
        model = self._current_model or "claude"

        if duration_s is None:
            duration_s = time.monotonic() - self._current_start if self._current_start else 0.0

        token_usage = getattr(result, "token_usage", {}) or {}
        input_tokens = token_usage.get("input", 0)
        output_tokens = token_usage.get("output", 0)
        cost = estimate_cost(input_tokens, output_tokens, model=model)

        self._stages.append(
            StageProfile(
                stage=stage_name,
                model=model,
                status=getattr(result, "status", "unknown"),
                duration_s=round(duration_s, 6),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                cost_usd=round(cost.total_cost_usd, 8),
                error=getattr(result, "error", None),
            )
        )
        self._current_stage = None
        self._current_model = None
        self._current_start = None

    def record_raw(
        self,
        stage: str,
        model: str,
        status: str,
        duration_s: float,
        input_tokens: int,
        output_tokens: int,
        error: str | None = None,
    ) -> None:
        """Record a stage profile from raw values (no RunTaskResult needed)."""
        from forgeflow_runtime.cost import estimate_cost

        cost = estimate_cost(input_tokens, output_tokens, model=model)
        self._stages.append(
            StageProfile(
                stage=stage,
                model=model,
                status=status,
                duration_s=round(duration_s, 6),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                cost_usd=round(cost.total_cost_usd, 8),
                error=error,
            )
        )

    def build(self) -> PipelineProfile:
        """Build a frozen :class:`PipelineProfile` from collected data."""
        total_duration = sum(s.duration_s for s in self._stages)
        total_cost = sum(s.cost_usd for s in self._stages)
        total_input = sum(s.input_tokens for s in self._stages)
        total_output = sum(s.output_tokens for s in self._stages)
        self._finished_at = _utc_now_iso()
        return PipelineProfile(
            pipeline_id=self.pipeline_id,
            route=self.route,
            stages=tuple(self._stages),
            total_duration_s=round(total_duration, 6),
            total_cost_usd=round(total_cost, 8),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            started_at=self._started_at,
            finished_at=self._finished_at,
        )


# ---------------------------------------------------------------------------
# Stage timer (internal context manager)
# ---------------------------------------------------------------------------
class _StageTimer:
    """Context manager returned by :meth:`ProfilingCollector.stage`."""

    def __init__(self, collector: ProfilingCollector, stage_name: str, model: str) -> None:
        self._collector = collector
        self._stage_name = stage_name
        self._model = model

    def __enter__(self) -> _StageTimer:
        self._collector._start_stage(self._stage_name, self._model)
        return self

    def __exit__(self, *args: Any) -> None:
        pass  # timing completed in record_stage()


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------
def detect_bottlenecks(profile: PipelineProfile, *, top_n: int = 3) -> list[Bottleneck]:
    """Identify the slowest and most expensive stages.

    Returns up to *top_n* bottlenecks.  Each metric category (duration, cost,
    tokens) contributes at most one entry — the worst offender — so the
    caller gets a concise, multi-dimensional view regardless of scale
    differences between metrics.
    """
    if not profile.stages:
        return []

    metric_defs: list[tuple[str, str, str]] = [
        ("duration_s", "desc", "{:.2f}s"),
        ("cost_usd", "desc", "${:.6f}"),
        ("total_tokens", "desc", "{:.0f} tokens"),
    ]

    bottlenecks: list[Bottleneck] = []
    for metric_name, _, _ in metric_defs:
        ranked = sorted(profile.stages, key=lambda s, m=metric_name: getattr(s, m), reverse=True)
        worst = ranked[0]
        value = getattr(worst, metric_name)
        if value <= 0:
            continue
        # percentile: 1.0 for single-stage, decreasing for lower ranks
        n = len(ranked)
        rank = 1.0 if n == 1 else (n - 0) / n  # top element

        fmt = next(f for m, _, f in metric_defs if m == metric_name)
        label = f"{worst.stage} ({worst.model}) — {fmt.format(value)}"

        bottlenecks.append(
            Bottleneck(
                label=label,
                stage=worst.stage,
                metric=metric_name,
                value=value,
                percentile_rank=round(rank, 4),
            )
        )

    # Order: duration > cost > tokens (fixed priority, no cross-metric compare)
    priority = {m: i for i, (m, _, _) in enumerate(metric_defs)}
    bottlenecks.sort(key=lambda b: priority[b.metric])
    return bottlenecks[:top_n]


def compare_profiles(baseline: PipelineProfile, candidate: PipelineProfile) -> ComparisonResult:
    """Compare two pipeline profiles and identify regressions/improvements.

    Positive deltas mean the candidate is *worse* (slower, more expensive).
    """
    regressions: list[str] = []
    improvements: list[str] = []

    duration_delta = candidate.total_duration_s - baseline.total_duration_s
    cost_delta = candidate.total_cost_usd - baseline.total_cost_usd
    input_delta = candidate.total_input_tokens - baseline.total_input_tokens
    output_delta = candidate.total_output_tokens - baseline.total_output_tokens

    if duration_delta > 0:
        regressions.append(f"duration +{duration_delta:.2f}s ({duration_delta / max(baseline.total_duration_s, 0.001) * 100:.1f}%)")
    elif duration_delta < 0:
        improvements.append(f"duration {duration_delta:.2f}s ({duration_delta / max(baseline.total_duration_s, 0.001) * 100:.1f}%)")

    if cost_delta > 0:
        regressions.append(f"cost +${cost_delta:.6f}")
    elif cost_delta < 0:
        improvements.append(f"cost ${cost_delta:.6f}")

    if input_delta > 0:
        regressions.append(f"input tokens +{input_delta}")
    elif input_delta < 0:
        improvements.append(f"input tokens {input_delta}")

    if output_delta > 0:
        regressions.append(f"output tokens +{output_delta}")
    elif output_delta < 0:
        improvements.append(f"output tokens {output_delta}")

    return ComparisonResult(
        baseline_id=baseline.pipeline_id,
        candidate_id=candidate.pipeline_id,
        duration_delta_s=round(duration_delta, 6),
        cost_delta_usd=round(cost_delta, 8),
        token_input_delta=input_delta,
        token_output_delta=output_delta,
        regressions=tuple(regressions),
        improvements=tuple(improvements),
    )


def format_summary(profile: PipelineProfile) -> str:
    """Format a human-readable summary of a pipeline profile."""
    lines = [
        f"Pipeline: {profile.pipeline_id} (route={profile.route})",
        f"Stages: {profile.stage_count} ({profile.success_count} ok, {profile.failure_count} failed)",
        f"Duration: {profile.total_duration_s:.2f}s",
        f"Tokens: {profile.total_input_tokens} in / {profile.total_output_tokens} out",
        f"Cost: ${profile.total_cost_usd:.6f}",
    ]

    if profile.stages:
        lines.append("")
        lines.append("Stage breakdown:")
        for s in profile.stages:
            status_icon = "✓" if s.status == "success" else "✗" if s.status == "failure" else "⊘"
            lines.append(
                f"  {status_icon} {s.stage:20s} {s.model:10s} "
                f"{s.duration_s:8.2f}s  {s.total_tokens:8d} tok  ${s.cost_usd:.6f}"
            )
            if s.error:
                lines.append(f"    error: {s.error[:100]}")

    bottlenecks = detect_bottlenecks(profile)
    if bottlenecks:
        lines.append("")
        lines.append("Bottlenecks:")
        for b in bottlenecks:
            lines.append(f"  ⚠ {b.label}")

    return "\n".join(lines)


def format_comparison(result: ComparisonResult) -> str:
    """Format a human-readable comparison between two profiles."""
    lines = [
        f"Comparison: {result.baseline_id} (baseline) vs {result.candidate_id}",
    ]
    if result.regressions:
        lines.append("Regressions:")
        for r in result.regressions:
            lines.append(f"  ↗ {r}")
    if result.improvements:
        lines.append("Improvements:")
        for i in result.improvements:
            lines.append(f"  ↘ {i}")
    if not result.regressions and not result.improvements:
        lines.append("  — no significant difference")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
