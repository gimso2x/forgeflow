---
description: >
  ForgeFlow plugin release workflow: version bump → commit → push → GitHub release → docs sync.
  Use this skill whenever the user says anything about releasing, publishing, version bumping,
  or deploying the forgeflow plugin — including phrases like "커밋 푸시", "릴리즈", "배포",
  "버전 올려", "플러그인 업데이트", or "출시". Also trigger on "commit push release" or "ship plugin".
---

# /forgeflow:release

ForgeFlow plugin release workflow. Syncs version across all metadata files, commits, pushes, creates a GitHub release, and updates docs.

## Prerequisites

- Clean working tree (no unstaged changes). If dirty, stop and ask the user to commit or stash first.
- On `main` branch. If on another branch, stop and confirm.
- `gh` CLI available and authenticated.

## Version files

These files must always have identical versions:

| File | Field |
|------|-------|
| `VERSION` | plain text `X.Y.Z` |
| `SKILL.md` | `version: "X.Y.Z"` in frontmatter |
| `.claude-plugin/plugin.json` | `"version": "X.Y.Z"` |
| `.claude-plugin/marketplace.json` | `"metadata"."version": "X.Y.Z"` |
| `.codex-plugin/plugin.json` | `"version": "X.Y.Z"` |
| `.cursor-plugin/plugin.json` | `"version": "X.Y.Z"` |
| `gemini-extension.json` | `"version": "X.Y.Z"` |

Also add a `## [X.Y.Z] - YYYY-MM-DD` section to `CHANGELOG.md` before release.

## Instructions

### 1. Determine version bump

- Read current version from `.claude-plugin/plugin.json`.
- Ask the user: patch (default), minor, or major? If the user already specified, use that.
- Bump version following semver:
  - patch: Z+1 (bug fixes, small improvements)
  - minor: Y+1, Z=0 (new features, skill additions)
  - major: X+1, Y=0, Z=0 (breaking changes)

### 2. Sync version across files

Update all version files with the new version number. Use Edit tool — do not rewrite entire files.

### 3. Generate changelog

- Run `git log <previous-version-tag>..HEAD --oneline` to collect commits since last release.
- Summarize changes in Korean for the release notes.
- Group by theme if there are many commits.

### 4. Stage and commit

- Stage only the version files explicitly: `git add VERSION SKILL.md CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json .cursor-plugin/plugin.json gemini-extension.json`
- Commit message format: `[main] v<X.Y.Z> 릴리즈` or `[main] <change summary> 및 v<X.Y.Z> 릴리즈`

### 5. Push

- `git push origin main`

### 6. Create GitHub release

```bash
gh release create v<X.Y.Z> \
  --title "v<X.Y.Z>" \
  --notes "<changelog>"
```

### 7. Report

Output a summary:
- 버전: X.Y.Z
- 커밋: SHA
- 릴리즈: GitHub release URL
- 변경사항: changelog summary

## Safety rules

- Never force push.
- Never commit files the user didn't approve.
- If `gh release create` fails, report the error and suggest manual retry.
- If the version files are already out of sync, warn the user before proceeding.
