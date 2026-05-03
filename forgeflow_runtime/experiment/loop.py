"""Experiment loop orchestrator for XLOOP."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from forgeflow_runtime.experiment.circuit import CircuitBreaker, CircuitState
from forgeflow_runtime.experiment.git_ops import ExperimentGit, GitDiff
from forgeflow_runtime.experiment.metric import MetricResult, execute_metric
from forgeflow_runtime.experiment.simplicity import (
    improvement_efficiency,
    simplicity_score,
)


@dataclass(frozen=True)
class IterationResult:
    """Result of a single experiment iteration."""

    iteration: int
    metric: MetricResult
    improvement: float  # positive = improved
    simplicity: float
    efficiency: float
    kept: bool  # True if improvement was accepted
    circuit_state: CircuitState


@dataclass(frozen=True)
class ExperimentResult:
    """Aggregate result of an experiment run."""

    experiment_id: str
    total_iterations: int
    baseline: MetricResult
    final: MetricResult
    iterations: list[IterationResult]
    circuit_tripped: bool
    top_improvements: list[IterationResult]  # top 5 by efficiency


@dataclass(frozen=True)
class ExperimentConfig:
    """Configuration for an experiment run."""

    metric_command: list[str]  # e.g. ["python", "-m", "pytest", "-q", "--tb=no"]
    metric_key: str  # JSON key to track, e.g. "passed"
    direction: str  # "higher" (maximize) or "lower" (minimize)
    max_iterations: int = 10
    circuit_breaker_limit: int = 3
    branch_prefix: str = "xloop"
    min_improvement: float = 0.0  # minimum improvement to accept
    cwd: Path | None = None


def run_experiment(
    config: ExperimentConfig,
    *,
    on_iteration: Callable[[IterationResult], None] | None = None,
) -> ExperimentResult:
    """Run the full experiment loop.

    1. Create experiment branch
    2. Capture baseline metric
    3. Loop:
       a. Execute metric command
       b. Compare against best-so-far
       c. Calculate simplicity + efficiency
       d. If improved and efficient -> commit (keep)
       e. If regressed -> reset (discard)
       f. Check circuit breaker
    4. Return to original branch
    5. Return ExperimentResult with top improvements

    on_iteration(iteration_result) callback for live progress.
    """
    experiment_id = uuid.uuid4().hex[:8]
    cwd = config.cwd or Path.cwd()
    circuit = CircuitBreaker(max_stagnant=config.circuit_breaker_limit)
    git = ExperimentGit(repo_root=cwd, branch_prefix=config.branch_prefix)

    # Snapshot current diff before branching (to track new changes only)
    git.create_branch(experiment_id)
    pre_diff = git.get_diff()

    # Baseline metric
    baseline = execute_metric(config.metric_command, cwd=cwd)
    best_value = _get_metric_value(baseline, config.metric_key)
    iterations: list[IterationResult] = []

    for i in range(1, config.max_iterations + 1):
        metric = execute_metric(config.metric_command, cwd=cwd)
        current_value = _get_metric_value(metric, config.metric_key)
        improvement = _calc_improvement(best_value, current_value, config.direction)

        # Diff since pre-experiment state
        diff = git.get_diff()
        # Subtract pre-existing diff to get experiment-only changes
        exp_diff = GitDiff(
            files_changed=max(0, diff.files_changed - pre_diff.files_changed),
            lines_added=max(0, diff.lines_added - pre_diff.lines_added),
            lines_removed=max(0, diff.lines_removed - pre_diff.lines_removed),
        )
        simp = simplicity_score(
            exp_diff.files_changed, exp_diff.lines_added, exp_diff.lines_removed
        )
        eff = improvement_efficiency(improvement, simp)

        improved = improvement > config.min_improvement
        state = circuit.record(improved)

        kept = False
        if improved:
            git.commit_changes(f"xloop/{experiment_id}: iteration {i}")
            best_value = current_value
            kept = True
        else:
            git.reset_to_start()

        ir = IterationResult(
            iteration=i,
            metric=metric,
            improvement=improvement,
            simplicity=simp,
            efficiency=eff,
            kept=kept,
            circuit_state=state,
        )
        iterations.append(ir)
        if on_iteration is not None:
            on_iteration(ir)

        if circuit.tripped:
            break

    # Determine final metric
    final = execute_metric(config.metric_command, cwd=cwd)

    # Return to original branch
    git.checkout_original()

    top = sorted(iterations, key=lambda x: x.efficiency, reverse=True)[:5]

    return ExperimentResult(
        experiment_id=experiment_id,
        total_iterations=len(iterations),
        baseline=baseline,
        final=final,
        iterations=iterations,
        circuit_tripped=circuit.tripped,
        top_improvements=top,
    )


def _get_metric_value(metric: MetricResult, key: str) -> float:
    """Retrieve a numeric metric value by key, defaulting to 0.0."""
    return metric.values.get(key, 0.0)


def _calc_improvement(best: float, current: float, direction: str) -> float:
    """Calculate improvement. Positive = improved."""
    if direction == "higher":
        return current - best
    elif direction == "lower":
        return best - current
    return 0.0
