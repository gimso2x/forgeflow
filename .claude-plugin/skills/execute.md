---
description: Execute the planned implementation with evidence-backed verification.
---

# /forgeflow:execute

Implement the task. Updates `run-state.json` with progress and verification evidence.

## Instructions

1. Read `brief.json` and `plan-ledger.json` (if route requires planning).

2. For `small` route: implement the full objective directly.
   For `medium`/`high`: work through plan tasks in dependency order.

3. **Worktree isolation preference**: Python runtime calls this stage `execute`; Claude plugin users invoke it as `/forgeflow:execute`. Before editing code, inspect `brief.json` and the latest `decision-log.json` entries.
   - If `brief.json` has `"use_worktree": true`, use the runtime-prepared git worktree for execution when `run-state.json.worktree.path` is active.
   - If `brief.json` has `"use_worktree": false`, execute in the current working tree.
   - If `use_worktree` is missing/null, or `decision-log.json` contains `worktree preference not set — ask user`, ask the user whether to isolate execute in a git worktree. Then write `"use_worktree": true` or `"use_worktree": false` to `brief.json` and re-run `/forgeflow:execute`. Do not continue implementation until that preference is recorded.
   - If the project is not a git repo, worktree isolation is non-fatal; continue in the current working tree.
   - **Environment safety net**: If `brief.json` lacks `environment_preflight`, run: `git rev-parse --is-inside-work-tree 2>/dev/null; ls node_modules .venv vendor 2>/dev/null | head -3`. If dependencies are missing and a package manager is detected, stop and ask: "종속성이 설치되지 않았습니다. 설치를 먼저 진행하시겠습니까?" Do NOT attempt installation yourself. If no git and route is medium/high, warn that ship cannot commit/PR, then continue.

4. For each sub-task or implementation step:
   - Make the smallest useful change
   - Run verification commands (lint, build, test) that actually exist
   - Record results in `run-state.json`
   - **Context budget**: Do not re-read a file already in context unless it was edited since. Before reading a file, ask: "Do I need the full content, or just a specific section?" If the latter, read only the relevant lines using offset/limit. Batch multiple file inspections into parallel tool calls where possible.

5. `run-state.json` format:
   ```json
   {
     "schema_version": "0.1",
     "task_id": "<task-id>",
     "status": "not_started|in_progress|completed|blocked",
     "progress": {
       "percentage": 0-100,
       "current_task": "<sub-task-id>",
       "completed_tasks": []
     },
     "evidence": [
       {
         "command": "...",
         "exit_code": 0,
         "summary": "..."
       }
     ],
     "updated_at": "<ISO 8601>"
   }
   ```

6. **Rules**:
   - `progress.percentage` must be recalculated on every write
   - Timestamps must be real ISO 8601 (not placeholder zeros)
   - Only report commands that exist — verify before claiming
   - If verification fails, record the failure; do not mark complete
   - Do not add features or edge-case handling not in the brief. Only implement what is explicitly required.

7. **Scope gate**: Before implementing, list each requirement from brief/plan. Every line of code must trace to a stated requirement. Remove any feature not in the brief immediately.
   **Contract checkpoint**: If task directory contains contract invariants (contracts.md, DECISIONS.md), read them before implementation. Before marking any plan task complete, verify: "Does this code violate a stated contract?" Record in evidence as `contract_check:PASS <task>` or `contract_check:FAIL <task> reason="..."`.

8. **Test isolation**: Tests must pass independently via `python -m pytest tests/ -v` in a fresh shell.
   - Use `tmp_path` fixtures for files/DBs. No shared `reset_database()` patterns.
   - External resources (servers) must be started in fixtures, not assumed running.
   - Module-level mutable state must be isolated per test via `monkeypatch` or snapshot/restore.
   - Never hard-code ports. Use OS-assigned or `unused_port` fixtures.
   - Tests must pass in any execution order.

9. **State management**: Avoid module-level mutable state.
   - No `db_connection = None` style globals. Use constructors or context managers.
   - When globals are unavoidable, provide a reset function and isolate in tests.
   - Prefer class instances or function parameters over module-level state.

10. **Design assumptions**: When a requirement is ambiguous, state the decision before implementing.
   - Add `# DESIGN DECISION: ...` comments with rationale for unstated choices (retry behavior, defaults, error strategy).
   - Record in `decision-log.json`. Include "why", not just "what".

11. When all tasks are done:
    - Set `run-state.json` status to `"completed"`.
    - **완료 보고** (반드시 사용자에게 출력):
      1. 완료 요약 (1-2문장, 한국어)
      2. 검증 결과: lint/build/test 각각 pass/fail + 숫자
      3. 변경 파일 목록
      4. **다음 단계 안내** (route별):
         - `small` route: "리뷰를 진행하시겠습니까? `/forgeflow:review`를 실행해주세요."
         - `medium`/`high` route: "독립 리뷰가 필요합니다. `/forgeflow:review`를 실행해주세요."
         - 이미 review를 통과한 경우: "`/forgeflow:ship`으로 출하를 진행해주세요."
      5. 주의사항 (있는 경우): contract_check 실패, environment warning, 미해결 decisions
    - Do NOT auto-proceed to the next stage. 반드시 사용자가 다음 단계를 실행하도록 대기.

## Bounded verification fix loop

When a lint/build/test/typecheck command fails after an implementation change, do not stop at the first failure. Record each failed command, exit code, and concise failure summary in `run-state.json.evidence_refs` using a compact string such as `verification:FAIL attempt=1 command="npm run lint" exit=1 reason="react-hooks/set-state-in-effect"`, increment `run-state.retries.execute`, apply the smallest scoped fix, then rerun the focused verification. Repeat for at most 3 attempts. Mark work complete only after the latest required verification passes and add a final `verification:PASS ...` evidence ref; if failures remain, set `run-state.status` to `blocked` and keep the latest failure evidence.

## Automation / non-interactive approval mode

If the user explicitly includes `--yes`, `--auto-approve`, `--non-interactive`, or says to continue through ForgeFlow stages without further approval, treat that as approval for the current bounded ForgeFlow sequence. Do not pause at the normal stage-boundary y/n prompt; proceed to the next requested ForgeFlow stage after writing the required artifact for the current stage. This only applies inside the stated task scope and never overrides a blocker, failed verification, missing required artifact, or unsafe/destructive action.


## Status analysis preflight

Read `run-state.json`, review/eval artifacts, and `decision-log.json` from the active `.forgeflow/tasks/<task-id>/` before acting. For multi-task triage, run `python3 scripts/forgeflow_monitor.py --tasks .forgeflow/tasks --recent 10` as read-only evidence; then inspect the selected artifacts directly.
