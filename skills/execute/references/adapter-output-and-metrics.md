# Adapter Output and Metrics

Use this reference from `skills/execute/SKILL.md` when normalizing agent output, applying adapter-specific execution hints, or collecting metrics for the Completion Response and review stage.

## Output normalization

When ForgeFlow artifacts are parsed by downstream stages, normalize agent output to avoid noise:

- **Codex**: strip raw git diff blocks before extracting summaries. Codex may output 100KB+ diffs; only the final summary section is relevant for artifacts.
- **All adapters**: remove ANSI escape sequences, cache/memory logs, and progress spinners from captured command output before recording in `implementation-notes.md`.
- Extract only: file list, verification results, component descriptions, edge cases, and the completion report.

This normalization is advisory for skill prompts but mandatory when ForgeFlow orchestrates multi-adapter pipelines.

## Adapter-aware execution

Detect the current adapter via `skills/forgeflow/SKILL.md` -> Adapter detection, then apply these adjustments:

| Adapter | Verification | Output Discipline | Rate Limit |
|---------|-------------|-------------------|------------|
| Claude | `build` preferred. Table-format reports. | Concise by default (~5KB/medium task). No special handling needed. | No known issues. |
| Codex | `lint` mandatory (Codex naturally does this). | Normalize diff-heavy output. Strip raw git diffs; keep only summaries. Output can exceed 100KB without normalization. | No known issues. |
| Antigravity CLI | `import type` enforced for TS with `verbatimModuleSyntax`. Structured markdown. | Compact output (~7KB/medium task). May introduce UI abstractions not requested. | HTTP 429 can occur under concurrent load. Run sequentially or add 30s cooldown between tasks when executing multiple plan steps. |
| Cursor | Skill names without colons. Same adjustments as the underlying adapter (Claude by default). | Same as underlying adapter. | Same as underlying adapter. |

## Code quality metrics

Collect quantitative metrics after implementation:

```bash
# LOC generated
find src/ \( -name "*.ts" -o -name "*.tsx" -o -name "*.css" \) -exec cat {} + | wc -l

# TypeScript type safety
npx tsc --noEmit 2>&1 | grep -c "error TS"

# Type assertions (lower is better)
grep -r "as " src/ --include="*.ts" --include="*.tsx" | wc -l

# Debug artifacts (must be 0)
grep -rE "console\.log|TODO|FIXME|debugger" src/ --include="*.ts" --include="*.tsx" | wc -l

# Component complexity (flag any component > 100L)
for f in $(find src/ -name "*.tsx" -o -name "*.ts"); do echo "$(wc -l < "$f") $f"; done
```

Record results in `implementation-notes.md` -> Metrics section and in the Completion Response item 7.
