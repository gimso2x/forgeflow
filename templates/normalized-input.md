# Normalized Input

> Standalone review normalized input. Auto-generated during Step S4 (normalize).
> Standard 4-field structure — all reviewer roles consume this file.

## Brief

<!-- What is being reviewed. Auto-generated from input type rules:
  - GitHub PR: PR title + body
  - GitHub commit: Commit message (first line = title, body = context)
  - GitHub compare: "<base>...<head> comparison" + commit messages in range
  - Other URL: Page <title> or first <h1>
  - Repo path (current): "Review of working tree in <repo>" + git log --oneline -5
  - Repo path (range): "Review of <range> in <repo>" + commit/file counts
  - Diff/patch: "Review of diff: <N> files, <M> additions, <K> deletions"
  - File bundle: "Review of: <file1>, <file2>, ..."
  - Existing artifact: Artifact filename + first heading or summary line
  If user provides --desc, use that as brief and append auto-generated version as context.
-->

## Evidence

<!-- Concrete content to review. Extracted per input type rules.
  Evidence integrity rules:
  - Never fabricate or infer. If fetch failed, this field is null and review is blocked.
  - Mark truncated evidence: [TRUNCATED: showing N/M lines]
  - Mark fetched evidence source: [source: gh pr diff], [source: file read], [source: web_extract]
-->

## Scope

<!-- What range is in scope:
  - GitHub PR/commit/compare: Files changed
  - URL: Entire fetched content
  - Repo path (current): Uncommitted + staged changes; if clean: last 5 commits
  - Repo path (range): Files changed in range
  - Diff/patch: Files in diff headers (---/+++)
  - File bundle: Listed files only
  - Existing artifact: Artifact + referenced files that exist
  User can narrow with --scope <pattern> (glob).
-->

## Constraints

<!-- Review focus areas or restrictions. Structured list format:
```
constraints:
  - type: <auto-inferred | user-specified>
  - focus: [spec | quality | security | ux | perf]
  - excluded_paths: [...]  (if --scope narrows)
  - additional_rules: [...]  (user-provided or inferred)
```
-->
