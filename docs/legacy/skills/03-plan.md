# Skill: plan

## Purpose

Turn `requirements.md` into an executable **plan.json** with task contracts. Every task contains exact file paths, acceptance criteria, and verification steps. No placeholders allowed.

## Trigger

- After `specify` produces `requirements.md`.
- User says: `"plan this"`, `"create a plan"`, or any intent to generate an executable task graph.

## Input

- `brief.json`
- `requirements.md`
- Codebase context

## Output Artifacts

| Artifact | Schema | Description |
|----------|--------|-------------|
| `plan.json` | `schemas/plan.schema.json` | Task graph with contracts, dependencies, and verification steps. |

## Execution

1. **Read all requirements and sub-requirements.** Every task must fulfill at least one sub-requirement.
2. **Decompose into tasks.** Each task should be completable in 2–10 minutes of focused implementation.
3. **Assign task contracts.** Every task object must include:
   - `id`: T1, T2, ...
   - `title`: One-line description.
   - `fulfills`: Array of requirement IDs this task satisfies.
   - `depends_on`: Array of task IDs that must complete first.
   - `files`: Exact file paths to create or modify.
   - `acceptance_criteria`: List of verifiable conditions.
   - `verification`: How to verify (test command, inspection step, or demo).
   - `parallel_safe`: Boolean. Can this run concurrently with others?
4. **Build dependency DAG.** Detect cycles. If a cycle exists, merge tasks or rethink decomposition.
5. **Estimate risk.** Tag high-risk tasks (touching critical paths, external APIs, or security boundaries).
6. **Write `plan.json`.**

## Constraints

- No placeholder text. If you don't know the exact file path yet, derive it from codebase conventions or ask.
- Every task must have at least one `fulfills` entry linking back to a requirement.
- `parallel_safe` defaults to `false`. Only mark `true` if the task is genuinely independent.

## Example `plan.json` fragment

```json
{
  "schema_version": "0.1",
  "task_id": "plan-001",
  "derived_from": "brief-001",
  "tasks": [
    {
      "id": "T1",
      "title": "Add ThemeContext provider",
      "fulfills": ["R1.1"],
      "depends_on": [],
      "files": ["src/contexts/ThemeContext.tsx"],
      "acceptance_criteria": ["Exports useTheme hook", "Reads initial value from localStorage"],
      "verification": "pnpm test ThemeContext",
      "parallel_safe": false
    }
  ]
}
```

## Complex tasks: milestone split

If the route is `large`, split the plan into milestones before writing `plan.json`:
- Each milestone is a mini-plan with its own task graph.
- Milestones are ordered and checkpointed independently.
- Write `plan.json` with a `milestones` array instead of a flat `tasks` array.
