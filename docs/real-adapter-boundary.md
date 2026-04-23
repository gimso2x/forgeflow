# Real adapter execution boundary

ForgeFlow separates generated adapter docs from runtime execution. Generated markdown teaches a host agent the harness semantics; it is not the execution engine and must not become the source of truth.

## Supported real execution slice

**Codex CLI only** is supported for the first real execution slice.

```bash
python3 scripts/run_orchestrator.py execute \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --route small \
  --adapter codex \
  --real
```

`--real` is always explicit. Stub execution remains the default because validation must not require provider credentials, API spend, or a logged-in workstation.

## Unsupported real execution

Real Claude and Cursor execution are intentionally unsupported in this slice. They may have generated adapter docs, but `--real --adapter claude` and `--real --adapter cursor` are not supported runtime boundaries yet.

This is not coyness. Calling every host CLI directly before defining capture, auth, cwd, and artifact semantics is how a harness turns into soup.

## Runtime boundary

For the supported Codex path, ForgeFlow owns:

- generating the stage prompt from canonical policy, prompts, and task artifacts
- invoking `codex exec <prompt>` from the task directory
- capturing stdout into `<stage>-output.md` when the adapter returns success
- returning structured execution status through the operator CLI

Codex owns:

- provider authentication
- model/provider execution
- any provider-side errors

## Failure modes

The operator CLI must report these explicitly:

- **missing CLI** — `codex` is not on `PATH`; install/auth Codex CLI or omit `--real` to use the safe stub
- **auth failure** — Codex exits non-zero because the local CLI is unauthenticated or provider access fails
- **non-zero exit** — Codex returns a failing process status; stderr is surfaced in the structured error
- **malformed output** — reserved for future artifact-parsing slices; current slice treats stdout as raw stage output and does not parse it as structured JSON

## Drift control

Runtime behavior is implemented in `forgeflow_runtime/executor.py` and exercised through `scripts/run_orchestrator.py`. Generated adapter markdown stays downstream of canonical docs/policy/prompts and must not be hand-edited into a separate runtime contract.
