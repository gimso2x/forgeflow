# ForgeFlow Runtime Adapters

ForgeFlow keeps workflow contracts separate from execution backends. The canonical flow remains `clarify → plan → run → review → ship`; adapters only describe how a backend can execute a stage, collect evidence, and surface safety constraints.

## Adapter boundary

Adapters may own:

- target-specific instructions and generated context (`adapters/targets/*`, `adapters/generated/*`)
- backend invocation details and capability notes
- hook or rule delivery when the backend supports it
- evidence capture guidance for stage execution

Adapters must not own:

- ForgeFlow stage names or gate semantics
- artifact schemas
- route selection policy
- review approval rules
- hidden alternate state outside `.forgeflow/tasks/<task-id>/`

## Capability matrix

- Claude Code
  - Strengths: project-local plugin delivery, hooks, subagents, interactive repair loops.
  - Best fit: clarify, plan, run, review, ship in Claude Code workspaces.
  - Caveats: stage-boundary approvals and max-turn behavior can stop an otherwise useful run; evidence must still be written to artifacts.

- Codex
  - Strengths: non-interactive code execution, review-friendly diffs, local marketplace-style generated guidance.
  - Best fit: run and focused verification in scoped repositories.
  - Caveats: prompts must explicitly require `.forgeflow/tasks` artifact writes; otherwise Codex may complete code without state artifacts.

- Hermes
  - Strengths: orchestration, scheduled/background work, tool-driven inspection, multi-agent delegation.
  - Best fit: coordination, repository inspection, verification orchestration, handoff summaries.
  - Caveats: Hermes self-report is still reported evidence unless concrete command output, files, or diffs are attached.

- OpenCode
  - Strengths: alternate coding backend and adapter target for environments that prefer OpenCode conventions.
  - Best fit: scoped run/review loops when the adapter instructions are installed project-locally.
  - Caveats: capability parity must be documented before relying on backend-specific hooks or tools.

## Stage selection guidance

- Clarify: choose the backend that can inspect repo context and ask only blocker questions.
- Plan: choose the backend that can preserve requirement IDs, contracts, journeys, and `verify_plan` links.
- Run: choose the backend with the best local execution and verification access.
- Review: choose an independent reviewer from the worker when possible. The review must cite observed evidence, not worker self-report.
- Ship: choose the backend with safe git/release tooling in the target repo.

## Evidence contract

Every backend must leave review-grade evidence in the active task directory or in directly inspectable repo state:

- artifacts written under `.forgeflow/tasks/<task-id>/`
- command output summaries with command, exit code, and pass/fail counts when applicable
- concrete changed paths or diffs
- explicit missing evidence when a check could not be run

If a backend cannot satisfy the evidence contract, the next review must treat the gap as missing evidence and avoid approval-grade claims.
