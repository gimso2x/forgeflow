# ForgeFlow — AGENTS.md

Repository-level instructions for AI coding agents working on this repo.

## Project Overview

ForgeFlow is an artifact-first delivery harness for AI coding agents. It provides staged workflows, gates, evidence trails, and independent review for Claude Code and Codex.

## Tech Stack

- **Language**: Python 3.11+
- **Runtime**: `forgeflow_runtime/` — 55 modules, 67 importable
- **Tests**: pytest, 1082 tests across `tests/`
- **No external runtime dependencies** — stdlib only (no pip install needed)
- **Adapters**: Claude Code (marketplace plugin), Codex (CODEX.md)

## Repo Structure

```
forgeflow_runtime/       # Core runtime library
  engine.py              # Stage execution glue
  executor.py            # Adapter dispatch
  orchestrator.py        # Stage coordination + gate enforcement
  generator.py           # Prompt generation
  artifact_validation.py # JSON artifact schema + read/write
  plan_ledger.py         # Plan task tracking
  gate_evaluation.py     # Stage gate enforcement
  gate_ralf.py           # RALF self-healing loop
  operator_routing.py    # Route selection (small/medium/large)
  ...
tests/
  runtime/               # Runtime module tests
  evolution/             # Evolution framework tests
  *.py                   # Integration / install / contract tests
adapters/targets/
  claude/                # Claude Code adapter (hooks, agents, manifest)
  codex/                 # Codex adapter (agents, rules, manifest)
.claude-plugin/          # Claude Code marketplace plugin manifest
scripts/                 # Utility scripts (validate, install, release)
docs/                    # Design documents
```

## Development Workflow

1. **Edit code** in `forgeflow_runtime/`
2. **Write/update tests** in `tests/`
3. **Run tests**: `source .venv/bin/activate && python3 -m pytest -q`
4. **Validate structure**: `python3 scripts/validate_structure.py`
5. **Commit** with conventional messages: `feat:`, `fix:`, `chore:`, `docs:`

## Code Conventions

- **No external dependencies** — stdlib only. Do not add pip requirements.
- All artifacts use JSON with `schema_version: "0.1"`.
- Artifact writes go through `write_json()` / `write_validated_artifact()`.
- Use `RuntimeViolation` for rule violations.
- Tests use `tests/runtime/conftest.py` and `tests/conftest.py` fixtures.
- New modules must be importable: `python3 -c "import forgeflow_runtime.<module>"`

## Key Patterns

- **Gate enforcement**: `enforce_stage_gate()` checks artifacts before stage transitions.
- **Artifact validation**: `assert_supported_artifact_schema_version()` + schema validators.
- **Route selection**: `auto_route_for_task_dir()` picks small/medium/large based on risk.
- **Evolution**: proposals → review → approval → promotion lifecycle.
- **Orchestration**: consensus/debate/pipeline/fastest multi-model strategies.

## Testing Rules

- Every new module gets a corresponding `tests/runtime/test_<module>.py`.
- Test functions use `def test_` prefix.
- Use `tmp_path` or `tests/runtime/conftest.py` fixtures for task directories.
- Aim for meaningful coverage — test the contract, not just imports.
- Run full suite before committing: `python3 -m pytest -q`

## Do NOT

- Add third-party pip dependencies.
- Write to `~/.claude/agents` or `~/.codex` — project-local only.
- Hallucinate commands — verify they exist in package.json or scripts.
- Modify code during review stage — read-only enforcement.
