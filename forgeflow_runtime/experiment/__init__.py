"""Automated Experiment Loop (XLOOP) for ForgeFlow.

Metric-driven experimentation with git isolation and circuit breaker safety.
"""

from __future__ import annotations

from forgeflow_runtime.experiment.loop import (
    ExperimentConfig,
    ExperimentResult,
    IterationResult,
    run_experiment,
)

__all__ = [
    "ExperimentConfig",
    "ExperimentResult",
    "IterationResult",
    "run_experiment",
]
