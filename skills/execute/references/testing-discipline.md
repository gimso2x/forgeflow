# Testing And Debugging Discipline

Use this reference during `/forgeflow:execute` when choosing verification depth, handling lint failures, applying TDD, debugging failures, or writing timestamped execution evidence.

## Route-aware Testing

Testing approach differs by route to balance speed and safety:

| Route | Approach | Rationale |
|-------|----------|-----------|
| small | No mandatory tests. Run lint/build only. | 1-2 file changes; overhead exceeds value |
| medium | **Test-after**: implement first, then write tests to cover the happy path + key edge cases. No dedicated "Red" step. | 구현 후 테스트가 빠르고 토큰 절약. T1 테스트 전용 단계를 plan에 넣지 마라 |
| high | **TDD for logic steps only**: Red->Green->Refactor for steps that change business logic, state management, or API contracts. Style/config steps use test-after. | 핵심 로직은 TDD, 나머지는 경량화 |
| epic | **Full TDD**: Red->Green->Refactor for every implementation step. | 가장 높은 품질 보장 필요 |

For medium route test-after:
1. Implement the code change.
2. Write tests covering the objective's happy path and critical edge cases.
3. Run tests to confirm pass.
4. If tests fail, fix implementation, not the test. The test is written against working code.

For high/epic TDD:
1. **Red**: Write a failing test that covers the objective. Run it and confirm failure.
2. **Green**: Write the minimal code to pass the test.
3. **Refactor**: Improve the code while keeping tests green.

## Scoped lint for isolated changes

When the full lint fails due to pre-existing errors outside the changed scope:
1. Confirm the failure is not in newly changed code.
2. Run scoped lint on changed files only.
3. Record pre-existing errors as minor findings in `implementation-notes.md` Evidence.
4. Do not block ship on pre-existing lint errors in unchanged code.

## Hypothesis-Driven Debugging

If a bug or failure occurs during implementation/verification:
1. Document the reproduction steps and observed issue in `implementation-notes.md`.
2. List causal hypotheses.
3. Test each hypothesis.
4. Apply the fix only after the root cause is verified. Avoid trial-and-error coding.

## Progress and timestamp discipline

All timestamps in `implementation-notes.md` must be real ISO 8601 values, not placeholders.

If the task directory is missing, bootstrap or recover it first. Do not jump straight into source edits while the workflow state lives nowhere.
