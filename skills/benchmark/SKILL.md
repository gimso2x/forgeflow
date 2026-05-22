---
name: benchmark
description: Run cross-adapter benchmark tests to compare AI agent ForgeFlow workflow compatibility. Use when the user types /benchmark or /forgeflow:benchmark.
version: 0.3.0
author: gimso2x
dependencies:
  - skills/_shared/discipline.md
validate_prompt: |
  Must run the same prompt against multiple adapters.
  Must produce a structured comparison report.
  Must not modify the main project workspace.
---

# Benchmark

Run the same prompt against multiple AI adapters (Claude, Codex, Gemini) and produce a structured comparison report.

Shared file-write, cache-location, and provider-E2E claim rules: `_shared/discipline.md`.

## Trigger

User types `/benchmark` or `/forgeflow:benchmark`.

## Input

- Test prompt benchmark size: `small`, `medium`, or `large`
  - These are benchmark fixture sizes, not ForgeFlow route labels. Do not report `large` as a workflow route; active routes remain `small` / `medium` / `high` / `epic`.
- Target adapters (default: all available)
- Project template (default: Vite + React + TypeScript)
- Execution mode: `parallel` (default) or `sequential` (for rate-limited adapters)
- Repeat count (default: 1, set ≥ 3 for variance analysis)

## Output Artifacts

- `.forgeflow/benchmarks/<timestamp>/report.md` — structured comparison report
- `.forgeflow/benchmarks/<timestamp>/<agent>-<size>.log` — raw output per adapter
- `.forgeflow/benchmarks/<timestamp>/<agent>-<size>.metrics.json` — per-run metrics

## Procedure

### 1. Pre-flight checks

#### 1a. Adapter CLI resolution

Resolve each adapter's executable path, handling WSL2 alias conflicts:

```bash
for cmd in claude codex gemini; do
  # Skip Windows-side aliases in WSL2
  resolved=$(which -a "$cmd" 2>/dev/null | grep -v '/mnt/c/' | head -1)
  if [ -z "$resolved" ]; then
    echo "WARN: $cmd not available"
  else
    echo "$cmd: $resolved ($($resolved --version 2>&1 | head -1))"
  fi
done
```

For each available adapter, note the version and resolved path. Skip unavailable adapters with a warning.

#### 1b. Environment snapshot

Record once for the report header:

```bash
node --version
pnpm --version
uname -srm
date -Iseconds
```

### 2. Prepare test projects

For each adapter × size combination:

```bash
mkdir -p /tmp/forgeflow-bench/<agent>-<size>
cd /tmp/forgeflow-bench/<agent>-<size>
pnpm create vite . --template react-ts
pnpm install
# Add TypeScript strict check
jq '.compilerOptions.strict = true' tsconfig.app.json > tsconfig.app.tmp.json && mv tsconfig.app.tmp.json tsconfig.app.json
pnpm install -D @typescript-eslint/eslint-plugin @typescript-eslint/parser 2>/dev/null || true
git init && git add -A && git commit -m "init"
```

Sizes:
- `small`: Static landing page (hero + feature cards + footer)
- `medium`: API-integrated CRUD app (fetch + form + state management)
- `large`: Multi-page app with routing, auth mock, and data persistence (optional)

### 3. Write test prompts

Prompt files go to `/tmp/forgeflow-bench/prompts/<size>-prompt.md`.

Each prompt MUST include a **ForgeFlow compliance section** requiring:
- Implementation plan before code changes
- Changed file list after completion
- Component/function role descriptions (one line each)
- Edge case enumeration (medium and large only)
- Verification command execution and results

**Critical**: Wrap compliance requirements in a unique delimiter so the evaluator can distinguish the adapter's own compliance response from echoed prompt text:

```markdown
<!-- BEGIN COMPLIANCE REQUIREMENTS -->
(compliance items listed here)
<!-- END COMPLIANCE REQUIREMENTS -->
```

### 4. Execute adapters

#### Execution modes

- **parallel**: Run all adapters for a given size simultaneously. Faster but may trigger rate limits.
- **sequential**: Run adapters one at a time with a 30s cooldown between runs. Slower but avoids rate limits.
- **auto** (recommended): Start parallel, detect failures, retry failed adapters sequentially.

#### Adapter CLI invocations

Use the resolved paths from step 1a, not bare command names:

| Adapter | Command |
|---------|---------|
| Claude | `cd <dir> && <claude-path> -p --dangerously-skip-permissions "$(cat <prompt>)" > <log> 2>&1` |
| Codex | `cd <dir> && <codex-path> exec -s danger-full-access "$(cat <prompt>)" > <log> 2>&1` |
| Gemini | `cd <dir> && <gemini-path> -p "$(cat <prompt>)" --yolo --output-format text --skip-trust > <log> 2>&1` |

Record start/end timestamps for each run.

#### Failure detection and retry

After each run, check for common failure signals:

```bash
# Rate limit detection
if grep -qiE "429|rate.?limit|too many requests" "$log"; then
  echo "WARN: $adapter-$size hit rate limit, will retry sequentially"
fi

# No code changes detection
if cd "$dir" && git diff --stat HEAD | grep -q "0 files changed"; then
  echo "WARN: $adapter-$size produced no code changes"
fi
```

Retry failed runs sequentially with a 30s cooldown. Mark as DNF after 2 failed attempts.

#### Repeat runs (optional)

When repeat count > 1, run each adapter × size N times using separate project directories (`<agent>-<size>-run<N>`). Report mean and standard deviation for execution time and LOC.

### 5. Collect metrics

For each completed run, capture:

