"""Self-improve signal pipeline — collect, deduplicate, and act on improvement signals."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class SignalSource(Enum):
    FIX_COMMIT = "fix_commit"
    BUG_FIXER_RETRY = "bug_fixer_retry"
    RECURRENCE = "recurrence"
    TELEMETRY = "telemetry"
    ADVERSARIAL_FINDING = "adversarial_finding"


@dataclass(frozen=True)
class Signal:
    id: str
    source: SignalSource
    description: str
    severity: str  # "low" | "medium" | "high"
    timestamp: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SignalFilter:
    acked_signal_ids: set[str] = field(default_factory=set)
    cooldown_seconds: int = 900
    max_signals_per_source: int = 10


def generate_signal_id(source: SignalSource, description: str) -> str:
    """Return a deterministic 12-char hex ID from source + description."""
    raw = f"{source.value}:{description}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def is_duplicate(signal: Signal, acked: set[str]) -> bool:
    """Return True if the signal ID has already been acknowledged."""
    return signal.id in acked


def is_on_cooldown(
    signal: Signal,
    last_signal_times: dict[str, str],
    cooldown: int,
) -> bool:
    """Return True if the same source had a signal within *cooldown* seconds."""
    key = signal.source.value
    last_ts = last_signal_times.get(key)
    if last_ts is None:
        return False
    try:
        last_dt = datetime.fromisoformat(last_ts)
        sig_dt = datetime.fromisoformat(signal.timestamp)
    except (ValueError, TypeError):
        return False
    elapsed = (sig_dt - last_dt).total_seconds()
    return 0 <= elapsed < cooldown


def filter_signals(
    signals: list[Signal],
    filter_config: SignalFilter,
    last_times: dict[str, str],
) -> list[Signal]:
    """Apply dedup, cooldown, and per-source cap filters."""
    result: list[Signal] = []
    counts: dict[str, int] = defaultdict(int)

    for sig in signals:
        if is_duplicate(sig, filter_config.acked_signal_ids):
            continue
        if is_on_cooldown(sig, last_times, filter_config.cooldown_seconds):
            continue
        counts[sig.source.value] += 1
        if counts[sig.source.value] > filter_config.max_signals_per_source:
            continue
        result.append(sig)

    return result


def should_invoke_worker(filtered_signals: list[Signal]) -> bool:
    """Return True when there is at least one signal to act on."""
    return len(filtered_signals) > 0


def format_signal_report(signals: list[Signal]) -> str:
    """Return a human-readable summary grouped by source."""
    if not signals:
        return "No signals."
    groups: dict[str, list[Signal]] = defaultdict(list)
    for sig in signals:
        groups[sig.source.value].append(sig)
    lines: list[str] = []
    for src, sigs in sorted(groups.items()):
        lines.append(f"[{src}] ({len(sigs)} signal(s))")
        for s in sigs:
            lines.append(f"  - [{s.severity}] {s.description}  (id={s.id})")
    return "\n".join(lines)


def build_signal_sources_config() -> dict[str, dict[str, Any]]:
    """Return default configuration for the five signal sources."""
    return {
        "fix_commit": {"enabled": True, "cooldown": 600, "severity_threshold": "low"},
        "bug_fixer_retry": {"enabled": True, "cooldown": 900, "severity_threshold": "medium"},
        "recurrence": {"enabled": True, "cooldown": 1200, "severity_threshold": "medium"},
        "telemetry": {"enabled": True, "cooldown": 300, "severity_threshold": "high"},
        "adversarial_finding": {"enabled": True, "cooldown": 1800, "severity_threshold": "high"},
    }
