"""Circuit breaker for XLOOP experiment loops."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CircuitState:
    """Snapshot of circuit breaker state."""

    consecutive_no_improvements: int
    tripped: bool


class CircuitBreaker:
    """Trips after *max_stagnant* consecutive non-improvements."""

    def __init__(self, max_stagnant: int = 3) -> None:
        self.max_stagnant = max_stagnant
        self._stagnant_count = 0

    def record(self, improved: bool) -> CircuitState:
        """Record iteration result. Returns current state."""
        if improved:
            self._stagnant_count = 0
        else:
            self._stagnant_count += 1
        return CircuitState(
            consecutive_no_improvements=self._stagnant_count,
            tripped=self.tripped,
        )

    def reset(self) -> None:
        """Reset for new experiment."""
        self._stagnant_count = 0

    @property
    def tripped(self) -> bool:
        """True if circuit breaker has tripped."""
        return self._stagnant_count >= self.max_stagnant
