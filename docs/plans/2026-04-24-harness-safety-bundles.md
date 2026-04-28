# Harness Safety Bundles Implementation Plan

> **For Hermes:** Implement this slice with strict TDD. Keep it project-local opt-in; do not install hooks by default.

**Goal:** Add a minimal project-local safety bundle installer path that exposes ForgeFlow's guard intent for Claude projects without importing `harness_framework`'s global Stop-hook runtime or auto-commit loop.

**Architecture:** Extend `scripts/install_agent_presets.py` with `--hook-bundles`. For this first hook slice, support Claude only and install a static project-local `.claude/settings.json` plus hook scripts under `.claude/hooks/forgeflow/`. Codex/Codex should fail clearly for hook bundles instead of pretending equivalent runtime hooks exist. Hooks are small Python stdlib scripts receiving Claude Code stdin JSON.

**Tech Stack:** Python stdlib, Claude Code hook JSON stdin contract, pytest.

---

## Non-Goals

- Do not enable hooks by default.
- Do not run full build/test on every Stop.
- Do not add auto-commit, auto-push, or `stepN.md` runtime.
- Do not edit global `~/.claude/settings.json`.
- Do not claim regex command guards are a complete security model.

## Bundle scope for PR2

Support one bundle first:

```text
basic-safety
```

It installs:

```text
.claude/hooks/forgeflow/basic_safety_guard.py
.claude/settings.json
```

Behavior:
- PreToolUse/Bash hook blocks obviously destructive commands: `rm -rf`, `git reset --hard`, `git push --force`, `DROP TABLE`.
- Allows normal non-destructive commands.
- Emits a concise block message and exits 2 when blocking.

---

### Task 1: Add failing installer tests

**Files:**
- Modify: `tests/test_agent_preset_install.py`

**Test cases:**
1. `--hook-bundles basic-safety` with `--adapter claude` creates:
   - `.claude/hooks/forgeflow/basic_safety_guard.py`
   - `.claude/settings.json`
2. Generated `docs/forgeflow-team-init.md` lists `basic-safety` under a safety bundle section.
3. `--hook-bundles basic-safety` with `--adapter codex` fails with a clear `Claude adapter only` message.
4. Running without `--hook-bundles` creates no `.claude/settings.json`.

**RED command:**
```bash
pytest tests/test_agent_preset_install.py::test_claude_installer_can_install_basic_safety_hook_bundle tests/test_agent_preset_install.py::test_hook_bundles_are_claude_only tests/test_agent_preset_install.py::test_installer_does_not_install_hooks_by_default -q
```

### Task 2: Add failing hook behavior tests

**Files:**
- Create/modify: `tests/test_claude_safety_bundle_hooks.py`

**Test cases:**
1. Run `basic_safety_guard.py` with stdin:
   ```json
   {"tool_name":"Bash","tool_input":{"command":"rm -rf node_modules"}}
   ```
   Expected: exit 2 and stderr contains `FORGEFLOW BASIC SAFETY`.
2. Run with `npm run test` and expect exit 0.
3. Run with non-Bash payload and expect exit 0.

**RED command:**
```bash
pytest tests/test_claude_safety_bundle_hooks.py -q
```

### Task 3: Implement hook template and settings writer

**Files:**
- Create: `adapters/targets/claude/hook-bundles/basic-safety/basic_safety_guard.py`
- Create: `adapters/targets/claude/hook-bundles/basic-safety/settings.json`
- Modify: `scripts/install_agent_presets.py`

**Implementation:**
- Add `SUPPORTED_HOOK_BUNDLES = {"basic-safety"}`.
- Add CLI `--hook-bundles` as comma-separated list.
- Reject hook bundles for adapters other than Claude.
- Copy bundle files into `.claude/hooks/forgeflow/` and `.claude/settings.json`.
- Do not overwrite existing `.claude/settings.json`; fail clearly if it already exists.

### Task 4: Update onboarding note and docs

**Files:**
- Modify: `scripts/install_agent_presets.py`
- Modify: `README.md`

**Implementation:**
- Add `## Installed hook/safety bundles` to `forgeflow-team-init.md`.
- README documents:
  ```bash
  python3 scripts/install_agent_presets.py --adapter claude --target /path/to/project --profile nextjs --hook-bundles basic-safety
  ```
- README states hooks are opt-in, project-local, and not a complete security sandbox.

### Task 5: Verify and commit

**Commands:**
```bash
python -m py_compile scripts/install_agent_presets.py adapters/targets/claude/hook-bundles/basic-safety/basic_safety_guard.py
pytest tests/test_agent_preset_install.py tests/test_claude_safety_bundle_hooks.py -q
make validate
python -m pytest -q
git diff --check
```

**Commit:**
```bash
git add docs/plans/2026-04-24-harness-safety-bundles.md scripts/install_agent_presets.py adapters/targets/claude/hook-bundles tests/test_agent_preset_install.py tests/test_claude_safety_bundle_hooks.py README.md
git commit -m "feat: add opt-in claude safety bundle"
```
