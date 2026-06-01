# Hook Setup Guide

ForgeFlow provides hook scripts that integrate with Claude Code's hooks system to enforce hard rules automatically. This guide explains how to configure them.

## Prerequisites

- ForgeFlow installed as a Claude Code plugin
- `scripts/forgeflow_hook_check.sh` accessible from your project
- Active hard rules in `~/.forgeflow/evolution/rules/` or `.forgeflow/evolution/rules/`

## Hook Scripts

### `scripts/forgeflow_hook_check.sh`

Runs hard rule checks. Designed for Claude Code hook integration.

```bash
# Check a specific rule
forgeflow_hook_check.sh --rule no-env-commit --project /path/to/project

# Check all active hard rules
forgeflow_hook_check.sh --all --project /path/to/project
```

Exit codes:
- `0` = PASS
- `2` = BLOCK (hard rule violated, execution should stop)

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

### Example: Pre-commit hard rule check

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
