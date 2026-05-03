"""Metric execution and JSON extraction for XLOOP."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class MetricResult:
    """Result of executing a metric command."""

    raw_output: str
    values: dict[str, float]
    timestamp: str


def execute_metric(
    command: list[str],
    *,
    timeout: int = 60,
    cwd: Path | None = None,
) -> MetricResult:
    """Execute a metric command safely.

    Safety: command must be a list (no shell injection).
    Uses subprocess.run with explicit args.
    Extracts JSON objects from mixed stdout (brace-depth aware).

    Raises:
        subprocess.CalledProcessError: If command exits non-zero.
        subprocess.TimeoutExpired: If command exceeds timeout.
    """
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            command,
            output=result.stdout,
            stderr=result.stderr,
        )
    values = extract_json_values(result.stdout)
    timestamp = datetime.now(timezone.utc).isoformat()
    return MetricResult(
        raw_output=result.stdout,
        values=values,
        timestamp=timestamp,
    )


def extract_json_values(output: str) -> dict[str, float]:
    """Parse JSON values from mixed stdout. Brace-depth aware extraction.

    Scans through the output looking for JSON objects (``{...}``), parses
    each one, and merges their numeric values into a single dict.  Later
    objects overwrite earlier ones on key collision.
    """
    values: dict[str, float] = {}
    depth = 0
    start = -1
    for i, ch in enumerate(output):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                candidate = output[start : i + 1]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict):
                        for key, val in obj.items():
                            if isinstance(val, (int, float)):
                                values[str(key)] = float(val)
                except (json.JSONDecodeError, ValueError):
                    pass
                start = -1
    return values
