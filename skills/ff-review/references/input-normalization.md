# Input Normalization Reference

Use this reference when `/forgeflow:ff-review` runs in standalone mode or when raw review input must be converted into `normalized-input.md`.

Regardless of input type, normalize to a standard 4-field structure before review proceeds. Write the result to `normalized-input.md` in the synthetic task directory.

## brief

What is being reviewed. Auto-generated from input:

| Input type | brief source |
|------------|-------------|
| GitHub PR | PR title + body (from `gh pr view`) |
| GitHub commit | Commit message (first line = title, body = context) |
| GitHub compare | `"<base>...<head> comparison"` + commit messages in range |
| Other URL | Page `<title>` or first `<h1>`. If none: `"Review of <url>"` |
| Repo path (current) | `"Review of working tree in <repo>"` + `git log --oneline -5` summary |
| Repo path (range) | `"Review of <range> in <repo>"` + commit count + file count from `git diff --stat` |
| Diff/patch | `"Review of diff: <N> files, <M> additions, <K> deletions"` |
| File bundle | `"Review of: <file1>, <file2>, ..."` (list all files) |
| Existing artifact | Artifact filename + first heading or summary line |

If the user provides an explicit description (`--desc "..."` or natural language in the command), use that as brief and append the auto-generated version as context.

## evidence

The concrete content to review. Extraction rules:

| Input type | evidence extraction |
|------------|-------------------|
| GitHub PR | `gh pr diff <n>` output (full diff). Separate from PR metadata. |
| GitHub commit | `git show <sha>` output (stat + diff). |
| GitHub compare | `git diff <range>`. If too large (>5000 LOC changed), sample: first/last 200 lines per file + file list. |
| Other URL | Extracted page content (markdown). If page is a code host, extract code blocks. |
| Repo path (current) | `git diff HEAD` + `git diff --cached`. If clean, `git log --oneline -10` + tree listing. |
| Repo path (range) | `git diff <range>`. Same large-diff sampling rule as compare. |
| Diff/patch | The raw diff text, including content read from `.diff` / `.patch` file paths. Parse into per-file hunks. |
| File bundle | Each file's full content. If a file exceeds 2000 lines, read first 500 + last 200 and note truncation. |
| Existing artifact | Full artifact content. |

Evidence integrity rules:
- Never fabricate or infer evidence. If fetch fails, the field is `null` and review is `blocked`.
- Mark truncated evidence with `[TRUNCATED: showing N/M lines]`.
- Mark fetched evidence with source: `[source: gh pr diff]`, `[source: file read]`, `[source: web_extract]`.

## scope

What range is in scope for this review:

| Input type | scope definition |
|------------|-----------------|
| GitHub PR | Files changed in the PR (from `gh pr diff --name-only`). |
| GitHub commit | Files changed in the commit (from `git show --stat`). |
| GitHub compare | Files changed in the range. |
| Other URL | Entire fetched content. |
| Repo path (current) | All uncommitted changes + staged changes. If clean: last 5 commits. |
| Repo path (range) | Files changed in the range. |
| Diff/patch | Files mentioned in diff headers (`---`/`+++`); for `.diff` / `.patch` files, the patch file itself is provenance, not review scope unless explicitly requested. |
| File bundle | The listed files only. |
| Existing artifact | The artifact itself + any referenced files that exist. |

User can narrow scope with `--scope <pattern>` (glob). Only review files matching the pattern within the detected scope.

## constraints

Review focus areas or restrictions:

- **User-specified**: `--focus security`, `--focus quality`, `--type spec`, `--type quality`. These constrain which reviewer role runs.
- **Inferred from input**:
  - PR with no description -> quality review only (no spec to check against).
  - Diff with only test files (all changed filenames match test patterns: `*.test.*`, `*.spec.*`, `*_test.*`, `test_*`, or live under a test directory) -> quality-reviewer with test-quality focus: check coverage adequacy, assertion quality, test isolation, fixture management.
  - URL to a design doc -> spec/ux review only.
  - File bundle of config files -> quality/security review.
- **Default** (no constraints specified): run both spec and quality reviews. Spec review uses auto-generated brief as the "spec" to check against.

Write constraints to `normalized-input.md` as a structured list:

```yaml
constraints:
  - type: <auto-inferred | user-specified>
  - focus: [spec | quality | security | ux | perf]
  - excluded_paths: [...]  # if --scope narrows
  - additional_rules: [...]  # user-provided or inferred
```

## Normalization Gate

After writing `brief`, `evidence`, `scope`, and `constraints`, mark the `normalization gate` in `normalized-input.md`:
- `brief_present`: `PASS` only when the review target is named and sourced.
- `evidence_present_or_blocked`: `PASS` only when concrete evidence exists, or evidence fetching failed and the failure is recorded as a blocker.
- `scope_explicit`: `PASS` only when included/excluded files, ranges, or URL bounds are explicit.
- `constraints_explicit`: `PASS` only when active roles/focus and ignored/conflicting flags are explicit.
- `limitations_visible`: `PASS` only when truncation, sampling, auth/fetch failures, excluded paths, and missing evidence are visible to reviewer roles.

Any `FAIL` blocks review approval. Record the failed gate item as missing evidence rather than continuing with inferred content.
