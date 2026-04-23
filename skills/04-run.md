# Skill: run

## Purpose

Execute `plan.json` using **worker-validator pairs**. Workers implement; validators verify independently with **zero knowledge** of the worker's approach.

## Trigger

- After `plan` produces `plan.json`.
- User says: `"run the plan"`, `"execute"`, or any intent to start implementation.

## Input

- `plan.json`
- `requirements.md`
- `brief.json`
- Codebase

## Output Artifacts

| Artifact | Schema | Description |
|----------|--------|-------------|
| `decision-log.json` | `schemas/decision-log.schema.json` | Per-task decisions, rationale, and rollback pointers. |
| `run-state.json` | `schemas/run-state.schema.json` | Current stage, completed gates, failed gates, retries. |
| `plan-ledger.json` | `schemas/plan-ledger.schema.json` | Plan vs runtime truth. Updated after every task. |
| Code changes | Git working tree | Actual file modifications. |

## Execution

1. **Load the plan DAG.** Determine execution order via topological sort.
2. **Initialize `plan-ledger.json`** with planned tasks and empty runtime status.
3. **For each task (in order):**
   a. **Worker phase:**
      - Read the task contract and nothing else.
      - Implement the task. Write code, tests, and docs.
      - Run the task's `verification` step.
      - If verification fails, retry up to 2 times with backoff.
      - Write a decision entry to `decision-log.json`.
      - Update `plan-ledger.json`: mark task as `in_progress`.
   b. **Validator phase (information isolation):**
      - The validator reads **only** `plan.json`, `requirements.md`, and the codebase.
      - The validator **must not** read execution logs, worker output, or chat history.
      - Validator checks: Does the code fulfill the task's `acceptance_criteria`? Does it satisfy the linked requirements?
      - Validator verdict: `pass`, `fail`, or `needs_clarification`.
   c. **If validator verdict is `pass`:**
      - Mark task complete in `run-state.json`.
      - Update `plan-ledger.json`: mark task as `completed` with validator signature.
      - Commit changes (if using git).
   d. **If validator verdict is `fail`:**
      - Record failure in `run-state.json`.
      - Update `plan-ledger.json`: mark task as `failed` with reason.
      - Roll back the task's changes.
      - Retry the task (max 2 retries per task, max 3 total task failures before stopping).
   e. **If validator verdict is `needs_clarification`:**
      - Stop execution.
      - Emit a blocker in `run-state.json`.
      - Recommend returning to `clarify` or `specify`.
4. **Checkpoint after every milestone** (if large route).
   - Write `checkpoint.json` with current state.
   - Allow `resume` from this checkpoint.

## Constraints

- Worker and validator share no memory. Validator must not see worker reasoning. This is the anti-self-approval mechanism.
- Do not proceed to the next task until the current one passes validation.
- If a task is `parallel_safe`, workers may run in parallel, but each still gets its own validator.
- `plan-ledger.json` must be updated after every task. No ledger, no runtime truth.

## Recovery

If execution stops midway, invoke `x-resume`:
```bash
python3 scripts/run_orchestrator.py resume --task-dir <dir>
```
The orchestrator reloads `run-state.json` and `plan-ledger.json`, then continues from the last uncompleted task.
