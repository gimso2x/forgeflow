# Standalone Review Quick Start

For users who want to run `/forgeflow:ff-review` without the full normalized-input pipeline, here are lightweight entry points that still produce useful review reports.

## When to use simplified mode

- Quick PR/diff review without adapter infrastructure
- Local code review from the command line
- First-time ForgeFlow users evaluating review quality
- Any situation where filling `normalized-input.md` (133 fields) is impractical

## Simplified entry paths

### 1. Git range (most common)

```text
/forgeflow:ff-review HEAD~3..HEAD
```

ForgeFlow auto-detects the git range, generates a synthetic brief, and runs quality-reviewer. The adapter fills input-source.md and normalized-input.md automatically from `git diff`.

### 2. File/directory review

```text
/forgeflow:ff-review ./src/auth/
```

Scans the directory, generates a brief from file contents, and runs quality-reviewer. Security-reviewer is auto-triggered when auth-related files are detected.

### 3. Diff file

```text
/forgeflow:ff-review ./changes.diff
```

Reads the diff file directly, normalizes into brief/evidence/scope/constraints, and runs the appropriate reviewers.

### 4. URL (GitHub PR)

```text
/forgeflow:ff-review https://github.com/org/repo/pull/42
```

Fetches the PR diff via `gh` or web, normalizes, and runs reviewers. Requires `gh` CLI or curl access.

## What gets generated

Even in simplified mode, ForgeFlow writes:

1. **`input-source.md`** — auto-filled with detected input type, source, and fetch status
2. **`normalized-input.md`** — auto-filled with brief, evidence (from diff/files), scope, and constraints
3. **`review-report.md`** — the actual review findings with verdict

The key difference from full pipeline mode: the adapter fills the normalization artifacts instead of requiring manual input.

## Manual fallback

If no adapter is available and you're using a plain AI chat:

1. Paste your diff or describe the change
2. Ask the agent to use `/forgeflow:ff-review` with `--type quality`
3. The agent will generate a minimal review-report.md based on what it can observe

This produces a less rigorous review than the full pipeline (no fetch ledger, no freshness checks), but it's still better than no review at all.

## Role selection in simplified mode

| Flag | Effect |
|------|--------|
| (none) | quality-reviewer only (fastest) |
| `--type security` | security-reviewer only |
| `--type all` | all 6 roles |
| `--focus architecture` | architecture-reviewer only |

## Limitations of simplified mode

- No `Fetch Method Ledger` (evidence is provided, not fetched)
- No `freshness_status` (assumed current)
- No `Mutation Check` (assumed PASS for local diffs)
- Evidence level defaults to `observed` for local files, `reported` for URLs

These limitations are recorded in the review-report automatically.
