# Epic Decomposition (Phase 0)

> Reference for ff-plan's epic route decomposition. Extracted from ff-plan SKILL.md.

If the route is `epic` and no `roadmap.md` exists in the task directory, run epic decomposition before task planning. If `roadmap.md` already exists, skip decomposition and plan the next incomplete milestone. If the user provides `--milestone M2`, plan only that milestone.

## Epic Problem framing

1. Read `brief.md` and identify: goal, scope boundaries, technical constraints, success criteria.
2. If a codebase is involved, inspect relevant architecture and file structure.
3. Compose a **Problem Brief** — a self-contained summary that guides decomposition:

   Include: Goal, Scope (In/Out), Technical Context, Constraints, Success Criteria, and Verification Strategy (the highest-level verification command and what passing it proves).

4. Run verification discovery: search for e2e tests, integration tests, test suite, build+lint. Record the best available verification.

## Five-angle pressure test

Analyze the problem from five independent angles. For each angle, produce a structured assessment:

1. **Feasibility**: Can each component be built with the stated tech stack? Classify effort as Small (1-3 tasks), Medium (4-8 tasks), Large (9+ tasks), or Uncertain (needs spike). Flag components with hidden complexity.
2. **Architecture**: Identify shared interfaces, state mutations, and module boundaries. Map which files are touched by which work. Flag files touched by multiple streams — these create ordering constraints.
3. **Risk**: Rate each component for technical risk and risk of underestimation. Identify components needing prototype before planning. Flag blast radius of potential failures.
4. **Dependency**: Map all ordering constraints — file conflicts, interface dependencies, shared state. Identify parallelizable groups (zero dependencies between them). Draw the dependency DAG.
5. **User value**: Rank work by user-visible impact. Identify the minimum milestone that delivers standalone value.

## Synthesis

Apply these synthesis heuristics to convert five-angle analysis into milestone boundaries:

| Signal from analysis | Synthesis action |
|---|---|
| Feasibility = Uncertain | Extract as a spike milestone (time-boxed exploration, no production code) |
| Risk = High + blast radius = wide | Isolate behind an interface milestone; dependents wait for interface stabilization |
| Dependency = zero between two groups | Mark as parallelizable; assign different milestone numbers |
| User value = standalone | Ship first for early feedback, even if technically dependent on nothing |
| Architecture = shared file touched by multiple streams | Create a "foundation" milestone that stabilizes the shared surface before dependents |
| Component = Large (9+ tasks) | Split into "core" + "extensions" milestones; core ships first |

1. Define milestone boundaries based on the synthesis:
   - Each milestone should be independently deliverable and testable
   - Target 3-8 tasks per milestone (sweet spot for a single plan-execute-review cycle)
   - Milestones that are too large (>12 tasks) should split; too small (1-2 tasks) should merge

2. Build the dependency DAG. Mark parallelizable groups explicitly.

3. **Append Integration Verification milestone** as the final node (`M_final`):
   - Depends on ALL other milestones
   - Read-only verification — no new code
   - Runs the highest-level verification discovered in Phase 1
   - Validates cross-milestone interfaces end-to-end

4. Write `roadmap.md` following the format in `templates/roadmap.md`.

5. Present the milestone plan to the user for approval.

## Epic anti-patterns

| Anti-Pattern | Why It Fails |
|---|---|
| Accepting milestones without measurable success criteria | "Done" becomes subjective |
| Creating milestones too large (>12 tasks) | Exceeds single plan cycle; context loss |
| Creating milestones too small (1-2 tasks) | Overhead exceeds the work itself |
| More than 10 milestones without user approval | Compounding risk; likely needs project split |
| Skipping integration verification milestone | Milestones pass independently but break at boundaries |
