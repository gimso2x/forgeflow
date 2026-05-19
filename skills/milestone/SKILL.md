---
name: milestone
description: Create and manage hierarchical milestones for a project using parallel reviewer analysis. Decomposes epic-scale work into independently deliverable milestones with dependency DAG, success criteria, and integration verification. Use when the user types /forgeflow:milestone, or when clarify routes to epic.
version: 0.3.0
author: gimso2x
validate_prompt: |
  Must produce roadmap.md conforming to the templates/roadmap.md format.
  Must include measurable success criteria for each milestone.
  Must append an Integration Verification milestone as the final node.
  Must not create more than 10 milestones without explicit user approval.
---

# Milestone

Break large, multi-day tasks into optimized milestones with dependency ordering and integration verification. Adapted from the Ultraplan parallel-reviewer approach.

## Trigger

- When the user types `/forgeflow:milestone`, `/forgeflow:milestone new`, or `/forgeflow:milestone progress`.
- When `/forgeflow:clarify` routes to `epic`.
- When a task needs multiple plan-execute-review cycles.

## Input

| Artifact | Source |
|----------|--------|
| `brief.md` | Active task workspace |
| Codebase context | Direct inspection |

## Output Artifacts

| Artifact | Format | Description |
|----------|--------|-------------|
| `roadmap.md` | `templates/roadmap.md` | Milestone definitions, dependency DAG, statuses |
| Reviewer outputs | Per-milestone notes | Feasibility, architecture, risk, dependency, user-value analysis |

## Procedure

### Phase 1: Problem framing

1. Read `brief.md` and identify: goal, scope boundaries, technical constraints, success criteria.
2. If a codebase is involved, inspect relevant architecture and file structure.
3. Compose a **Problem Brief** -- a self-contained summary that guides decomposition:

   Include: Goal, Scope (In/Out), Technical Context, Constraints, Success Criteria, and Verification Strategy (the highest-level verification command and what passing it proves).

4. Run verification discovery: search for e2e tests, integration tests, test suite, build+lint. Record the best available verification.

### Phase 2: Five-angle pressure test

Analyze the problem from five independent angles. For each angle, produce a structured assessment:

1. **Feasibility**: Can each component be built with the stated tech stack? Classify effort as Small (1-3 tasks), Medium (4-8 tasks), Large (9+ tasks), or Uncertain (needs spike). Flag components with hidden complexity.

2. **Architecture**: Identify shared interfaces, state mutations, and module boundaries. Map which files are touched by which work. Flag files touched by multiple streams -- these create ordering constraints.

3. **Risk**: Rate each component for technical risk and risk of underestimation. Identify components needing prototype before planning. Flag blast radius of potential failures.

4. **Dependency**: Map all ordering constraints -- file conflicts, interface dependencies, shared state. Identify parallelizable groups (zero dependencies between them). Draw the dependency DAG.

5. **User value**: Rank work by user-visible impact. Identify the minimum milestone that delivers standalone value.

### Phase 3: Synthesis

1. Define milestone boundaries based on the five-angle analysis:
   - Each milestone should be independently deliverable and testable
   - Target 3-8 tasks per milestone (sweet spot for a single plan-execute-review cycle)
   - Milestones that are too large (>12 tasks) should split; too small (1-2 tasks) should merge

2. Build the dependency DAG. Mark parallelizable groups explicitly.

3. **Append Integration Verification milestone** as the final node (`M_final`):
   - Depends on ALL other milestones
   - Read-only verification -- no new code
   - Runs the highest-level verification discovered in Phase 1
   - Validates cross-milestone interfaces end-to-end

4. Write `roadmap.md` following the format in `templates/roadmap.md`:
   - Each milestone section includes: name, objective, success criteria, depends on, status
   - Include a Tasks per Milestone section with checkboxes
   - Include the Integration Verification section
   - Include a Progress Summary section

5. Present the milestone plan to the user for approval.

### Phase 4: Progress tracking (when invoked with `progress`)

1. Read `roadmap.md` and any state artifacts from the active task directory.
2. Report: completion percentage, current milestone, next actionable milestone.
3. If a milestone has failed, recommend whether to retry, adjust, or escalate.

## Anti-patterns

| Anti-Pattern | Why It Fails |
|---|---|
| Accepting milestones without measurable success criteria | "Done" becomes subjective |
| Creating milestones too large (>12 tasks) | Exceeds single plan cycle; context loss |
| Creating milestones too small (1-2 tasks) | Overhead exceeds the work itself |
| More than 10 milestones without user approval | Compounding risk; likely needs project split |
| Skipping integration verification milestone | Milestones pass independently but break at boundaries |
| Running reviewers sequentially when parallel is possible | Wastes time; reviewers are independent |
| Ignoring dependency conflicts | Surface during execution when expensive to fix |

## File write and output discipline

Write `roadmap.md` to the active task directory. If the task directory is missing, bootstrap it first. If a roadmap already exists, update status instead of overwriting unless the user requests a fresh decomposition.

## Exit Condition

- `roadmap.md` is written following `templates/roadmap.md` format
- Every milestone has a name, goal, measurable success criteria, and dependencies
- Integration Verification milestone is present as the final node
- Dependency DAG is valid (no cycles, no orphans)
- User has approved the milestone plan
- Next step: `/forgeflow:plan` for the first milestone, or `/forgeflow:execute` if a plan already exists

## Notes

- Milestone planning is the entry point for epic routes. For smaller work, use `/forgeflow:plan` directly.
- The milestone phase does not write code. It decomposes and orders work.
- Each milestone will later get its own `plan.md` during the plan stage.
