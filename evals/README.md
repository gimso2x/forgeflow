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
- each referenced `files` path is repo-relative, tracked by git, and exists
- assertion types stay in the supported deterministic set
- assertion `value` / `values` entries are non-blank strings, so whitespace-only checks cannot pass accidentally
- persisted smoke `review-report.md` fixtures are concrete audit output, not unresolved templates
- review evals preserve the reported-vs-observed evidence boundary before approving verification
- final summaries do not overclaim provider/plugin E2E or live Claude/Codex/Gemini behavior from deterministic repo validators alone

## When adding a fixture

1. Add the eval object to `evals/evals.json` with the next sequential `id`.
2. Keep prompts on the current public workflow surface: `/forgeflow:clarify`, `/forgeflow:plan`, `/forgeflow:execute`, `/forgeflow:review`, `/forgeflow:ship`, and `/forgeflow:long-run`.
3. Reference only files that are committed in this repo.
4. Prefer assertions that prove exact contract behavior; avoid claims about Claude/Codex/Gemini live execution unless that provider smoke was actually run.
5. Run the local checks above before committing.
