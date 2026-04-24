---
name: verify
description: Verify ForgeFlow work before any success, completion, gate, artifact, commit, PR, or ship claim; evidence before assertions.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must require fresh verification evidence before completion, success, artifact, gate, commit, PR, or ship claims.
  Must not accept subagent reports, stale command output, or assumed correctness as evidence.
  Must report exact command, exit code, result summary, and unresolved failures or residual risk.
---

# Verify

Use this skill before claiming ForgeFlow work is complete, fixed, passing, ready to ship, or approved by a gate.

## Iron law

```text
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you did not just verify the claim, do not make the claim. Say what is still unverified instead.

## Input

- The exact claim you are about to make
- Current plan / run-state / review-report if available
- Relevant artifact paths
- Project verification commands
- Git status and diff scope when code changed

## Output Artifacts

Return a concise verification report containing:

- Claim being verified
- Evidence source:
  - fresh command output
  - artifact inspection
  - gate artifact and approval status
  - git diff/status when relevant
- Exact command, if one was run
- Exit code
- Pass/fail result
- Residual risks or skipped checks
- Next required action if verification failed or was blocked

## Exit Condition

- Every success/completion claim has fresh evidence
- Every artifact or gate claim names the checked artifact/gate
- Subagent work has been independently checked
- Failures are reported plainly instead of softened into “probably fixed” nonsense

## Gate function

Before any positive status claim:

1. **Identify the claim.** Example: “tests pass”, “review approved”, “artifact is valid”, “ready to ship”.
2. **Choose the proof.** Pick the command, file read, schema check, git diff, or review artifact that proves that exact claim.
3. **Run or inspect it now.** Fresh evidence beats memory. Old logs are hints, not proof.
4. **Read the result.** Check the exit code, failing count, warnings, and actual output.
5. **State only what the evidence proves.** If one check passed but another was skipped, say that.

## Evidence rules

Good evidence:

- `pytest -q` fresh command output with exit code 0
- `make validate` fresh command output with exit code 0
- `git status --short` and `git diff --stat` showing intended scope
- A valid `review-report.json` with the expected `review_type` and `approved` status
- A schema validation command against the specific artifact being claimed

Bad evidence:

- “Looks good”
- “Should pass”
- “I changed the code, so it is fixed”
- “The subagent said it passed”
- A command from earlier in the session that ran before the latest change
- A partial check presented as full verification

## Subagent verification rule

Subagent reports are not evidence. They are leads.

When a subagent claims completion:

1. Inspect the produced diff or artifact yourself with `git diff`, `git status`, or direct file reads.
2. run the relevant verification command in the target repo.
3. Compare the result to the original requirement, not just the subagent summary.
4. Report mismatches directly.

## Artifact and gate claims

If you claim a ForgeFlow gate passed, name the gate and evidence:

```text
Gate: quality-review
Evidence: review-report.json, review_type=quality, approved=true
Verification: scripts/validate_sample_artifacts.py exit 0
```

If you claim an artifact is valid, name the artifact and validation path:

```text
Artifact: plan.json
Verification: python3 scripts/forgeflow_plan.py validate plan.json
Result: exit 0
```

Do not say “gate passed” because tests passed. Tests and gates are related, not identical.

## Handling blocked verification

If verification cannot be run, say so and stop short of success language:

```text
Verification blocked: npm is not installed in this environment.
Not claiming build success. Next action: run npm test in the project environment.
```

Blocked verification is not failure, but it is also not proof.

## Exact-output and dry-run constraints

If the user asks for exact output, dry-run only, or “do not run commands”, respect that constraint. In that case, provide a verification plan or checklist, not a fake result.

Bad:

```text
Tests pass. Run pytest -q to verify.
```

Good:

```text
Not verified here because command execution was disallowed. Manual check: run pytest -q and confirm exit code 0.
```

## Common red flags

Stop and verify before saying any of these:

- done
- fixed
- passes
- clean
- ready
- shipped
- approved
- no issues
- validated
- should work
- probably fine

“Should work” is not a status. It is a smell.
