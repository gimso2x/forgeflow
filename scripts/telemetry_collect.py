#!/usr/bin/env python3
"""Collect telemetry events from .forgeflow/tasks/ artifacts.

Scans task directories for brief.md, plan.md, implementation-notes.md,
review-report.md, and ship-summary.md. Extracts stage metadata and appends
structured events to .forgeflow/telemetry/<task-id>.md.

Usage:
    python3 scripts/telemetry_collect.py [--project-dir DIR]

Creates .forgeflow/telemetry/ if missing. Appends only new events
(not already recorded for the same task+stage+event combination).
"""
import pathlib
import re
import sys
import datetime

ROOT = pathlib.Path(".")


def _read(p):
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def _yaml_field(text, key):
    """Extract a YAML frontmatter field value."""
    m = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
    if m:
        val = m.group(1).strip()
        # strip inline comment
        val = re.sub(r"\s*<!--.*?-->\s*", "", val).strip()
        return val if val else None
    return None


def _yaml_field_block(text, key):
    """Extract a YAML field that may span multiple lines (e.g. scope_boundary)."""
    m = re.search(rf"^{key}:\s*$", text, re.MULTILINE)
    if not m:
        return None
    # grab indented lines after the key
    start = m.end()
    lines = []
    for line in text[start:].split("\n"):
        if line and not line.startswith(" "):
            break
        lines.append(line)
    return "\n".join(lines) if lines else None


def _yaml_nested(text, parent, child):
    """Extract parent.child from YAML frontmatter."""
    block = _yaml_field_block(text, parent)
    if block is None:
        return None
    m = re.search(rf"^\s+{child}:\s*(.+)$", block, re.MULTILINE)
    if m:
        val = m.group(1).strip()
        val = re.sub(r"\s*<!--.*?-->\s*", "", val).strip()
        return val if val else None
    return None


def _extract_adapter():
    """Best-effort adapter detection from env markers or directory."""
    # Check for adapter indicators in project dir
    if (ROOT / ".claude-plugin").exists() or (ROOT / ".claude").exists():
        return "claude"
    if (ROOT / ".codex-plugin").exists():
        return "codex"
    if (ROOT / "GEMINI.md").exists():
        return "gemini"
    if (ROOT / ".cursor-plugin").exists():
        return "cursor"
    return "unknown"


def _extract_route(brief_text):
    """Extract route from brief.md frontmatter."""
    route = _yaml_field(brief_text, "route")
    if route:
        return route.strip()
    # fallback: look in body
    m = re.search(r"\b(small|medium|high|epic)\b", brief_text)
    return m.group(1) if m else "unknown"


def _extract_specialist(brief_text):
    """Extract specialist primary from brief.md frontmatter."""
    primary = _yaml_nested(brief_text, "specialist", "primary")
    if primary:
        return primary.strip()
    return "none"


def _extract_outcome(artifact_text, stage):
    """Extract outcome from stage artifact."""
    text_lower = artifact_text.lower()
    if stage == "review":
        if "approved" in text_lower:
            return "success"
        if "changes_requested" in text_lower or "blocked" in text_lower:
            return "partial"
    if stage == "ship":
        if "merged" in text_lower or "shipped" in text_lower:
            return "success"
    # generic
    if "fail" in text_lower:
        return "failed"
    if "partial" in text_lower:
        return "partial"
    return "success"


def _existing_events(telemetry_file):
    """Parse already-recorded stage+event combos from telemetry file."""
    seen = set()
    if not telemetry_file.exists():
        return seen
    text = _read(telemetry_file)
    # look for event blocks: ### <timestamp> followed by - **event**: ...
    blocks = re.split(r"^### ", text, flags=re.MULTILINE)
    for block in blocks[1:]:  # skip preamble
        evt = re.search(r"^\- \*\*event\*\*:\s*(\S+)", block, re.MULTILINE)
        stage = re.search(r"^\- \*\*stage\*\*:\s*(\S+)", block, re.MULTILINE)
        if evt and stage:
            seen.add((evt.group(1), stage.group(1)))
    return seen


