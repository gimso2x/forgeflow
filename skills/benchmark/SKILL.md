---
name: benchmark
description: Run cross-adapter benchmark tests to compare AI agent ForgeFlow workflow compatibility. Use when the user types /benchmark or /forgeflow:benchmark.
validate_prompt: |
  Must run the same prompt against multiple adapters.
  Must produce a structured comparison report.
  Must not modify the main project workspace.
---

# Benchmark

Run the same prompt against multiple AI adapters (Claude, Codex, Gemini) and produce a structured comparison report.

## Trigger

User types `/benchmark` or `/forgeflow:benchmark`.

## Input

- Test prompt (small or medium complexity)
- Target adapters (default: all available)
- Project template (default: Vite + React + TypeScript)

## Output Artifacts

- `.forgeflow/benchmarks/<timestamp>/report.md` — structured comparison report
- `.forgeflow/benchmarks/<timestamp>/<agent>-<size>.log` — raw output per adapter

## Procedure

### 1. Pre-flight checks

Verify adapter CLIs are available:

```bash
which claude codex gemini 2>&1
```

For each available adapter, note the version. Skip unavailable adapters with a warning.

### 2. Prepare test projects

For each adapter × size combination:

```bash
mkdir -p /tmp/forgeflow-bench/<agent>-<size>
cd /tmp/forgeflow-bench/<agent>-<size>
pnpm create vite . --template react-ts
pnpm install
git init && git add -A && git commit -m "init"
```

Sizes:
- `small`: Static landing page (hero + feature cards + footer)
- `medium`: API-integrated CRUD app (fetch + form + state management)

### 3. Write test prompts

Prompt files go to `/tmp/forgeflow-bench/prompts/<size>-prompt.md`.

Each prompt MUST include a **ForgeFlow compliance section** requiring:
- Implementation plan before code changes
- Changed file list after completion
- Component/function role descriptions (one line each)
- Edge case enumeration (medium only)
- Verification command execution and results

### 4. Execute adapters (parallel)

Run all small tests in parallel, then all medium tests in parallel.

Adapter CLI invocations:

| Adapter | Command |
|---------|---------|
| Claude | `cd <dir> && claude -p --dangerously-skip-permissions "$(cat <prompt>)" > <log> 2>&1` |
| Codex | `cd <dir> && codex exec -s danger-full-access "$(cat <prompt>)" > <log> 2>&1` |
| Gemini | `cd <dir> && gemini -p "$(cat <prompt>)" --yolo --output-format text --skip-trust > <log> 2>&1` |

Record start/end timestamps for each run.

### 5. Collect results

For each completed run, capture:

```bash
# Lines of code generated
find <dir>/src \( -name "*.tsx" -o -name "*.ts" -o -name "*.css" \) -exec cat {} + | wc -l

# Files created
find <dir>/src \( -name "*.tsx" -o -name "*.ts" -o -name "*.css" \) | sort

# Build verification
cd <dir> && pnpm build
```

### 6. Evaluate ForgeFlow compliance

Score each adapter on the mandatory checklist:

| # | Item | Required for |
|---|------|-------------|
| 1 | Implementation plan stated | all |
| 2 | Changed file list with descriptions | all |
| 3 | Component/function role descriptions | all |
| 4 | Edge cases enumerated | medium |
| 5 | Verification commands run | all |

Score: `<met_items>/<total_items>` per adapter per size.

### 7. Generate report

Write to `.forgeflow/benchmarks/<timestamp>/report.md`:

```markdown
# ForgeFlow Adapter Benchmark Report

**Date**: <date>
**Environment**: <os>, Node <version>, pnpm <version>

## Execution Time

| Adapter | Small | Medium | Total |
|---------|-------|--------|-------|
| ... | ...s | ...s | ...s |

## Code Volume (LOC)

| Adapter | Small | Medium | Total |
|---------|-------|--------|-------|
| ... | ... | ... | ... |

## ForgeFlow Compliance

### Small
| Item | Claude | Codex | Gemini |
|------|--------|-------|--------|
| Plan stated | ✅/❌ | ✅/❌ | ✅/❌ |
| File list | ✅/❌ | ✅/❌ | ✅/❌ |
| Role descriptions | ✅/❌ | ✅/❌ | ✅/❌ |
| Verification | ✅/❌ | ✅/❌ | ✅/❌ |
| **Score** | **n/4** | **n/4** | **n/4** |

### Medium
(Same table + Edge cases + 2 verification gates)

## Build Verification
| Adapter | Small | Medium |
|---------|-------|--------|
| ... | ✅/❌ | ✅/❌ |

## Code Quality Notes
(Per-adapter observations)

## Recommendation
(Ranked by ForgeFlow compatibility)
```

## Exit Condition

- All available adapters have been tested
- Report is written to `.forgeflow/benchmarks/<timestamp>/report.md`
- Build verification passed for all projects
- Compliance scores are calculated

## Constraints

- Benchmark runs in `/tmp/` — never in the main project workspace
- Each adapter gets the same prompt text
- Timing starts when the adapter process starts, ends when it exits
- Raw logs are preserved for manual inspection
- Do not modify any ForgeFlow source files during benchmarking
