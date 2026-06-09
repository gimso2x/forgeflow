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

`VERSION` 파일이 단일 소스. CI(`sync-version.yml`)가 push 시 자동으로 7개 매니페스트를 동기화하므로, **`VERSION`만 수정**하고 나머지는 건드리지 않는다.

| File | Field |
|------|-------|
| `VERSION` | plain text `X.Y.Z` (단일 소스, **직접 수정**) |
| `SKILL.md` | `version: "X.Y.Z"` (CI 자동 동기화) |
| `.claude-plugin/plugin.json` | `"version": "X.Y.Z"` (CI 자동 동기화) |
| `.claude-plugin/marketplace.json` | `"metadata"."version": "X.Y.Z"` (CI 자동 동기화) |
| `.codex-plugin/plugin.json` | `"version": "X.Y.Z"` (CI 자동 동기화) |
| `.cursor-plugin/plugin.json` | `"version": "X.Y.Z"` (CI 자동 동기화) |
| `plugin.json` | `"version": "X.Y.Z"` (CI 자동 동기화) |

Also add a `## [X.Y.Z] - YYYY-MM-DD` section to `CHANGELOG.md` before release.

## Instructions

### 1. Determine version bump

- Read current version from `.claude-plugin/plugin.json`.
- Ask the user: patch (default), minor, or major? If the user already specified, use that.
- Bump version following semver:
  - patch: Z+1 (bug fixes, small improvements)
  - minor: Y+1, Z=0 (new features, skill additions)
  - major: X+1, Y=0, Z=0 (breaking changes)

### 2. Update VERSION file

Edit **only** `VERSION`. CI(`sync-version.yml`)가 push 후 나머지 매니페스트 7개를 자동 동기화한다. manifest 파일을 직접 수정하지 마라.

### 3. Generate changelog

- Run `git log <previous-version-tag>..HEAD --oneline` to collect commits since last release.
- Summarize changes in Korean for the release notes.
- Group by theme if there are many commits.

#### Changelog classification (v1.12+)

새 버전부터 CHANGELOG를 영향 축 기준으로 분류한다. 기존 Keep a Changelog 섹션(Added/Changed/Fixed/Removed) 대신:

| 영향 축 | 설명 | 대표 키워드 |
|---------|------|------------|
| 🔒 자동화·정합성 | validator, CI, drift guard, artifact 정합성 | validation, guard, drift, 검증, contract |
| 🔍 검증·정책 | advisory contract, role/evidence/stage boundary, eval | role, evidence, stage, eval, boundary, handoff |
| ⚡ 속도·안정성 | 중복 제거, 경량화, stub 정리, 성능 | duplicate, phony, stub, residue, regress |
| 👤 사용자·경험 | README, 산출물 가이드, 설치, 한국어 docs | README, reader-facing, user-facing, 설명, guidance |

분류 규칙:
1. 항목이 여러 축에 해당하면 **가장 구체적인 축** 우선 (예: README + validation → 👤 사용자·경험)
2. 기존 버전(1.11.x 이하)은 retroactive 재분류하지 않음
3. `validate_changelog_links.py`가 두 포맷(Keep a Changelog + 영향 축) 모두 허용

### 4. Stage and commit

- Stage only: `git add VERSION CHANGELOG.md`
- Commit message format: `[main] v<X.Y.Z> 릴리즈` or `[main] <change summary> 및 v<X.Y.Z> 릴리즈`

### 5. Push

- `git push origin main` — CI가 매니페스트 버전을 자동 동기화한다.

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
