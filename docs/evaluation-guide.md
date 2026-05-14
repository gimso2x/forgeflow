# Evaluation guide

ForgeFlow evals are executable workflow checks. They are not prose guidelines, and they are not a replacement for unit tests. Unit tests verify code behavior; evals verify that the harness still enforces its artifact, stage, route, and review contracts end to end.

## Quick start

From a fresh clone, prepare the repo-managed virtualenv first:

```bash
make setup
make check-env
make evals
```

For only the workflow adherence suite:

```bash
make adherence-evals
```

Both targets use `.venv` through the Makefile. A failing eval exits non-zero, so CI can trust the command status directly.

## Current suites

- `adherence` — validates route/stage/gate behavior against positive and negative fixtures. It catches policy bypasses such as missing required artifacts, stale task IDs, out-of-sequence checkpoints, invalid review reports, and long-run gates without eval evidence.

Suite details live in:

- `evals/README.md`
- `evals/adherence/README.md`
- `scripts/run_evals.py`
- `scripts/run_adherence_evals.py`

## Reading results

`make evals` prints suite-level status:

- `FORGEFLOW EVALS: PASS` — every registered suite passed.
- `FORGEFLOW EVALS: FAIL` — at least one registered suite failed.
- `EVAL SUITE: <name> PASS` — one suite passed.
- `EVAL SUITE: <name> FAIL exit_code=<n>` — one suite failed and returned a non-zero exit code.

The adherence runner also prints individual fixture outcomes. Positive fixtures should run to the expected terminal stage. Negative fixtures should be blocked with the expected `RuntimeViolation`. If a negative fixture starts passing, that is usually bad: the harness just lost a guardrail.

## Adding or changing a suite

1. Add or update fixtures under `evals/<suite>/` or the relevant runtime fixture directory.
2. Document the fixture intent in the suite README.
3. Add the runner command to `scripts/run_evals.py`.
4. Add a Makefile target if developers need to run the suite directly.
5. Add or update tests that lock the runner contract.
6. Run `make evals` and the narrow tests touched by the suite.

Do not add a docs-only eval. If it cannot fail automatically, it is not an eval; it is a wish with Markdown syntax highlighting.

## PR checklist

For changes touching routes, stages, artifact schemas, review gates, policy, or examples:

- Run `make evals` or explain why it is not relevant.
- Include the eval command and result in the PR body or handoff.
- Update `evals/README.md` and this guide when adding a new suite or changing output semantics.
