# Operator shell

ForgeFlow의 정본 흐름은 `clarify-first`다. operator shell은 그 정본을 사람이 로컬에서 만질 수 있게 만든 얇은 표면이다. 이걸 새 workflow 의미론으로 착각하면 바로 삐끗한다.

## When to use it

Use the operator shell when you need to:

- inspect persisted task state
- bootstrap a new task from explicit operator inputs
- run a route against local artifacts
- execute or advance one stage manually
- retry a failed stage within budget
- rewind a stage after review or gate failure
- escalate a task to `large_high_risk`

Do not use it to bypass review gates. `spec-review`와 `quality-review`는 CLI 명령이 아니라 artifact와 evidence로 통과한다.

## Safe sample command

`run_runtime_sample.py` is the safe demo entry. It copies a fixture to a disposable workspace before running, so tracked fixture artifacts do not get dirtied by a sample command.

```bash
python3 scripts/run_runtime_sample.py \
  --fixture-dir examples/runtime-fixtures/small-doc-task \
  --route small
```

## Canonical help

The CLI itself carries the short operator cheatsheet:

```bash
python3 scripts/run_orchestrator.py --help
```

Review rollup note: there is intentionally no `review-summary` command yet. Use `status` plus the review artifacts; the decision rationale lives in `docs/review-summary-decision.md`.

For command-specific arguments:

```bash
python3 scripts/run_orchestrator.py run --help
python3 scripts/run_orchestrator.py advance --help
python3 scripts/run_orchestrator.py execute --help
```

## Common commands

```bash
# Bootstrap a real task from explicit inputs.
python3 scripts/run_orchestrator.py init \
  --task-dir work/my-task \
  --task-id my-task-001 \
  --objective "Update README quickstart" \
  --risk low

# Inspect current artifacts and stage pointer.
python3 scripts/run_orchestrator.py status \
  --task-dir examples/runtime-fixtures/small-doc-task

# Fallback entry: route omitted, so persisted state or brief/checkpoint artifacts decide.
python3 scripts/run_orchestrator.py start \
  --task-dir examples/runtime-fixtures/small-doc-task

python3 scripts/run_orchestrator.py run \
  --task-dir examples/runtime-fixtures/small-doc-task

# Raise the minimum route floor without lowering persisted or explicit route choice.
python3 scripts/run_orchestrator.py run \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --min-route medium

# Execute the current stage with a selected adapter.
# Default execution is a safe stub; the JSON payload should report
# "execution_mode": "stub".
python3 scripts/run_orchestrator.py execute \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --route small \
  --adapter codex

# Opt into the real provider CLI explicitly. This requires the selected
# binary and auth to be available on PATH, and the JSON payload should report
# "execution_mode": "real".
python3 scripts/run_orchestrator.py execute \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --route small \
  --adapter claude \
  --real

# Advance from clarify and immediately execute the next stage.
python3 scripts/run_orchestrator.py advance \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --route small \
  --current-stage clarify \
  --execute \
  --adapter cursor

# Retry, rewind, or escalate.
python3 scripts/run_orchestrator.py retry \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --stage execute \
  --max-retries 2

python3 scripts/run_orchestrator.py step-back \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --route small \
  --current-stage quality-review

python3 scripts/run_orchestrator.py escalate \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --from-route small
```

## Route selection rules

- `--route` is an explicit override.
- Without `--route`, the CLI reuses route state from `session-state.json`, `checkpoint.json`, or `plan-ledger.json`.
- If no persisted route exists, `brief.json.risk_level` maps to a route.
- If nothing is available, fallback route is `small`.
- `--min-route` can raise the floor, but must not lower an explicit or persisted route.

## Mutation warning

Manual `run_orchestrator.py` commands mutate the target `--task-dir`. That is intended for real local task artifacts and dangerous for tracked examples. For demos, use `run_runtime_sample.py` unless you specifically want to inspect fixture mutation.

## Exit condition

An operator shell session is complete only when artifacts, gates, and review evidence agree. A pretty CLI JSON response is not evidence by itself. Worker self-report is definitely not enough for finalize. Nice try, robot.
