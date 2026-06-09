---
name: unstuck
description: Break through implementation or design blocks using lateral thinking personas. Use when the agent is stuck, looping, or unable to make progress after 2+ attempts. Not for normal planning or review.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must not replace plan or review — only unblocks stuck execution.
  Must offer at least 3 distinct personas.
  Must produce a concrete next action, not abstract advice.
dependencies:
  - skills/_shared/discipline.md
  - skills/_shared/role-architect.md
---

# Unstuck

Break through implementation or design blocks using lateral thinking personas.

## When to use

- Agent has failed 2+ times on the same task or subtask
- ff-loop stagnation detection triggers (spinning, oscillation, diminishing returns)
- User explicitly says "막혔다", "unstuck", "stuck", "모르겠어", "how to proceed"
- Review returns `changes_requested` with the same finding pattern twice

## Modes

### Solo mode (default)

Apply one selected persona to the problem:

| Persona | Lens | Question |
|---------|------|----------|
| **Hacker** | Exploit, workaround | "What's the fastest hack that works? What can we skip?" |
| **Researcher** | Evidence, precedent | "What does the codebase/lib docs say? What worked before?" |
| **Simplifier** | Reduction, deletion | "What can we remove entirely? What's the minimum viable change?" |
| **Architect** | Structure, abstraction | "What's the right abstraction? Where should the boundary be?" (see `skills/_shared/role-architect.md`) |
| **Contrarian** | Challenge assumptions | "What if the requirement is wrong? What if we do the opposite?" |

### Debate mode

Apply 2-3 personas and let them argue. Synthesize the best path forward.

## Procedure

1. **Problem statement**: Read the current blocker from `checkpoint.md` Blockers, `implementation-notes.md` Blocked By, or the user's description. State it in one sentence.

2. **Persona selection**:
   - Solo: pick the persona most likely to unblock based on the problem type:
     - Logic bug / edge case → Hacker
     - Missing knowledge / "how to" → Researcher
     - Scope creep / complexity → Simplifier
     - Structural / architecture friction → Architect
     - Wrong approach / repeated failure → Contrarian
   - Debate: pick 2-3 complementary personas.

3. **Apply the lens**:
   - Read the relevant code/artifacts through the persona's lens.
   - Identify 1-3 concrete actions the persona would recommend.
   - For debate mode: note where personas agree and disagree.

4. **Produce output**:
   - One concrete next action (file to edit, command to run, assumption to test)
   - If the action requires a plan change, note it as a deviation for `implementation-notes.md`
   - Do NOT implement the action — only recommend it

5. **Record in artifacts**:
   - Append to `implementation-notes.md` → Decisions:
     ```
     [unstuck] persona=<name> applied. Recommendation: <action>. Rationale: <why>.
     ```

## Exit Condition

- A concrete next action is recommended
- The blocker is either resolved or reframed as a bounded assumption
- The user can proceed without further agent help OR has a clear question to ask

## Constraints

- This is an advisory skill, not an execution skill. Do not edit code.
- Do not run for trivial blockers (missing import, typo). Save personas for genuine design/logic blocks.
- Maximum 3 rounds of unstuck per task. After 3, escalate to human.
- Output must include the persona used and the concrete action recommended.
