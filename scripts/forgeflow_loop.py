#!/usr/bin/env python3
"""Minimal ForgeFlow local loop CLI.

Reads markdown task artifacts, queues phone-originated requests, and computes/records the next actionable item.
Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

ALLOWED_STATUSES = {"pending", "in_progress", "blocked", "done", "discarded"}
PROTECTED_PATHS = (".git", ".forgeflow")
TASK_HEADING_RE = re.compile(r"^###\s+(Task\s+\d+:\s+.+?)\s*$")
FIELD_RE = re.compile(r"^- \*\*(Status|Assignee|Claim Marker|Evidence Refs|Blocker|Retry Count)\*\*:\s*(.*)$")
FANOUT_RE = re.compile(r"^- (?P<stamp>\S+) task=(?P<task>.+?) worker=(?P<worker>\S+) branch=(?P<branch>\S+) owner=(?P<owner>\S+) status=(?P<status>\S+)")


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


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.lower()).strip("-._")
    return slug[:80] or "worker"


def path_owner(task: dict[str, str]) -> str:
    owner = (task.get("claim_marker") or "").strip()
    if not owner or owner == "none":
        owner = slugify(task["heading"])
    owner = owner.strip("/")
    if not owner or owner.startswith(PROTECTED_PATHS) or "/.git" in owner or "/.forgeflow" in owner:
        raise LoopError(f"protected path ownership is not allowed: {owner or 'empty'}")
    return owner


def paths_conflict(left: str, right: str) -> bool:
    left = left.rstrip("/")
    right = right.rstrip("/")
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def fanout_candidates(tasks: list[dict[str, str]], max_workers: int) -> list[tuple[dict[str, str], str]]:
    selected: list[tuple[dict[str, str], str]] = []
    for task in tasks:
        if task.get("status", "pending") not in {"pending", "in_progress"}:
            continue
        owner = path_owner(task)
        for other_task, other_owner in selected:
            if paths_conflict(owner, other_owner):
                raise LoopError(f"conflicting path ownership: {task['heading']}={owner} overlaps {other_task['heading']}={other_owner}")
        selected.append((task, owner))
        if len(selected) >= max_workers:
            break
    return selected


def git(project_root: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project_root), *args],
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


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


def selected_task(task_dir: Path) -> dict[str, str]:
    _ledger_path, _checkpoint_path, tasks, checkpoint = load_state(task_dir)
    task = first_actionable(tasks, checkpoint)
    if task is None:
        raise LoopError("no actionable task")
    return task


def run_adapter(task_dir: Path, adapter: str, command_template: str, verify_command: str | None) -> int:
    try:
        task = selected_task(task_dir)
    except LoopError as exc:
        raise LoopError("no actionable task for adapter run") from exc
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



def step_supervisor(task_dir: Path, adapter: str, command_template: str | None, verify_command: str | None) -> int:
    task = selected_task(task_dir)
    adapter_command = command_template or "python3 -c 'import sys; data=sys.stdin.read(); print(\"stub adapter received prompt_chars=\" + str(len(data)))'"
    print(f"step: selected={format_task(task)}")
    print(f"step: adapter={adapter}")
    if verify_command:
        print(f"step: verify_command={verify_command}")
    else:
        print("step: verify_command=not_run")
    result = run_adapter(task_dir, adapter, adapter_command, verify_command)
    print(f"step: completed exit={result}")
    return result



def recommend_route(request: str) -> tuple[str, str]:
    text = request.lower()
    high_markers = ("rewrite", "refactor", "migration", "security", "auth", "database", "schema", "deploy", "architecture", "전체", "대규모", "마이그레이션")
    small_markers = ("typo", "문구", "오타", "버튼", "색", "copy", "readme", "docs", "이거", "고쳐", "fix")
    if len(request) > 240 or any(marker in text for marker in high_markers):
        return "high", "larger scope/risk marker detected; user may override after queue intake"
    if len(request) <= 80 or any(marker in text for marker in small_markers):
        return "small", "terse phone-originated request; safe default is smallest reviewable route"
    return "medium", "moderate natural-language request; user may override after queue intake"


def draft_brief(task_id: str, request: str, route: str, route_reason: str) -> str:
    files_limit = {"small": "3", "medium": "8", "high": "20", "epic": "unlimited"}[route]
    return f"""---
