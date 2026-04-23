# missing-eval-record-before-long-run

Large/high-risk route negative fixture.

- `brief.json`, `plan.json`, `review-report-spec.json`, `review-report-quality.json` exist
- `eval-record.json` is intentionally missing
- orchestrator should refuse `long-run` because `worth_long_run_capture` cannot be satisfied
