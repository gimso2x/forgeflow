"""Multi-model orchestration layer for ForgeFlow.

Provides strategies for fan-out dispatch to multiple adapters:
consensus, debate, pipeline, fastest.
"""

from __future__ import annotations

from forgeflow_runtime.orchestra.strategy import (
    STRATEGY_REGISTRY,
    OrchestrationConfig,
    OrchestrationResult,
    run_orchestration,
)

__all__ = [
    "OrchestrationConfig",
    "OrchestrationResult",
    "STRATEGY_REGISTRY",
    "run_orchestration",
]
