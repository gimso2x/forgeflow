#!/usr/bin/env python3
"""Aggregate ForgeFlow telemetry event logs into summary.md.

Reads all <task-id>.md files in <storage-root>/telemetry/, parses event blocks,
and generates <storage-root>/telemetry/summary.md following templates/metrics-dashboard.md.

Usage:
    python3 scripts/telemetry_aggregate.py [--project-dir DIR]

Default storage is global/project-scoped:
    ~/.forgeflow/projects/<project-slug>/telemetry/

Set FORGEFLOW_HOME to override the global root.
"""
import pathlib
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

from forgeflow_storage import telemetry_dir

ROOT = pathlib.Path(".")


def _read(p):
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def _parse_events(text):
    """Parse event blocks from a telemetry event log file."""
    events = []
    blocks = re.split(r"^### ", text, flags=re.MULTILINE)
    for block in blocks[1:]:
        evt = {}
        for field in ["event", "stage", "duration_seconds", "tokens_used",
                       "model", "adapter", "route", "specialist", "outcome",
                       "failure_type"]:
            m = re.search(rf"^\- \*\*{field}\*\*:\s*(.+)$", block, re.MULTILINE)
            if m:
                val = m.group(1).strip()
                # skip placeholder comments
                if val.startswith("<!--"):
                    evt[field] = None
                else:
                    evt[field] = val
        if evt.get("event") and evt.get("stage"):
            events.append(evt)
    return events


def _percentile(sorted_vals, p):
    if not sorted_vals:
        return "N/A"
    idx = int(len(sorted_vals) * p / 100)
    idx = min(idx, len(sorted_vals) - 1)
    return sorted_vals[idx]


def _fmt_duration(seconds_str):
    """Format seconds for display."""
    if seconds_str is None:
        return "N/A"
    try:
        s = float(seconds_str)
        if s < 60:
            return f"{s:.0f}s"
        return f"{s/60:.1f}m"
    except (ValueError, TypeError):
        return "N/A"


def aggregate(project_dir):
    tel_dir = telemetry_dir(project_dir)

    if not tel_dir.exists():
        print(f"OK: no telemetry directory at {tel_dir}, nothing to aggregate")
        return

    all_events = []
    task_files = list(tel_dir.glob("*.md"))
    task_files = [f for f in task_files if f.name != "summary.md"]

    if not task_files:
        print("OK: no telemetry event files found, nothing to aggregate")
        return

    for tf in task_files:
        text = _read(tf)
        events = _parse_events(text)
        all_events.extend(events)

    if not all_events:
        print("OK: telemetry files exist but contain no parsed events")
        return

    # Compute metrics
    stage_durations = defaultdict(list)
    stage_outcomes = defaultdict(lambda: defaultdict(int))
    failure_counts = defaultdict(int)
    adapter_tokens = defaultdict(lambda: {"total": 0, "tasks": 0})
    route_counts = defaultdict(int)
    route_durations = defaultdict(list)
    total_tasks = len(task_files)

    for evt in all_events:
        stage = evt.get("stage", "unknown")
        outcome = evt.get("outcome", "unknown")

        # durations
        dur = evt.get("duration_seconds")
        if dur:
            try:
                stage_durations[stage].append(float(dur))
            except (ValueError, TypeError):
                pass

        # outcomes
        if evt.get("event") == "stage_complete":
            stage_outcomes[stage][outcome] += 1

        # failures
        if outcome == "failed" and evt.get("failure_type"):
            failure_counts[evt["failure_type"]] += 1

        # adapter tokens
        adapter = evt.get("adapter", "unknown")
        tokens = evt.get("tokens_used")
        if tokens:
            try:
                adapter_tokens[adapter]["total"] += int(tokens)
                adapter_tokens[adapter]["tasks"] += 1
            except (ValueError, TypeError):
                pass

        # route distribution
        route = evt.get("route", "unknown")
        if evt.get("event") == "stage_complete" and stage == "ship":
            route_counts[route] += 1
        if dur:
            try:
                route_durations[route].append(float(dur))
            except (ValueError, TypeError):
                pass

    # Build summary
    lines = [
        "---",
        "schema: metrics-dashboard/v1",
        f"period: auto",
        f"total_tasks: {total_tasks}",
        f"generated: {datetime.now(timezone.utc).isoformat()}",
        "---",
        "",
        "# ForgeFlow Metrics",
        "",
        "## Stage Duration (p50 / p90)",
        "| Stage | p50 | p90 |",
        "|---|---|---|",
    ]

    for stage in ["clarify", "plan", "execute", "review", "ship"]:
        durs = sorted(stage_durations.get(stage, []))
        p50 = _fmt_duration(_percentile(durs, 50)) if durs else "N/A"
        p90 = _fmt_duration(_percentile(durs, 90)) if durs else "N/A"
        lines.append(f"| {stage} | {p50} | {p90} |")

    lines.extend([
        "",
        "## Failure Distribution",
        "| Failure Type | Count | Rate |",
        "|---|---|---|",
    ])

    total_failures = sum(failure_counts.values()) or 1
    for ftype, count in sorted(failure_counts.items(), key=lambda x: -x[1]):
        rate = f"{count/total_failures*100:.0f}%"
        lines.append(f"| {ftype} | {count} | {rate} |")

    if not failure_counts:
        lines.append("| (none) | 0 | 0% |")

    lines.extend([
        "",
        "## Token Cost by Adapter",
        "| Adapter | Avg tokens/task | Total |",
        "|---|---|---|",
    ])

    for adapter in sorted(adapter_tokens.keys()):
        info = adapter_tokens[adapter]
        avg = info["total"] // max(info["tasks"], 1)
        lines.append(f"| {adapter} | {avg} | {info['total']} |")

    if not adapter_tokens:
        lines.append("| (no token data) | N/A | N/A |")

    lines.extend([
        "",
        "## Worktree Stability",
        "- **Success rate**: N/A (not collected)",
        "- **Avg cleanup time**: N/A (not collected)",
        "",
        "## Route Distribution",
        "| Route | Count | Avg Duration |",
        "|---|---|---|",
    ])

    for route in ["small", "medium", "high", "epic"]:
        count = route_counts.get(route, 0)
        durs = sorted(route_durations.get(route, []))
        avg = _fmt_duration(str(sum(durs) / len(durs))) if durs else "N/A"
        lines.append(f"| {route} | {count} | {avg} |")

    summary_path = tel_dir / "summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"OK: aggregated {len(all_events)} events from {total_tasks} tasks -> {summary_path}")


def main():
    project_dir = ROOT
    if len(sys.argv) > 2 and sys.argv[1] == "--project-dir":
        project_dir = pathlib.Path(sys.argv[2])

    aggregate(project_dir)


if __name__ == "__main__":
    main()