```bash
# Lines of code generated
loc=$(find <dir>/src \( -name "*.tsx" -o -name "*.ts" -o -name "*.css" \) -exec cat {} + | wc -l)

# Files created (vs init commit)
files=$(cd <dir> && git diff --stat HEAD | tail -1)

# TypeScript type safety
ts_errors=$(cd <dir> && npx tsc --noEmit 2>&1 | grep -c "error TS")

# Type assertions
as_count=$(grep -r "as " <dir>/src/ --include="*.ts" --include="*.tsx" | wc -l)

# Leftover debug artifacts
debug_count=$(grep -rE "console\.log|TODO|FIXME|debugger" <dir>/src/ --include="*.ts" --include="*.tsx" | wc -l)

# Component complexity
for f in $(find <dir>/src/components -name "*.tsx"); do
  echo "$(wc -l < "$f") $f"
done

# Build verification
cd <dir> && pnpm build
build_exit=$?
```

Write metrics to `<agent>-<size>.metrics.json`:

```json
{
  "adapter": "claude",
  "size": "small",
  "loc": 274,
  "files_created": 6,
  "files_deleted": 3,
  "ts_errors": 0,
  "type_assertions": 0,
  "debug_artifacts": 0,
  "component_sizes": {"Hero.tsx": 15, "Features.tsx": 56, "Footer.tsx": 9},
  "build_success": true,
  "log_size_kb": 1.9
}
```

### 6. Evaluate ForgeFlow compliance

Score each adapter on the mandatory checklist:

| # | Item | Required for |
|---|------|-------------|
| 1 | Implementation plan stated | all |
| 2 | Changed file list with descriptions | all |
| 3 | Component/function role descriptions | all |
| 4 | Edge cases enumerated | medium, large |
| 5 | Verification commands run | all |

**Evaluation method**: Extract the adapter's response AFTER the last code block (where compliance items typically appear). Only score content outside the `<!-- BEGIN/END COMPLIANCE REQUIREMENTS -->` delimiter range. This prevents false positives from prompt echoing.

Score: `<met_items>/<total_items>` per adapter per size.

Mark runs as **DNF** (Did Not Finish) when:
- Rate limit or API error prevented code generation
- Git diff shows zero file changes from init
- Build fails and adapter did not attempt a fix

DNF runs are excluded from ranking but documented in the Environment Issues section.

### 7. Generate report

Write to `.forgeflow/benchmarks/<timestamp>/report.md`:

```markdown
# ForgeFlow Adapter Benchmark Report

**Date**: <date>
**Environment**: <os>, Node <version>, pnpm <version>
**Execution Mode**: parallel|sequential|auto
**Repeat Count**: N

## Execution Time

| Adapter | Small | Medium | Large | Total |
|---------|-------|--------|-------|-------|
| ... | ...s | ...s | ...s | ...s |

*(Include mean ± std dev when repeat count > 1)*

## Code Volume (LOC)

| Adapter | Small | Medium | Large | Total |
|---------|-------|--------|-------|-------|
| ... | ... | ... | ... | ... |

## Code Quality

| Adapter | Size | TS Errors | Type Assertions | Debug Artifacts | Max Component LOC |
|---------|------|-----------|-----------------|-----------------|-------------------|
| ... | ... | ... | ... | ... | ... |

## ForgeFlow Compliance

### Small (4 items)
| Item | Claude | Codex | Gemini |
|------|--------|-------|--------|
| Plan stated | ✅/❌ | ✅/❌ | ✅/❌ |
| File list | ✅/❌ | ✅/❌ | ✅/❌ |
| Role descriptions | ✅/❌ | ✅/❌ | ✅/❌ |
| Verification | ✅/❌ | ✅/❌ | ✅/❌ |
| **Score** | **n/4** | **n/4** | **n/4** |

### Medium (5 items)
| Item | Claude | Codex | Gemini |
|------|--------|-------|--------|
| Plan stated | ✅/❌ | ✅/❌ | ✅/❌ |
| File list | ✅/❌ | ✅/❌ | ✅/❌ |
| Role descriptions | ✅/❌ | ✅/❌ | ✅/❌ |
| Edge cases | ✅/❌ | ✅/❌ | ✅/❌ |
| Verification | ✅/❌ | ✅/❌ | ✅/❌ |
| **Score** | **n/5** | **n/5** | **n/5** |

### Compliance Summary
| Adapter | Small | Medium | Large | Total |
|---------|-------|--------|-------|-------|
| ... | **n/4** | **n/5** | **n/5** | **n/14** |

## Build Verification
| Adapter | Small | Medium | Large |
|---------|-------|--------|-------|
| ... | ✅/❌ | ✅/❌ | ✅/❌ |

## Log Volume
| Adapter | Small | Medium | Large | Total |
|---------|-------|--------|-------|-------|
| ... | ...KB | ...KB | ...KB | ...KB |

## Environment Issues
(Any DNF runs, rate limits, CLI resolution issues, or infrastructure failures)

## Code Quality Notes
(Per-adapter observations on architecture, separation of concerns, naming, etc.)

## Recommendation
(Ranked by completed runs only: compliance score → code quality → execution time → log conciseness)
```

## Exit Condition

- All available adapters have been tested (or marked DNF after retries)
- Report is written to `.forgeflow/benchmarks/<timestamp>/report.md`
- Build verification passed for all non-DNF projects
- Compliance scores are calculated using response-only evaluation
- Metrics JSON files are written for each run

## Constraints

- Benchmark runs in `/tmp/` — never in the main project workspace
- Each adapter gets the same prompt text
- Timing starts when the adapter process starts, ends when it exits
- Raw logs are preserved for manual inspection
- Do not modify any ForgeFlow source files during benchmarking
- DNF runs must be documented, not silently dropped