schema: brief/v2
task_id: {task_id}
route: {route}
specialist:
  primary: none
  secondary: none
  rationale: phone queue draft; refine during clarify if needed
scope_boundary:
  files_planned: 1
  files_limit: {files_limit}
  boundary_status: within
ambiguity:
  objective: 4
  scope: 5
  constraints: 5
  acceptance: 5
  score: 0.5
  rounds: 0
  status: bounded_assumption
---

# 컨텍스트 브리프 (Context Brief)

## 목표 (Objective)
{request}

## 라우트 (Route)
{route}

## 라우트 근거 (Route Rationale)
{route_reason}

## 범위 포함 (In Scope)
- Phone queue intake로 들어온 요청을 clarify 가능한 작업 초안으로 보존합니다.
- 다음 단계에서 objective/scope/acceptance를 보강합니다.

## 범위 제외 (Out of Scope)
- 이 초안만으로 구현 성공을 주장하지 않습니다.
- 사용자 승인 없는 push/release/external side effect는 제외합니다.

## 인수 기준 (Acceptance Criteria)
- [ ] 원문 요청이 보존되어 있다.
- [ ] route recommendation이 표시되고 override 가능하다.
- [ ] 검증/완료 보고는 Telegram에서 읽기 쉬운 evidence-first 요약으로 남긴다.

## Goal Contract
- **성공 기준 (Success Criteria):** 요청이 실행 가능한 ForgeFlow task draft로 전환된다.
- **필수 증거 (Evidence Required):** brief.md, ledger.md, checkpoint.md 파일 존재와 queue intake 로그.
- **인정된 리스크 (Accepted Risks):** 짧은 입력은 모호할 수 있어 clarify에서 보정한다.
- **명시적 제외 (Explicit Exclusions):** 이 단계는 실제 구현을 실행하지 않는다.

## 가정과 해석 (Assumptions and Interpretation)
- **Selected interpretation**: {request}
- **Assumptions**: phone-originated terse request; route can be overridden.
- **Open ambiguity**: exact files, final acceptance criteria, verification command.
- **Why safe to proceed**: only task artifacts are written; no external side effects.
"""


def queue_request(queue_root: Path, request: str, task_id: str | None, route_override: str | None) -> int:
    request = request.strip()
    if not request:
        raise LoopError("request text is required")
    recommended, reason = recommend_route(request)
    route = route_override or recommended
    if route not in {"small", "medium", "high", "epic"}:
        raise LoopError("route must be one of: small, medium, high, epic")
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    task_id = task_id or f"phone-{stamp}-{slugify(request)[:32]}"
    task_dir = queue_root.expanduser().resolve() / task_id
    if task_dir.exists():
        raise LoopError(f"task already exists: {task_dir}")
    task_dir.mkdir(parents=True)
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    (task_dir / "brief.md").write_text(draft_brief(task_id, request, route, reason), encoding="utf-8")
    (task_dir / "ledger.md").write_text(f"""---
schema: ledger/v1
task_id: {task_id}
route: {route}
total_items: 1
---

# Ledger

## Queue Intake
- {now} source=phone request={request!r} recommended_route={recommended} selected_route={route} override={'yes' if route_override else 'no'}

## Execution Tracking

### Task 1: Clarify phone request
- **Plan Step**: clarify
- **Status**: pending
- **Assignee**: owner
- **Claim Marker**: brief.md
- **Evidence Refs**: queue_intake={now}
- **Blocker**: none
- **Retry Count**: 0
""", encoding="utf-8")
    (task_dir / "checkpoint.md").write_text(f"""# Checkpoint

## Current Stage
clarify

## Status
in_progress

## Active Task
Task 1

