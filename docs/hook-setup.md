# Hook Setup Guide

ForgeFlow provides hook scripts that integrate with AI coding agent hooks systems to enforce hard rules and optionally check artifact invariants. This guide explains how to configure them.

**Thin Guard** is ForgeFlow's opt-in artifact invariant checker. It inspects task directories for contract violations without mutating artifacts, executing stages, or introducing external dependencies. It is not a runtime, scheduler, or agent OS.

## Prerequisites

- ForgeFlow installed as a plugin or extension (Claude Code, Codex, Gemini CLI, or Cursor)
- `scripts/forgeflow_hook_check.sh` accessible from your project
- Active hard rules in `~/.forgeflow/evolution/rules/` or `.forgeflow/evolution/rules/` (for hard rule checks)

## Hook Scripts

### `scripts/forgeflow_hook_check.sh`

Runs hard rule checks and optional artifact guard checks. Designed for adapter hook integration.

```bash
# Check a specific rule
forgeflow_hook_check.sh --rule no-env-commit --project /path/to/project

# Check all active hard rules
forgeflow_hook_check.sh --all --project /path/to/project

# Check artifact invariants for a task directory (opt-in)
forgeflow_hook_check.sh --guard-artifacts --task-dir /path/to/task --stage execute
```

Exit codes:
- `0` = PASS
- `2` = BLOCK (hard rule violated or artifact guard failed, execution should stop)

### `scripts/forgeflow_guard_check.py` (Thin Guard)

Opt-in artifact invariant checker. Stdlib-only, no external dependencies. Does NOT mutate artifacts, execute stages, or repair files.

```bash
# Check task directory invariants
python3 scripts/forgeflow_guard_check.py check-task --task-dir /path/to/task --stage execute

# Check clarify / plan / execute stage artifacts
python3 scripts/forgeflow_guard_check.py check-clarify --task-dir /path/to/task
python3 scripts/forgeflow_guard_check.py check-plan --task-dir /path/to/task
python3 scripts/forgeflow_guard_check.py check-execute --task-dir /path/to/task

# Check review artifacts
python3 scripts/forgeflow_guard_check.py check-review --task-dir /path/to/task

# Check ship readiness
python3 scripts/forgeflow_guard_check.py check-ship --task-dir /path/to/task
```

Exit codes:
- `0` = PASS (all invariants satisfied)
- `2` = BLOCK (contract violation found)
- `1` = invalid invocation, unreadable file, or malformed artifact

Key properties:
- No default installation — must be explicitly wired in adapter hooks or invoked manually
- No source mutation — reports PASS/BLOCK only
- No stage execution — checks artifacts, does not run stages
- Adapter-neutral — works with Claude Code, Codex, Gemini CLI, Cursor, or standalone CLI

### `scripts/forgeflow_evolution_promote.py`

Tracks soft rule failures and auto-promotes to hard when threshold is reached.

```bash
# Record a soft rule failure
python3 scripts/forgeflow_evolution_promote.py record-fail --rule my-rule

# Check if promotion threshold reached
python3 scripts/forgeflow_evolution_promote.py check-promote --rule my-rule --threshold 2

# Manually promote a rule
python3 scripts/forgeflow_evolution_promote.py promote --rule my-rule

# List all failure counts
python3 scripts/forgeflow_evolution_promote.py list-failures
```

## Claude Code Hooks Configuration

Add hooks to `.claude/settings.json` (project) or `~/.claude/settings.json` (global):

### Example: Pre-commit hard rule check (Claude Code)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash /path/to/forgeflow/scripts/forgeflow_hook_check.sh --all --project ${PROJECT_DIR}"
          }
        ]
      }
    ]
  }
}
```

### Example: Artifact guard as preflight check (Claude Code)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash /path/to/forgeflow/scripts/forgeflow_hook_check.sh --guard-artifacts --task-dir ${TASK_DIR} --stage ${STAGE}"
          }
        ]
      }
    ]
  }
}
```

### CLI / Manual Usage

Thin Guard works without any adapter hooks. Run directly:

```bash
# Check task directory before execute
python3 scripts/forgeflow_guard_check.py check-task --task-dir ~/.forgeflow/projects/my-project/tasks/feature-xyz-a1b --stage execute

# Check stage completion gates
python3 scripts/forgeflow_guard_check.py check-clarify --task-dir ~/.forgeflow/projects/my-project/tasks/feature-xyz-a1b
python3 scripts/forgeflow_guard_check.py check-plan --task-dir ~/.forgeflow/projects/my-project/tasks/feature-xyz-a1b
python3 scripts/forgeflow_guard_check.py check-execute --task-dir ~/.forgeflow/projects/my-project/tasks/feature-xyz-a1b

# Check review before ship
python3 scripts/forgeflow_guard_check.py check-review --task-dir ~/.forgeflow/projects/my-project/tasks/feature-xyz-a1b

# Check ship readiness
python3 scripts/forgeflow_guard_check.py check-ship --task-dir ~/.forgeflow/projects/my-project/tasks/feature-xyz-a1b
```

When exit code is `2`, the adapter or hook should block the attempted action. When `0`, all invariants are satisfied.

### Example: Record failures on verification retry

When execute's bounded verification fix loop detects a retry (attempt ≥ 2), record the failure:

```bash
python3 scripts/forgeflow_evolution_promote.py record-fail --rule scope-boundary
```

### Example: Auto-promote on ship

Ship stage automatically runs `check-promote` for each extracted evolution rule. If the threshold is reached, the rule is promoted to hard enforcement.

## Promotion Lifecycle

```text
SOFT rule (advisory .md)
  → failure recorded (record-fail)
  → threshold reached (check-promote)
  → HARD rule (JSON with enforcement.mode = hard_exit_2)
  → enforced via hook (forgeflow_hook_check.sh)
  → audit logged (audit-log.jsonl)
```

## Safety Guarantees

- Hard rules require `hard_gate_evidence` with 8 safety criteria
- Auto-promoted rules include audit trail timestamps
- Manual `promote` requires explicit confirmation
- Rules can be retired by removing the JSON file and updating audit-log
