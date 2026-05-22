# ForgeFlow eval fixtures

`evals/evals.json` is a deterministic prompt-contract fixture set for the slim v1.x markdown distribution. It is not a live provider benchmark.

## Local checks

Run the same non-mutating checks used by the `evals` GitHub Actions workflow:

```bash
make validate-evals-json validate-eval-files validate-evals-fixtures
```

These validators ensure that:

- eval IDs are integer and sequential from `0`
- eval names are unique
- eval names use kebab-case slugs so fixture IDs stay stable in logs and result paths
- each referenced `files` path is repo-relative, tracked by git, exists, and is not duplicated within the same eval case
- assertion types stay in the supported deterministic set (`contains`, `contains_all`, `contains_any`, `equals`, `not_contains`, `not_contains_any`)
- assertion `value` / `values` entries are non-blank strings, so whitespace-only checks cannot pass accidentally
- multi-value assertion `values` entries are unique, so duplicated alternatives cannot make coverage look broader than it is
- assertion `text` entries are unique within each eval case, so duplicate audit rationale cannot hide missing contract coverage
- persisted smoke `review-report.md` fixtures are concrete audit output, not unresolved templates
- review evals preserve the reported-vs-observed evidence boundary before approving verification
- final summaries do not overclaim provider/plugin E2E or live Claude/Codex/Gemini behavior from deterministic repo validators alone
- fixture text avoids stale workflow vocabulary (`/forgeflow:finish`, `/forgeflow-init`, `large_high_risk`, and other removed commands) so prompts, expectations, assertions, and fixture names stay on the active public skill surface
- ship-stage fixture names use `ship-*` slugs even when testing branch-disposition safety, so eval result paths do not imply a removed finish stage
- long-run evolution fixtures record candidate notes in `eval-record.md` without claiming direct writes to `.forgeflow/evolution/proposed/`; ship owns rule materialization
- autonomous maintainer runs use `git branch --show-current` to confirm the expected target branch, stop on wrong-branch preflight before pull/edit/commit/push, and stop on user/unknown dirty paths before pull/edit/clean/commit/push mutations, including a second `git status --short` check after `git pull --ff-only`, a final `git status --short` check before staging intentional files, explicit-path staging instead of broad `git add -A` / `git add .`, a post-push `git status --short` check before claiming cleanliness, and no cron/crontab or external schedule mutation from inside the scheduled run
- autonomous maintainer final reports keep the required Korean headings (`요약`, `변경한 것`, `검증`, `커밋/푸시`, `다음 후보`, `블로커`), exact validation evidence, commit/push status, no separate `send_message` delivery step, no live provider/plugin E2E overclaim, explicit no-op commit refusal when no safe focused change is available, validation failures reported as blockers with no commit/push, and failed pushes reported as blockers rather than delivered changes
- silent scheduled ticks use exactly `[SILENT]` with no headings or explanatory prose when there is genuinely nothing new to report
- ship-stage fixtures refuse unresolved artifact residue such as TODO/template comments or angle-bracket placeholders before final handoff language
- Cursor onboarding fixtures keep the colon-free command namespace (`/clarify`, `/plan`, `/execute`, `/review`, `/ship`) distinct from Claude/Codex `/forgeflow:*` commands
- adapter setup fixtures keep plugin/extension install or cache locations separate from the target project root where `.forgeflow/tasks/<task-id>/` artifacts are written
- docs-review fixtures block broken Markdown links/anchors and removed slim-surface paths with deterministic `make validate-markdown-links` / `make validate-slim-surface` evidence, not provider/plugin E2E claims

## When adding a fixture

1. Add the eval object to `evals/evals.json` with the next sequential `id`.
2. Keep prompts on the current public workflow-stage surface: `/forgeflow:clarify`, `/forgeflow:plan`, `/forgeflow:execute`, `/forgeflow:review`, `/forgeflow:ship`, and `/forgeflow:long-run`; benchmark fixtures must use `/forgeflow:benchmark` and keep benchmark sizes (`small`/`medium`/`large`) distinct from workflow route labels (`small`/`medium`/`high`/`epic`).
3. Reference only files that are committed in this repo.
4. Prefer assertions that prove exact contract behavior; keep `expected_output` as human-readable context only.
5. Put every required pass/fail contract string in `assertions` (`contains*`, `equals`, `not_contains*`) so deterministic validators and future harnesses can evaluate it without interpreting prose.
6. Avoid claims about Claude/Codex/Gemini live execution unless that provider smoke was actually run.
7. Run the local checks above before committing.