def _build_event_block(event, stage, route, specialist, adapter, outcome, ts):
    """Build a single telemetry event markdown block."""
    lines = [
        f"### {ts}",
        f"- **event**: {event}",
        f"- **stage**: {stage}",
        f"- **duration_seconds**: <!-- N -->",
        f"- **tokens_used**: <!-- N -->",
        f"- **model**: <!-- model id -->",
        f"- **adapter**: {adapter}",
        f"- **route**: {route}",
        f"- **specialist**: {specialist}",
        f"- **outcome**: {outcome}",
        f"- **failure_type**: <!-- null or category -->",
    ]
    return "\n".join(lines)


def _ensure_header(telemetry_file, task_id):
    """Ensure telemetry file has YAML frontmatter and header."""
    if telemetry_file.exists():
        return
    header = (
        "---\n"
        f"schema: telemetry-event/v1\n"
        f"task_id: {task_id}\n"
        "---\n\n"
        "# Telemetry Event Log\n\n"
        "## Events\n"
    )
    telemetry_file.parent.mkdir(parents=True, exist_ok=True)
    telemetry_file.write_text(header, encoding="utf-8")


def collect_task(task_dir, tel_dir):
    """Collect telemetry from a single task directory."""
    task_id = task_dir.name
    brief_path = task_dir / "brief.md"

    if not brief_path.exists():
        return 0

    brief_text = _read(brief_path)
    route = _extract_route(brief_text)
    specialist = _extract_specialist(brief_text)
    adapter = _extract_adapter()

    # check for scope boundary info
    boundary_status = _yaml_nested(brief_text, "scope_boundary", "boundary_status")

    telemetry_file = tel_dir / f"{task_id}.md"
    _ensure_header(telemetry_file, task_id)
    seen = _existing_events(telemetry_file)

    events_added = 0
    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Stage mapping: artifact -> (stage, event_type)
    stages = [
        ("brief.md", "clarify", "stage_complete"),
        ("plan.md", "plan", "stage_complete"),
        ("implementation-notes.md", "execute", "stage_complete"),
        ("review-report.md", "review", "stage_complete"),
        ("ship-summary.md", "ship", "stage_complete"),
    ]

    for artifact_name, stage, event in stages:
        artifact_path = task_dir / artifact_name
        if not artifact_path.exists():
            continue
        if (event, stage) in seen:
            continue

        artifact_text = _read(artifact_path)
        outcome = _extract_outcome(artifact_text, stage)

        block = _build_event_block(event, stage, route, specialist, adapter, outcome, ts)
        # append to file
        with open(telemetry_file, "a", encoding="utf-8") as f:
            f.write("\n" + block + "\n")
        events_added += 1

    # boundary_alert event
    if boundary_status and boundary_status == "exceeds":
        if ("boundary_alert", "clarify") not in seen:
            block = _build_event_block(
                "boundary_alert", "clarify", route, specialist, adapter, "partial", ts
            )
            with open(telemetry_file, "a", encoding="utf-8") as f:
                f.write("\n" + block + "\n")
            events_added += 1

    return events_added


def main():
    global ROOT
    project_dir = ROOT
    if len(sys.argv) > 2 and sys.argv[1] == "--project-dir":
        ROOT = pathlib.Path(sys.argv[2])
        project_dir = ROOT

    tasks_dir = project_dir / ".forgeflow" / "tasks"
    tel_dir = project_dir / ".forgeflow" / "telemetry"

    if not tasks_dir.exists():
        print("OK: no .forgeflow/tasks/ directory found, nothing to collect")
        return

    tel_dir.mkdir(parents=True, exist_ok=True)

    total_events = 0
    total_tasks = 0
    for task_dir in sorted(tasks_dir.iterdir()):
        if not task_dir.is_dir():
            continue
        n = collect_task(task_dir, tel_dir)
        if n > 0:
            total_tasks += 1
            total_events += n

    if total_events > 0:
        print(f"OK: collected {total_events} events from {total_tasks} tasks -> .forgeflow/telemetry/")
    else:
        print("OK: telemetry up-to-date, no new events")


if __name__ == "__main__":
    main()
