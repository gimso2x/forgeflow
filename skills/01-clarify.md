# Skill: clarify

## Purpose

Turn a vague user request into a scoped **Context Brief** with an assigned complexity route. This is the **only** skill allowed to guess the route.

## Trigger

- User says: `"I want to..."`, `"I need..."`, `"Let's build..."`, `"Fix this..."`
- Any request where scope, constraints, or acceptance criteria are unclear.

## Input

- Raw user request (free text)
- Current codebase context (if available)

## Output Artifacts

| Artifact | Schema | Description |
|----------|--------|-------------|
| `brief.json` | `schemas/brief.schema.json` | Context Brief with goal, constraints, complexity score, and assigned route. |

## Execution

1. **Ask up to 3 Socratic questions** to surface hidden assumptions.
   - Do not ask more than 3. If the request is already clear, ask 0.
2. **Explore the codebase** (if one is open) to ground the brief in reality.
   - Look at existing structure, conventions, and similar features.
3. **Score complexity** on a scale of 5–15 using these heuristics:
   - **5–8 (small):** Single file change, well-understood domain, no new dependencies.
   - **9–12 (medium):** Multi-file change, some uncertainty, one external dependency.
   - **13–15 (large):** Architectural change, high uncertainty, multiple stakeholders, long-running.
4. **Assign route** based on score:
   - small → `clarify → run → review → ship`
   - medium → `clarify → specify → plan → run → review → ship`
   - large → `clarify → x-office-hours → specify → plan → run → x-spec-review → review → ship` (with checkpoints)
5. **Write `brief.json`** with schema version `0.1`.

## Constraints

- The brief **must not** contain implementation details. Only goal, constraints, and scope.
- Complexity score must be an integer. No fractional scores.
- If the user explicitly requests a route, use theirs but document the override in `brief.json`.

## Example `brief.json`

```json
{
  "schema_version": "0.1",
  "task_id": "brief-001",
  "goal": "Add a dark mode toggle to the settings page",
  "constraints": ["Must respect system preference", "Persist to localStorage"],
  "complexity_score": 7,
  "route": "small",
  "context_summary": "React app with existing settings page at /settings",
  "open_questions": []
}
```
