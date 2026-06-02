#!/usr/bin/env python3
"""Generate a lightweight ForgeFlow surface-usage audit.

The audit answers the maintainer question: which entrypoints and artifacts are
actually used in the last 2-4 weeks, and which documented surfaces are mostly
inventory cost?

Usage:
    python3 scripts/surface_usage_audit.py [--project-dir DIR] [--days 28]

Output:
    ~/.forgeflow/projects/<project-slug>/telemetry/surface-usage-audit.md by default
"""
import argparse
import pathlib
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone

import forgeflow_storage

ENTRYPOINTS = [
    "clarify",
    "plan",
    "execute",
    "review",
    "ship",
    "config",
    "long-run",
    "benchmark",
]

ARTIFACTS = [
    "brief.md",
    "plan.md",
    "ledger.md",
    "checkpoint.md",
    "implementation-notes.md",
    "review-report.md",
    "ship-summary.md",
    "roadmap.md",
    "eval-record.md",
    "evolution-rule.md",
    "telemetry-event.md",
    "metrics-dashboard.md",
]

CORE = {"clarify", "plan", "execute", "review", "ship"}
SUPPORT = {"config", "long-run"}
UTILITY = {"benchmark"}


def _run_git(project_dir, args):
    proc = subprocess.run(
        ["git", *args],
        cwd=str(project_dir),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout


def _count_entrypoints(text):
    counts = Counter()
    for name in ENTRYPOINTS:
        pattern = re.compile(rf"/(?:forgeflow:)?{re.escape(name)}\b")
        counts[name] += len(pattern.findall(text))
    return counts


def _count_artifacts(project_dir):
    counts = Counter()
    tasks_dir = forgeflow_storage.tasks_dir(project_dir)
    if tasks_dir.exists():
        for artifact in ARTIFACTS:
            counts[artifact] = sum(1 for _ in tasks_dir.glob(f"**/{artifact}"))
    tel_dir = forgeflow_storage.telemetry_dir(project_dir)
    if tel_dir.exists():
        counts["telemetry-event.md"] += sum(1 for p in tel_dir.glob("*.md") if p.name != "summary.md")
        counts["metrics-dashboard.md"] += int((tel_dir / "summary.md").exists())
    return counts


def _inventory_only(entry_counts, artifact_counts):
    notes = []
    for name in ENTRYPOINTS:
        if entry_counts[name] == 0:
            tier = "core" if name in CORE else "support" if name in SUPPORT else "utility"
            notes.append(f"- `{name}` ({tier}): no slash mentions in the selected git window")
    for artifact in ARTIFACTS:
        if artifact_counts[artifact] == 0:
            notes.append(f"- `{artifact}`: no tracked task/telemetry artifact instance found")
    return notes


def _render_table(counter, keys):
    lines = ["| Item | Count |", "|---|---:|"]
    for key in keys:
        lines.append(f"| `{key}` | {counter[key]} |")
    return lines


def audit(project_dir, days):
    since = f"{days} days ago"
    log_text = _run_git(project_dir, ["log", f"--since={since}", "--all", "--pretty=format:%s%n%b"])
    diff_text = _run_git(project_dir, ["log", f"--since={since}", "--all", "--name-only", "--pretty=format:"])
    combined = f"{log_text}\n{diff_text}"

    entry_counts = _count_entrypoints(combined)
    artifact_counts = _count_artifacts(project_dir)
    inventory_notes = _inventory_only(entry_counts, artifact_counts)

    top_entry = entry_counts.most_common(1)[0] if entry_counts else ("none", 0)
    active_core = sum(1 for name in CORE if entry_counts[name] > 0)
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    lines = [
        "---",
        "schema: surface-usage-audit/v1",
        f"period_days: {days}",
        f"generated: {generated}",
        "---",
        "",
        "# ForgeFlow Surface Usage Audit",
        "",
        "## Summary",
        f"- **Window**: last {days} days from git history plus current resolved task/telemetry artifacts",
        f"- **Most mentioned entrypoint**: `{top_entry[0]}` ({top_entry[1]})",
        f"- **Core entrypoints with recent slash mentions**: {active_core}/5",
        "- **Interpretation rule**: treat zero counts as a maintenance-review signal, not automatic removal approval.",
        "",
        "## Entrypoint Mentions",
        *_render_table(entry_counts, ENTRYPOINTS),
        "",
        "## Artifact Instances",
        *_render_table(artifact_counts, ARTIFACTS),
        "",
        "## Low-use / Inventory-only Signals",
    ]
    if inventory_notes:
        lines.extend(inventory_notes)
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## Maintainer Checklist",
        "- [ ] Confirm the top 2-3 entrypoints match actual operator behavior.",
        "- [ ] Check whether low-use support/utility surfaces still justify their README/skill footprint.",
        "- [ ] Verify Core still funnels work through clarify → plan/execute → review → ship.",
        "- [ ] Convert repeated review findings into Harness Follow-up items when the same issue recurs.",
        "- [ ] If a surface remains low-use for two consecutive audits, either document why it stays or propose removal/merge.",
    ])

    out_dir = forgeflow_storage.telemetry_dir(project_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "surface-usage-audit.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: wrote {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--days", type=int, default=28)
    args = parser.parse_args()
    audit(pathlib.Path(args.project_dir), args.days)


if __name__ == "__main__":
    main()
