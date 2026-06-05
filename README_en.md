# ForgeFlow

[![validate](https://github.com/gimso2x/forgeflow/actions/workflows/validate.yml/badge.svg)](https://github.com/gimso2x/forgeflow/actions/workflows/validate.yml) [![evals](https://github.com/gimso2x/forgeflow/actions/workflows/evals.yml/badge.svg)](https://github.com/gimso2x/forgeflow/actions/workflows/evals.yml)

ForgeFlow is an artifact-first delivery workflow for AI coding agents.
It guides Claude Code, Codex, Gemini CLI, and Cursor through clarify → plan → execute → review → ship using explicit markdown artifacts instead of chat memory.
It also includes coding-agent behavior guardrails for assumption surfacing, simplicity-first implementation, surgical diffs, and goal-driven verification. Clarify/plan/execute treat these as advisory habits, while review can report `assumption-risk`, `overengineering`, `scope-creep`, `unverified-success`, and `drive-by-refactor` findings.

## Why use it

- Track agent work through readable artifacts.
- Keep planning, implementation evidence, independent review, and shipping handoff separated.
- Reuse the same workflow across multiple agent adapters.
- Detect behavior risks such as hidden assumptions, overengineering, scope creep, unverified success, and drive-by refactors.

## Quickstart

### Claude Code

```text
/plugin marketplace add https://github.com/gimso2x/forgeflow
/plugin install forgeflow
```

### Gemini CLI

```bash
gemini extensions install https://github.com/gimso2x/forgeflow
printf 'Y\n' | gemini extensions update forgeflow
gemini extensions list
```

### Cursor local plugin

```bash
mkdir -p ~/.cursor/plugins/local
ln -s /path/to/forgeflow ~/.cursor/plugins/local/forgeflow
# Cursor: Developer: Reload Window
```

Cursor uses short slash command names:

```text
/clarify <describe the coding task>
/ff-plan
/execute
/ff-review
/ship
```

### Codex CLI / Codex App

Marketplace install:

```bash
codex plugin marketplace add gimso2x/forgeflow
codex plugin add forgeflow@forgeflow
codex plugin list
```

Local project install from a checkout:

```bash
# Run from the target project root.
make -C /path/to/forgeflow install-codex-local CODEX_LOCAL_PLUGIN_DIR="$PWD/.codex/plugins/forgeflow"
```

Codex App on WSL reads the same Codex CLI plugin configuration inside WSL. Restart the app after changing enabled plugins.

For a Codex App smoke test, run from the target project root, not from the ForgeFlow checkout or plugin cache:

```text
/forgeflow:clarify --auto <tiny low-risk task>
```

Confirm the task artifacts land under `~/.forgeflow/projects/<project-slug>/tasks/<task-id>/`.

Auto mode is route-aware: small tasks chain `clarify → execute → ship` after execute self-verification; medium and larger tasks keep the independent review stage before ship.

## Artifacts

By default, task artifacts are stored outside the repository:

```text
~/.forgeflow/projects/<project-slug>/tasks/<task-id>/
```

Each task workspace contains files such as `brief.md`, `plan.md`, `ledger.md`, `checkpoint.md`, `run-state.json`, `implementation-notes.md`, `review-report.md`, and `ship-summary.md`.

## Validation

```bash
make validate
make validate-evals
make validate-behavior-guardrails
make validate-guard-checks
```

GitHub Actions runs the same validation bundles through `.github/workflows/validate.yml` and `.github/workflows/evals.yml` with read-only `contents: read` permissions.

## Korean README

The canonical detailed README is [README.md](README.md). This English README is intentionally concise and mirrors the install and validation surfaces for global discoverability.
