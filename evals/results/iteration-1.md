# ForgeFlow Execution Evaluation Summary

## Scope

- Skill under evaluation: `forgeflow`
- Iteration: 1
- Evaluation type: with-skill vs baseline execution comparison
- Cases: 3
- Assertions: 12 per configuration

## Results

| Configuration | Passed | Total | Pass Rate | Tokens | Duration |
|---|---:|---:|---:|---:|---:|
| with_skill | 12 | 12 | 100% | 90,999 | 206.9s |
| without_skill | 9 | 12 | 75% | 64,482 | 132.1s |

## Per-case Results

| Eval | with_skill | without_skill | Signal |
|---|---:|---:|---|
| active-rule-clarify | 4/4 | 3/4 | Skill condition preserved concrete `.forgeflow/tasks/` artifact path. |
| propose-rule-long-run | 4/4 | 2/4 | Skill condition preserved full evolution-rule template fields and lifecycle/review status. |
| review-rule-boundary | 4/4 | 4/4 | Both conditions caught the invalid global-advisory hard-block boundary. |

## Remaining Baseline Failures

- `eval-0-active-rule-clarify/without_skill`: did not identify a concrete task artifact path under `.forgeflow/tasks/`.
- `eval-1-propose-rule-long-run/without_skill`: missed required evolution-rule template fields.
- `eval-1-propose-rule-long-run/without_skill`: did not clearly use `proposed` lifecycle and `unreviewed` review status.

## Interpretation

The actual execution evaluation supports the static review result: the ForgeFlow skill materially improves adherence to artifact-first behavior and the evolution rule lifecycle contract. The strongest gain is in long-run rule proposal, where the skill condition produced the complete reusable rule shape while baseline output missed lifecycle/template requirements.

## Source Artifacts

- `evals/evals.json`
- `forgeflow-eval-workspace/iteration-1/benchmark.json`
- `forgeflow-eval-workspace/iteration-1/benchmark.md`
- `forgeflow-eval-workspace/iteration-1/*/*/outputs/output.md`
- `forgeflow-eval-workspace/iteration-1/*/*/grading.json`
- `forgeflow-eval-workspace/iteration-1/*/*/timing.json`
