#!/usr/bin/env python3
"""Minimal ForgeFlow local loop CLI.

Reads markdown task artifacts and computes/records the next actionable item.
No provider/agent invocation. Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import shlex
import subprocess
import sys
from pathlib import Path

ALLOWED_STATUSES = {"pending", "in_progress", "blocked", "done", "discarded"}
TASK_HEADING_RE = re.compile(r"^###\s+(Task\s+\d+:\s+.+?)\s*$")
FIELD_RE = re.compile(r"^- \*\*(Status|Assignee|Claim Marker|Evidence Refs|Blocker|Retry Count)\*\*:\s*(.*)$")


class LoopError(RuntimeError):
    pass


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise LoopError(f"missing required artifact: {path.name}") from exc


def task_paths(task_dir: Path) -> tuple[Path, Path]:
    return task_dir / "ledger.md", task_dir / "checkpoint.md"


def artifact_paths(task_dir: Path) -> dict[str, Path]:
    return {
        "brief": task_dir / "brief.md",
        "plan": task_dir / "plan.md",
        "ledger": task_dir / "ledger.md",
        "checkpoint": task_dir / "checkpoint.md",
        "implementation_notes": task_dir / "implementation-notes.md",
    }


def parse_tasks(ledger_text: str) -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line_no, line in enumerate(ledger_text.splitlines(), start=1):
        heading = TASK_HEADING_RE.match(line)
        if heading:
            current = {"heading": heading.group(1), "line": str(line_no)}
            tasks.append(current)
            continue
        if current is None:
            continue
        field = FIELD_RE.match(line)
        if field:
            key = field.group(1).lower().replace(" ", "_")
            current[key] = field.group(2).strip()
    return tasks


def parse_checkpoint(checkpoint_text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    current_heading: str | None = None
    collected: list[str] = []

    def flush() -> None:
        nonlocal collected, current_heading
        if current_heading:
            body = "\n".join(line for line in collected if not line.strip().startswith("<!--")).strip()
            result[current_heading] = body
        collected = []

    for line in checkpoint_text.splitlines():
        if line.startswith("## "):
            flush()
            current_heading = line[3:].strip().lower().replace(" ", "_")
        else:
            collected.append(line)
    flush()
    return result


def first_actionable(tasks: list[dict[str, str]], checkpoint: dict[str, str]) -> dict[str, str] | None:
    pointer = checkpoint.get("resume_pointer", "")
    if pointer:
        for task in tasks:
            if task["heading"] in pointer or task["heading"].lower().replace(" ", "-").replace(":", "") in pointer.lower():
                if task.get("status", "pending") in {"pending", "in_progress"}:
                    return task
    for status in ("in_progress", "pending"):
        for task in tasks:
            if task.get("status", "pending") == status:
                return task
    return None


def load_state(task_dir: Path) -> tuple[Path, Path, list[dict[str, str]], dict[str, str]]:
    ledger_path, checkpoint_path = task_paths(task_dir)
    ledger_text = read_text(ledger_path)
    checkpoint_text = read_text(checkpoint_path)
    tasks = parse_tasks(ledger_text)
    if not tasks:
        raise LoopError("ledger.md has no '### Task N:' execution tracking rows")
    checkpoint = parse_checkpoint(checkpoint_text)
    return ledger_path, checkpoint_path, tasks, checkpoint


def print_status(task_dir: Path) -> int:
    _ledger_path, _checkpoint_path, tasks, checkpoint = load_state(task_dir)
    counts = {status: 0 for status in ALLOWED_STATUSES}
    unknown: list[str] = []
    for task in tasks:
        status = task.get("status", "pending") or "pending"
        if status in counts:
            counts[status] += 1
        else:
            unknown.append(f"{task['heading']}={status}")
    next_task = first_actionable(tasks, checkpoint)
    print(f"task_dir: {task_dir}")
    print(f"tasks: {len(tasks)}")
    for status in sorted(counts):
        print(f"{status}: {counts[status]}")
    if unknown:
        print("unknown_status: " + ", ".join(unknown))
    print("checkpoint_stage: " + (checkpoint.get("current_stage") or "unknown"))
    print("resume_pointer: " + (checkpoint.get("resume_pointer") or "none"))
    print("next: " + (format_task(next_task) if next_task else "none"))
    return 1 if unknown else 0


def format_task(task: dict[str, str] | None) -> str:
    if task is None:
        return "none"
    return (
        f"{task['heading']} | status={task.get('status', 'pending') or 'pending'} "
        f"retry={task.get('retry_count', '0') or '0'} assignee={task.get('assignee', 'worker') or 'worker'}"
    )


def print_next(task_dir: Path) -> int:
    _ledger_path, _checkpoint_path, tasks, checkpoint = load_state(task_dir)
    task = first_actionable(tasks, checkpoint)
    print(format_task(task))
    return 0 if task else 1


def update_task_block(ledger_text: str, task_heading: str, updates: dict[str, str]) -> str:
    lines = ledger_text.splitlines()
    in_target = False
    touched = set()
    out: list[str] = []
    for line in lines:
        heading = TASK_HEADING_RE.match(line)
        if heading:
            in_target = heading.group(1) == task_heading
        if in_target:
            field = FIELD_RE.match(line)
            if field:
                label = field.group(1)
                key = label.lower().replace(" ", "_")
                if key in updates:
                    line = f"- **{label}**: {updates[key]}"
                    touched.add(key)
        out.append(line)
    missing = set(updates) - touched
    if missing:
        raise LoopError(f"task row missing fields: {', '.join(sorted(missing))}")
    return "\n".join(out) + "\n"


def record(task_dir: Path, status: str, evidence: str, task_name: str | None, blocker: str | None) -> int:
    if status not in ALLOWED_STATUSES:
        raise LoopError(f"invalid status '{status}', expected one of: {', '.join(sorted(ALLOWED_STATUSES))}")
    ledger_path, checkpoint_path, tasks, checkpoint = load_state(task_dir)
    task = None
    if task_name:
        for candidate in tasks:
            if task_name in candidate["heading"]:
                task = candidate
                break
        if task is None:
            raise LoopError(f"task not found: {task_name}")
    else:
        task = first_actionable(tasks, checkpoint)
    if task is None:
        raise LoopError("no actionable task to record")
    if status == "done" and not evidence:
        raise LoopError("--evidence is required when recording done")
    if status == "blocked" and not (blocker or evidence):
        raise LoopError("--blocker or --evidence is required when recording blocked")

    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    evidence_ref = evidence or "none"
    blocker_text = blocker or ("none" if status != "blocked" else evidence_ref)
    updates = {
        "status": status,
        "evidence_refs": evidence_ref,
        "blocker": blocker_text,
    }
    ledger_text = read_text(ledger_path)
    ledger_path.write_text(update_task_block(ledger_text, task["heading"], updates), encoding="utf-8")

    checkpoint_text = read_text(checkpoint_path)
    next_line = f"{task['heading']} status={status} retry={task.get('retry_count', '0') or '0'} owner={task.get('assignee', 'worker') or 'worker'} next_update=implementation-notes.md#Evidence"
    checkpoint_text = replace_section(checkpoint_text, "Resume Pointer", next_line)
    checkpoint_text = replace_section(checkpoint_text, "Last Verified Evidence", f"{evidence_ref} recorded_at={now}")
    checkpoint_text = replace_section(checkpoint_text, "Status", "blocked" if status == "blocked" else "in_progress")
    checkpoint_path.write_text(checkpoint_text, encoding="utf-8")
    print(f"recorded: {format_task(task)} -> status={status} evidence={evidence_ref}")
    return 0


def build_adapter_prompt(task_dir: Path, task: dict[str, str]) -> str:
    paths = artifact_paths(task_dir)
    sections = [
        "You are an agent adapter running one ForgeFlow task.",
        "Do the task, but do not claim success without verifiable evidence.",
        f"Active task: {format_task(task)}",
    ]
    for name in ("brief", "plan", "ledger", "checkpoint"):
        path = paths[name]
        if path.exists():
            sections.append(f"\n--- {path.name} ---\n{read_text(path)}")
    return "\n".join(sections).strip() + "\n"


def render_command(command_template: str, task_dir: Path, prompt_path: Path) -> list[str]:
    rendered = command_template.format(task_dir=str(task_dir), prompt=str(prompt_path))
    return shlex.split(rendered)


def append_agent_run(
    task_dir: Path,
    task: dict[str, str],
    adapter: str,
    prompt_path: Path,
    proc: subprocess.CompletedProcess[str],
    verify: subprocess.CompletedProcess[str] | None,
) -> None:
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    notes_path = artifact_paths(task_dir)["implementation_notes"]
    notes_path.touch(exist_ok=True)
    verification = "not_run" if verify is None else f"exit={verify.returncode}\nstdout:\n{verify.stdout.strip()}\nstderr:\n{verify.stderr.strip()}"
    block = (
        f"\n\n## Agent Adapter Run - {now}\n"
        f"- task: {task['heading']}\n"
        f"- adapter: {adapter}\n"
        f"- prompt: {prompt_path.name}\n"
        f"- adapter_exit: {proc.returncode}\n"
        f"- verification: {verification}\n\n"
        f"### Adapter stdout\n```text\n{proc.stdout.strip()}\n```\n\n"
        f"### Adapter stderr\n```text\n{proc.stderr.strip()}\n```\n"
    )
    notes_path.write_text(notes_path.read_text(encoding="utf-8") + block, encoding="utf-8")

    ledger_path = artifact_paths(task_dir)["ledger"]
    verify_label = "not_run" if verify is None else str(verify.returncode)
    ledger_path.write_text(
        read_text(ledger_path)
        + f"\n## Agent Runs\n- {now} task={task['heading']} adapter={adapter} adapter_exit={proc.returncode} verification={verify_label} notes=implementation-notes.md\n",
        encoding="utf-8",
    )


def run_adapter(task_dir: Path, adapter: str, command_template: str, verify_command: str | None) -> int:
    _ledger_path, _checkpoint_path, tasks, checkpoint = load_state(task_dir)
    task = first_actionable(tasks, checkpoint)
    if task is None:
        raise LoopError("no actionable task for adapter run")
    prompt_path = task_dir / "agent-prompt.md"
    prompt_path.write_text(build_adapter_prompt(task_dir, task), encoding="utf-8")

    proc = subprocess.run(
        render_command(command_template, task_dir, prompt_path),
        cwd=task_dir,
        text=True,
        input=prompt_path.read_text(encoding="utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    verify = None
    if verify_command:
        verify = subprocess.run(
            render_command(verify_command, task_dir, prompt_path),
            cwd=task_dir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    append_agent_run(task_dir, task, adapter, prompt_path, proc, verify)

    if proc.returncode != 0:
        return record(task_dir, "blocked", f"adapter={adapter} exit={proc.returncode} notes=implementation-notes.md", task["heading"], "adapter command failed")
    if verify is not None and verify.returncode != 0:
        return record(task_dir, "blocked", f"adapter={adapter} verification_exit={verify.returncode} notes=implementation-notes.md", task["heading"], "verification command failed")
    evidence = f"adapter={adapter} notes=implementation-notes.md"
    if verify is not None:
        evidence += f" verification_exit={verify.returncode}"
    return record(task_dir, "done", evidence, task["heading"], None)


def replace_section(text: str, heading: str, body: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    marker = f"## {heading}"
    replaced = False
    while i < len(lines):
        out.append(lines[i])
        if lines[i].strip() == marker:
            i += 1
            # Preserve leading comments, then replace non-heading body until next section.
            while i < len(lines) and lines[i].strip().startswith("<!--"):
                out.append(lines[i])
                i += 1
            out.append(body)
            while i < len(lines) and not lines[i].startswith("## "):
                i += 1
            replaced = True
            continue
        i += 1
    if not replaced:
        out.extend([marker, body])
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="forgeflow-loop")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "next"):
        p = sub.add_parser(name)
        p.add_argument("--task-dir", required=True, type=Path)
    rec = sub.add_parser("record")
    rec.add_argument("--task-dir", required=True, type=Path)
    rec.add_argument("--status", required=True, choices=sorted(ALLOWED_STATUSES))
    rec.add_argument("--evidence", default="")
    rec.add_argument("--task", default=None, help="substring of task heading to update")
    rec.add_argument("--blocker", default=None)
    run = sub.add_parser("run-adapter")
    run.add_argument("--task-dir", required=True, type=Path)
    run.add_argument("--adapter", required=True, help="adapter label, for example claude/codex/gemini/stub")
    run.add_argument("--command", dest="adapter_command", required=True, help="adapter command template; receives prompt on stdin; supports {task_dir} and {prompt}")
    run.add_argument("--verify-command", default=None, help="verification command template; supports {task_dir} and {prompt}")
    args = parser.parse_args(argv)
    try:
        task_dir = args.task_dir.expanduser().resolve()
        if args.command == "status":
            return print_status(task_dir)
        if args.command == "next":
            return print_next(task_dir)
        if args.command == "record":
            return record(task_dir, args.status, args.evidence, args.task, args.blocker)
        if args.command == "run-adapter":
            return run_adapter(task_dir, args.adapter, args.adapter_command, args.verify_command)
    except LoopError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
