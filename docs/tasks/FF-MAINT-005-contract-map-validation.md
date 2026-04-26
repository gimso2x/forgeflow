# FF-MAINT-005: Harden Contract Map Validation

Priority: P1
Status: Landed in local review stack
Type: docs/structure validation
Primary file: `docs/contract-map.md`
Candidate tests: `tests/test_validate_structure.py`, optionally `tests/test_contract_map.py`

## Problem

`docs/contract-map.md` is a useful source-of-truth index, but its claims can drift from the repository unless some of them are validated.

The document currently records source surfaces, regeneration commands, validation commands, and consumers. That is good. The next step is not a bigger document. The next step is a small check that catches the most expensive drift.

## Goal

Add small, boring validation for high-risk contract-map claims.

## Non-goals

- Do not build a complete documentation linter.
- Do not make every sentence machine-verified.
- Do not require perfect parsing of markdown tables.
- Do not change contract surfaces and validation rules in the same large commit.

## Candidate checks

Pick one or two first:

- `docs/contract-map.md` exists and is required by structure validation.
- Runtime seam names in the map correspond to real files.
- Validation commands named in the map reference real scripts or test paths.
- `adapters/generated/*` is documented as generated output, not source of truth.
- `adapters/targets/*` is documented as adapter source.
- `scripts/*.py` is documented as thin CLI/validation entrypoints.

## Suggested implementation steps

1. Add a small failing assertion for one contract-map claim.
2. Update `docs/contract-map.md` only if the current wording is insufficient.
3. Keep the test simple enough that future maintainers can fix it without reverse-engineering a parser.
4. Run structure tests, validation, and full pytest.

## Acceptance criteria

- At least one high-risk contract-map claim is automatically checked.
- The check is low-brittleness.
- `docs/contract-map.md` remains concise.
- No unrelated runtime or adapter behavior changes are included.

## Suggested narrow validation

```bash
python -m pytest tests/test_validate_structure.py -q
make validate
python -m pytest -q
git diff --check
git status --short
```

## Commit message

```text
docs: harden contract map validation
```
