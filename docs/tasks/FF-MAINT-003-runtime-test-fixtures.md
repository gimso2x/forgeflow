# FF-MAINT-003: Consolidate Runtime Test Fixtures Carefully

Priority: P1
Status: Proposed
Type: test maintainability
Primary area: `tests/runtime/`
Candidate file: `tests/runtime/conftest.py`

## Problem

Runtime test modules are healthier after the earlier mega-test split, but several files remain large and likely duplicate setup helpers. Examples include checkpoint/resume, orchestrator CLI, and generated artifact validation coverage.

Large tests are not the problem by themselves. The problem is repeated setup that makes small behavior changes require edits across many files.

## Goal

Reduce obvious duplicated runtime test setup while preserving scenario coverage and assertions.

## Non-goals

- Do not delete large scenario tests because they are large.
- Do not weaken assertions.
- Do not move runtime code in the same commit.
- Do not create a vague shared fixture dumping ground.
- Do not force all test modules to use shared fixtures if local helpers are clearer.

## Candidate fixture targets

Only consolidate helpers after confirming real duplication. Possible candidates:

- task directory creation
- JSON write/read helpers
- medium-route plan ledger setup
- schema validation helper
- common runtime policy loading setup

Avoid extracting bespoke scenario setup that is clearer inline.

## Suggested implementation steps

1. List duplicated helpers across `tests/runtime/*.py`.
2. Pick exactly one helper family.
3. Move it into `tests/runtime/conftest.py` or a behavior-named fixture module.
4. Update only the modules using that helper family.
5. Keep test names and assertions unchanged.
6. Run narrow tests for touched modules, then full validation.

## Acceptance criteria

- One duplicated setup family is consolidated.
- No scenario coverage is removed.
- No runtime behavior changes are included.
- Test readability improves or at least does not degrade.
- The diff is mostly fixture plumbing, not assertion rewrites.

## Suggested narrow validation

Adjust touched modules, for example:

```bash
python -m pytest tests/runtime/test_checkpoint_resume.py tests/runtime/test_status_resume.py -q
python -m pytest tests/runtime -q
make validate
python -m pytest -q
git diff --check
git status --short
```

## Commit message

```text
test: consolidate runtime fixture setup
```
