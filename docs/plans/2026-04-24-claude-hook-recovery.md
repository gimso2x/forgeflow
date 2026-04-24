# Claude Hook Recovery Implementation Plan

> **For Hermes:** Execute this plan task-by-task. Keep hooks Claude-adapter-only; do not contaminate ForgeFlow core semantics.

**Goal:** Add Hoyeon-inspired Claude adapter recovery hooks for edit failures, large reads, repeated tool failures, and oversized tool output.

**Architecture:** Implement adapter-local Python hook scripts under `adapters/targets/claude/hooks/`, register them in a Claude adapter hook manifest, and test them by sending Claude hook JSON through stdin. Keep these as optional adapter assets, not canonical ForgeFlow workflow rules.

**Tech Stack:** Python stdlib, JSON stdin/stdout hook protocol, pytest, Makefile validation.

---

## Acceptance Criteria

- Hook scripts exist under `adapters/targets/claude/hooks/`.
- Hook manifest registers PostToolUse and PostToolUseFailure hooks.
- Tests invoke hooks via stdin JSON and verify returned `hookSpecificOutput.additionalContext`.
- Repeated failure tracking stores state under `CLAUDE_PROJECT_DIR` when provided, not user home during tests.
- `make validate` and `make smoke-claude-plugin` pass.

---

## Task 1: Add hook tests first

**Objective:** Lock Claude hook behavior before implementation.

**Files:**
- Create: `tests/test_claude_recovery_hooks.py`

**Test cases:**
1. `edit_error_recovery.py` returns old_string recovery guidance for Edit failures.
2. `large_file_recovery.py` returns large-file guidance for Read size-limit failures.
3. `tool_failure_tracker.py` emits repeated failure guidance on third failure in a session.
4. `tool_output_truncator.py` emits truncation context for oversized Bash output and preserves error lines.
5. Hook manifest references only existing scripts.

**Verification:**
```bash
pytest tests/test_claude_recovery_hooks.py -q
```
Expected first run: fails because hooks do not exist.

---

## Task 2: Implement adapter-local hook scripts

**Objective:** Add Python hooks with no external dependencies.

**Files:**
- Create: `adapters/targets/claude/hooks/edit_error_recovery.py`
- Create: `adapters/targets/claude/hooks/large_file_recovery.py`
- Create: `adapters/targets/claude/hooks/tool_failure_tracker.py`
- Create: `adapters/targets/claude/hooks/tool_output_truncator.py`
- Create: `adapters/targets/claude/hooks/hooks.json`

**Rules:**
- Read JSON from stdin.
- Return JSON only when guidance is needed.
- Exit 0 for non-matching events.
- Avoid `jq`/shell dependencies.
- Use `CLAUDE_PROJECT_DIR/.forgeflow/claude-hook-state/` for failure state when available.

**Verification:**
```bash
pytest tests/test_claude_recovery_hooks.py -q
```

---

## Task 3: Add hook manifest validation

**Objective:** Make broken hook registrations fail validation.

**Files:**
- Create: `scripts/validate_claude_hooks.py`
- Modify: `Makefile`

**Rules:**
- `adapters/targets/claude/hooks/hooks.json` must be valid JSON.
- Every command path must use `${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py`.
- Every referenced script must exist and be executable by Python syntax compile.

**Verification:**
```bash
python3 scripts/validate_claude_hooks.py
make validate
```

---

## Task 4: Document adapter boundary

**Objective:** Prevent future cargo-culting hooks into core.

**Files:**
- Modify: `adapters/targets/claude/manifest.yaml`

**Content:**
- Mention optional recovery hooks.
- State hooks are Claude-adapter UX helpers and must not redefine canonical workflow semantics.

**Verification:**
```bash
make validate
make smoke-claude-plugin
```
