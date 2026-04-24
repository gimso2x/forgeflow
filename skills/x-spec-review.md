---
name: x-spec-review
description: x-spec-review cross-cutting ForgeFlow skill
validate_prompt: |
  Must verify implemented behavior against requirements before quality preferences.
  Must block approval when requirements, artifacts, or evidence are missing.
  Must not conflate code style suggestions with spec compliance.
---

# Skill: x-spec-review

## Purpose

Verify that the implemented solution matches the stated requirements **before** quality review. This is a correctness gate, not a style gate.

## Trigger

- After `run` completes, before `review`.
- Required for `large` and `ultra` routes per `harness-v1-principles.md` #4.
- User says: `"did we build the right thing?"`, `"spec review"`.

## Input

| Artifact | Source |
|----------|--------|
| `requirements.md` | L0-L4 requirements |
| `plan.json` | Task contracts |
| Source files | Current codebase |

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| `spec-review-report.json` | Pass/fail per requirement with evidence |
| `decision-log.json` | Entry: spec-review result |

## Execution

1. Read `requirements.md`.
2. For each L1 requirement, verify it is implemented in the codebase.
3. For each L2 edge case, verify it is handled.
4. For each L3 performance/constraint target, verify it is met or explicitly deferred.
5. If any L1 requirement is missing or wrong, **fail** and stop. Do not proceed to quality review.
6. If all L1 requirements pass, write `spec-review-report.json` with `status: passed`.

## Constraints

- Spec-review failure blocks quality-review. No exceptions.
- Do not review code quality, naming, or tests here. Only correctness vs requirements.
- If a requirement is ambiguous, flag it in the report rather than guessing.

## Exit Condition

- `spec-review-report.json` exists with `status: passed` or `status: failed`.
- If failed, pipeline halts until requirements or implementation is corrected.

## Notes

- This is superpowers' "spec-review before quality-review" principle extracted into a cross-cutting skill.
- Without this gate, teams optimize the wrong solution beautifully.