## Resume Pointer
ledger.md#task-1-clarify-phone-request status=pending retry=0 owner=owner next_update=brief.md

## Next Action
Review brief.md, accept or override route, then run /forgeflow:clarify.

## Last Verified Evidence
queue_intake={now} task_dir={task_dir}
""", encoding="utf-8")
    (task_dir / "implementation-notes.md").write_text(f"# Implementation Notes\n\n## Queue Intake - {now}\n- request: {request}\n- recommended_route: {recommended}\n- selected_route: {route}\n- overrideable: yes\n", encoding="utf-8")
    print(f"queued: {task_id}")
    print(f"task_dir: {task_dir}")
    print(f"recommended_route: {recommended}")
    print(f"selected_route: {route}")
    print("telegram_summary: 요청 초안 생성 완료. route는 필요하면 override 가능합니다. 증거: brief.md, ledger.md, checkpoint.md")
    return 0


def normalize_learning_key(text: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9가-힣_.:/-]+", " ", text.lower()).strip()
    words = [word for word in normalized.split() if word not in {"none", "n/a", "the", "and", "or"}]
    return " ".join(words[:12]) or "unknown"


def read_learning_state(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LoopError(f"invalid learning state JSON: {path}") from exc
    if not isinstance(data, dict):
        raise LoopError(f"learning state must be a JSON object: {path}")
    return data


def write_learning_state(path: Path, data: dict[str, dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def increment_learning(data: dict[str, dict[str, object]], category: str, key: str, evidence: str, task_id: str, now: str) -> None:
    bucket = data.setdefault(category, {})
    item = bucket.setdefault(key, {"count": 0, "examples": [], "candidate_only": True, "human_approval_required": True})
    item["count"] = int(item.get("count", 0)) + 1
    examples = list(item.get("examples", []))
    examples.append({"task_id": task_id, "evidence": evidence, "captured_at": now})
    item["examples"] = examples[-5:]
    item["candidate_only"] = True
    item["human_approval_required"] = True


def capture_learning(task_dir: Path, learning_root: Path) -> int:
    ledger_path, _checkpoint_path, tasks, _checkpoint = load_state(task_dir)
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    state_path = learning_root.expanduser().resolve() / "learning-candidates.json"
    state = read_learning_state(state_path)
    captured = 0
    task_id = task_dir.name
    for task in tasks:
        status = task.get("status", "pending")
        blocker = task.get("blocker", "")
        evidence = task.get("evidence_refs", "")
        if status == "blocked" and blocker and blocker.lower() != "none":
            increment_learning(state, "blockers", normalize_learning_key(blocker), blocker, task_id, now)
            captured += 1
        if status == "done" and evidence and evidence.lower() != "none":
            increment_learning(state, "evidence_patterns", normalize_learning_key(evidence), evidence, task_id, now)
            captured += 1
    write_learning_state(state_path, state)
    notes_path = artifact_paths(task_dir)["implementation_notes"]
    notes_path.touch(exist_ok=True)
    notes_path.write_text(
        read_text(notes_path)
        + f"\n## Learning Capture - {now}\n"
        + f"- state: {state_path}\n"
        + f"- captured: {captured}\n"
        + "- canonical_promotion: human_approval_required\n",
        encoding="utf-8",
    )
    ledger_path.write_text(
        read_text(ledger_path)
        + f"\n## Learning Capture\n- {now} state={state_path} captured={captured} canonical_promotion=human_approval_required\n",
        encoding="utf-8",
    )
    print(f"learning_state: {state_path}")
    print(f"captured: {captured}")
    print("canonical_promotion: human_approval_required")
    return 0


def preflight_learning(learning_root: Path, request: str, min_count: int) -> int:
    state_path = learning_root.expanduser().resolve() / "learning-candidates.json"
    state = read_learning_state(state_path)
    request_key = normalize_learning_key(request)
    warnings: list[str] = []
    for category in ("blockers", "evidence_patterns"):
        bucket = state.get(category, {})
        if not isinstance(bucket, dict):
            continue
        for key, item in bucket.items():
            if not isinstance(item, dict) or int(item.get("count", 0)) < min_count:
                continue
            if key in request_key or any(part and part in request_key for part in key.split()[:3]):
                warnings.append(f"{category}:{key} count={item.get('count')} candidate_only={item.get('candidate_only', True)}")
    if warnings:
        print("preflight_warnings:")
        for warning in warnings:
            print(f"- {warning}")
        print("canonical_promotion: human_approval_required")
        return 1
    print("preflight_warnings: none")
    return 0

def worktree_fanout(task_dir: Path, project_root: Path, worker_root: Path, max_workers: int) -> int:
    ledger_path, _checkpoint_path, tasks, _checkpoint = load_state(task_dir)
    candidates = fanout_candidates(tasks, max_workers)
    if not candidates:
        raise LoopError("no pending or in-progress tasks available for fanout")
    worker_root.mkdir(parents=True, exist_ok=True)
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    lines = ["\n## Worktree Fanout"]
    created = 0
    for task, owner in candidates:
        slug = slugify(task["heading"])
        worker_path = worker_root / slug
        branch = f"forgeflow/{slug}"
        if worker_path.exists():
            raise LoopError(f"worker path already exists: {worker_path}")
        proc = git(project_root, "worktree", "add", "-b", branch, str(worker_path), "HEAD")
        if proc.returncode != 0:
            raise LoopError(f"git worktree add failed for {task['heading']}: {proc.stderr.strip()}")
        created += 1
        lines.append(f"- {now} task={slug} worker={worker_path} branch={branch} owner={owner} status=created")
    ledger_path.write_text(read_text(ledger_path) + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"fanout: created={created} worker_root={worker_root}")
    return 0


def parse_fanout_entries(ledger_text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in ledger_text.splitlines():
        match = FANOUT_RE.match(line)
        if match:
            entries.append(match.groupdict())
    return entries


def changed_paths(worker: Path) -> list[str]:
    add_intent = git(worker, "add", "-N", ".")
    if add_intent.returncode != 0:
        raise LoopError(f"git add -N failed in {worker}: {add_intent.stderr.strip()}")
    proc = git(worker, "diff", "--name-only", "HEAD")
    if proc.returncode != 0:
        raise LoopError(f"git diff failed in {worker}: {proc.stderr.strip()}")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def validate_worker_changes(entry: dict[str, str], paths: list[str]) -> None:
    owner = entry["owner"]
    for path in paths:
        if path.startswith(PROTECTED_PATHS) or "/.git" in path or "/.forgeflow" in path:
            raise LoopError(f"worker touched protected path: {path}")
        if not paths_conflict(path, owner):
            raise LoopError(f"worker changed unowned path: {path} outside {owner}")


def worktree_fanin(task_dir: Path, project_root: Path, verify_command: str) -> int:
    ledger_path = artifact_paths(task_dir)["ledger"]
    entries = [entry for entry in parse_fanout_entries(read_text(ledger_path)) if entry["status"] == "created"]
    if not entries:
        raise LoopError("no created worktree fanout entries to fan in")
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    merged = 0
    failed = 0
    lines = ["\n## Worktree Fanin"]
    for entry in entries:
        worker = Path(entry["worker"])
        try:
            paths = changed_paths(worker)
            validate_worker_changes(entry, paths)
            if paths:
                patch_proc = git(worker, "diff", "--binary", "HEAD")
                apply_proc = git(project_root, "apply", "--3way", input_text=patch_proc.stdout)
                if patch_proc.returncode != 0 or apply_proc.returncode != 0:
                    raise LoopError((patch_proc.stderr + apply_proc.stderr).strip() or "git apply failed")
                merged += 1
                status = "merged"
            else:
                status = "noop"
            lines.append(f"- {now} task={entry['task']} worker={worker} status={status} paths={','.join(paths) or 'none'}")
        except LoopError as exc:
            failed += 1
            lines.append(f"- {now} task={entry['task']} worker={worker} status=failed reason={str(exc).replace(' ', '_')}")
    verify = subprocess.run(
        shlex.split(verify_command),
        cwd=project_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    lines.append(f"- {now} verification_exit={verify.returncode} stdout={verify.stdout.strip()!r} stderr={verify.stderr.strip()!r}")
    ledger_path.write_text(read_text(ledger_path) + "\n".join(lines) + "\n", encoding="utf-8")
    if verify.returncode != 0:
        return record(task_dir, "blocked", f"worktree-fanin verification_exit={verify.returncode} ledger.md#Worktree-Fanin", None, "fan-in verification command failed")
    print(f"fanin: merged={merged} failed={failed} verification={verify.returncode}")
    return 0 if failed == 0 else 1


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
    step = sub.add_parser("step")
    step.add_argument("--task-dir", required=True, type=Path)
    step.add_argument("--adapter", default="stub", help="adapter label, default: stub")
    step.add_argument("--command", dest="adapter_command", default=None, help="optional adapter command template; receives prompt on stdin; supports {task_dir} and {prompt}")
    step.add_argument("--verify-command", default=None, help="optional verification command template; supports {task_dir} and {prompt}")
    queue = sub.add_parser("queue")
    queue.add_argument("--queue-root", required=True, type=Path, help="directory that receives task draft directories")
    queue.add_argument("--request", required=True, help="natural-language phone-originated request")
    queue.add_argument("--task-id", default=None)
    queue.add_argument("--route", default=None, choices=["small", "medium", "high", "epic"], help="override recommended route")
    learn = sub.add_parser("learn")
    learn.add_argument("--task-dir", required=True, type=Path)
    learn.add_argument("--learning-root", required=True, type=Path, help="directory for candidate-only learning records")
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--learning-root", required=True, type=Path)
    preflight.add_argument("--request", required=True)
    preflight.add_argument("--min-count", type=int, default=2)
    fanout = sub.add_parser("fanout")
    fanout.add_argument("--task-dir", required=True, type=Path)
    fanout.add_argument("--project-root", required=True, type=Path)
    fanout.add_argument("--worker-root", required=True, type=Path)
    fanout.add_argument("--max-workers", type=int, default=4)
    fanin = sub.add_parser("fanin")
    fanin.add_argument("--task-dir", required=True, type=Path)
    fanin.add_argument("--project-root", required=True, type=Path)
    fanin.add_argument("--worker-root", required=True, type=Path, help="kept for command symmetry; fan-in reads exact worker paths from ledger")
    fanin.add_argument("--verify-command", required=True, help="verification command that must pass after applying worker diffs")
    args = parser.parse_args(argv)
    try:
        task_dir = getattr(args, "task_dir", None)
        if task_dir is not None:
            task_dir = task_dir.expanduser().resolve()
        if args.command == "status":
            return print_status(task_dir)
        if args.command == "next":
            return print_next(task_dir)
        if args.command == "record":
            return record(task_dir, args.status, args.evidence, args.task, args.blocker)
        if args.command == "run-adapter":
            if task_dir is None:
                raise LoopError("--task-dir is required")
            return run_adapter(task_dir, args.adapter, args.adapter_command, args.verify_command)
        if args.command == "step":
            if task_dir is None:
                raise LoopError("--task-dir is required")
            return step_supervisor(task_dir, args.adapter, args.adapter_command, args.verify_command)
        if args.command == "queue":
            return queue_request(args.queue_root, args.request, args.task_id, args.route)
        if args.command == "learn":
            return capture_learning(task_dir, args.learning_root)
        if args.command == "preflight":
            return preflight_learning(args.learning_root, args.request, args.min_count)
        if args.command == "fanout":
            return worktree_fanout(task_dir, args.project_root.expanduser().resolve(), args.worker_root.expanduser().resolve(), args.max_workers)
        if args.command == "fanin":
            return worktree_fanin(task_dir, args.project_root.expanduser().resolve(), args.verify_command)
    except LoopError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
