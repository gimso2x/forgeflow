---
name: safe-commit
description: Pre-commit safety review for ForgeFlow changes. Use before committing or shipping local changes.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must inspect the actual diff before recommending commit.
  Must check for secrets, oversized/generated files, scope drift, and verification evidence.
  Must end with exactly one final disposition: SAFE or UNSAFE.
---

# Safe Commit

Use this cross-cutting skill before creating a commit or preparing a handoff that includes repository changes.

## Input

- Current `git status --short`
- Current `git diff --stat`
- Current `git diff` or an explicitly provided patch
- Relevant ForgeFlow artifacts when available:
  - `brief.json`
  - `requirements.md`
  - `plan.json`
  - `review-report.json`
- Verification command outputs or a clear statement that verification was not run

## Output Artifacts

Return or write a safe-commit report containing:

- changed files summary
- request-traceability notes
- secret scan result
- oversized/generated file check
- scope drift check
- verification evidence summary
- blockers, if any
- final disposition: `SAFE` or `UNSAFE`

If a writable task directory is provided, write the report to `safe-commit-report.md`. Otherwise return it in the response.

## Procedure

docs/review-model.md owns git-safety policy. Do not redefine git safety in this skill; apply that canonical policy while reviewing the commit candidate:

- Broad staging is forbidden unless explicitly justified by the requested scope.
- Destructive git actions require explicit user approval.
- Dirty user work is preserved by default.

1. Inspect the real diff; do not rely on memory or worker vibes.
2. Run or inspect a secret scan appropriate to the repository. At minimum, search changed content for obvious token/key patterns and credential files.
3. Check file-size and generated-file risk:
   - no accidental binaries
   - no cache/build outputs
   - no oversized logs
   - generated adapters are included only when canonical sources changed
4. Check request traceability:
   - every changed file should map to the active request, task document, or approved plan
   - flag drive-by refactors and unrelated cleanup
5. Check verification evidence:
   - cite exact commands personally run in this turn, or label evidence as reported/missing
   - do not convert reported evidence into observed evidence
6. Choose disposition:
   - `SAFE` only when no blockers remain and verification evidence is adequate for the change risk
   - `UNSAFE` when secrets, scope drift, missing critical verification, or unexplained files remain

## Constraints

- Do not commit automatically unless the user explicitly asked to commit.
- Do not delete or rewrite unrelated files to make the tree look clean.
- Do not expose secret values. Redact credentials as `[REDACTED]`.
- Do not approve a commit with unresolved critical or major blockers.

## Exit Condition

- The diff has been inspected.
- Secret, file-size/generated, scope drift, and verification checks are recorded.
- The final line includes exactly one disposition token: `SAFE` or `UNSAFE`.
