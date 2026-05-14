# Real adapter execution boundary

ForgeFlow separates generated adapter docs from runtime execution. Generated markdown teaches a host agent the harness semantics; it is not the execution engine and must not become the source of truth.

## Supported real execution slice

**Claude Code, Codex CLI, and Gemini CLI** are supported for the current real execution slice.

```bash
python3 scripts/run_orchestrator.py execute \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --route small \
  --adapter claude \
  --real

python3 scripts/run_orchestrator.py execute \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --route small \
  --adapter codex \
  --real

python3 scripts/run_orchestrator.py execute \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --route small \
  --adapter gemini \
  --real
```

`--real` is always explicit. Stub execution remains the default because validation must not require provider credentials, API spend, or a logged-in workstation.

## Unsupported real execution

Cursor is no longer a generated or supported adapter target in this repo. `--real --adapter cursor` is outside the current runtime boundary, and the supported surface is intentionally limited to Claude Code, Codex CLI, and Gemini CLI.

This is not coyness. Calling every host CLI directly before defining capture, auth, cwd, and artifact semantics is how a harness turns into soup.

## Runtime boundary

For supported real paths, ForgeFlow owns:

- generating the stage prompt from canonical policy, prompts, and task artifacts
- invoking `claude -p --dangerously-skip-permissions --bare <prompt>`, `codex exec <prompt>`, or `gemini --prompt --yolo <prompt>` from the task directory
- capturing stdout into `<stage>-output.md` when the adapter returns success
- returning structured execution status through the operator CLI

Claude Code, Codex, and Gemini own:

- provider authentication
- model/provider execution
- any provider-side errors

## Failure modes

The operator CLI must report these explicitly:

- **missing CLI** — `claude`, `codex`, or `gemini` is not on `PATH`; install/auth the selected CLI or omit `--real` to use the safe stub
- **auth failure** — Claude Code, Codex, or Gemini exits non-zero because the local CLI is unauthenticated or provider access fails
- **non-zero exit** — the selected CLI returns a failing process status; stderr is surfaced in the structured error
- **malformed output** — reserved for future artifact-parsing slices; current slice treats stdout as raw stage output and does not parse it as structured JSON

## Drift control

Runtime behavior is implemented in `forgeflow_runtime/executor.py` and exercised through `scripts/run_orchestrator.py`. Generated adapter markdown stays downstream of canonical docs/policy/prompts and must not be hand-edited into a separate runtime contract.
