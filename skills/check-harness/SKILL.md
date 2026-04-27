---
name: check-harness
description: Score ForgeFlow harness health and identify the smallest fixes that improve reliability.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must score entry points, shared context, execution habits, verification, and maintainability.
  Must provide actionable fixes rather than vague advice.
  Must not introduce a new workflow stage or bypass existing ForgeFlow gates.
---

# Check Harness

Use this cross-cutting skill to inspect whether a ForgeFlow installation or repository harness is easy for agents to run safely.

## Input

- Repository root
- Harness docs and policy files, when present:
  - `README.md`
  - `INSTALL.md`
  - `AGENTS.md`, `CLAUDE.md`, `CODEX.md`, or generated adapters
  - `skills/SKILLS.md`
  - `policy/canonical/*.yaml`
  - `scripts/*`
  - `tests/*`
- Recent validation output, if available

## Output Artifacts

Return or write a harness health report containing:

- total score out of 100
- category scores
- evidence refs for each score
- top blockers
- smallest sufficient fixes
- verification commands to rerun

If a writable task directory is provided, write the report to `harness-health.md`. Otherwise return it in the response.

## Scoring Categories

Score each category from 0 to 20.

1. **Entry points**
   - commands are discoverable
   - plugin/slash command paths match CLI paths
   - first-run instructions are executable
2. **Shared context**
   - canonical prompts/policy are single-source enough
   - generated adapters warn against manual edits
   - task artifacts have schemas or examples
3. **Execution habits**
   - stage boundaries are explicit
   - no automatic cross-stage chaining
   - worker/reviewer responsibilities are separated
4. **Verification**
   - validation commands exist
   - tests cover contracts and failure modes
   - generated artifacts can be checked for drift
5. **Maintainability**
   - docs are not duplicated beyond usefulness
   - imported ideas are adapted, not pasted wholesale
   - changes are request-traceable and small enough to review

## Procedure

1. Inspect the repository structure and key docs.
2. Score each category with concrete evidence refs.
3. Identify the top three fixes that would improve the score fastest.
4. Prefer small contract or documentation fixes before adding new runtime machinery.
5. If evidence is missing, say so plainly instead of guessing.

## Constraints

- This is a diagnostic skill, not a new ForgeFlow stage.
- Do not rewrite the harness while scoring it unless the user separately asks for implementation.
- Do not recommend a full scaffold reset when a smaller fix satisfies the problem.

## Exit Condition

- Five category scores are present.
- Total score out of 100 is present.
- At least one actionable fix is listed unless the score is perfect.
- Evidence refs distinguish observed files/commands from missing or reported evidence.
