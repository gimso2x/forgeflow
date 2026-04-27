# Skill: review

## Purpose

Perform an **information-isolated** post-execution verification. The reviewer reads only the plan, requirements, and final codebase — **no execution logs, no worker output, no chat history**.

## Trigger

- After `run` completes all tasks.
- User says: `"review the work"`, `"verify the implementation"`.
- Mandatory gate before `ship` on medium/large routes.

## Input

- `plan.json`
- `requirements.md`
- `brief.json`
- Final codebase (post-execution)

## Output Artifacts

| Artifact | Schema | Description |
|----------|--------|-------------|
| `review-report.json` | `schemas/review-report.schema.json` | Verdict, findings by severity, and next action. |

## Execution

1. **Load plan and requirements.** Do not load `decision-log.json`, execution transcripts, or chat history.
2. **Verify coverage.** Does every requirement have at least one task that fulfills it? Are there orphaned tasks that fulfill nothing?
3. **Inspect code against acceptance criteria.** For each task, check if its `acceptance_criteria` are met in the codebase.
4. **Check for regressions.** Run the full test suite. Any new failures?
5. **Check for slop.** Look for LLM-specific smells: over-commenting, unnecessary abstractions, verbose naming, defensive paranoia.
6. **Classify findings by severity:**
   - **critical:** Security bug, data loss, broken contract. Blocks ship.
   - **major:** Missing requirement, significant bug. Must fix before ship.
   - **minor:** Style issue, missed optimization. Can fix or ticket.
   - **info:** Suggestion, observation. Non-blocking.
7. **Write `review-report.json`.**

## Verdict rules

- `approved`: Zero critical/major findings.
- `approved_with_minor`: Only minor/info findings.
- `needs_fix`: One or more critical/major findings. Must re-run `run` for affected tasks.
- `needs_clarification`: Requirements ambiguity discovered. Return to `specify`.

## Constraints

- The reviewer must act as if they know nothing about how the code was written.
- Findings must reference specific requirements or task IDs.
- No gut feelings. Every finding links to a concrete criterion.
