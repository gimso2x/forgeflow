# Engineering Discipline Remaining Absorption Task Plan

> **For Hermes:** Apply this sequentially. Do not copy the source repo's folder religion. Absorb only ForgeFlow-native, testable operating patterns.

**Goal:** Finish the useful remaining absorption from `tmdgusya/engineering-discipline` into ForgeFlow without bloating the runtime or duplicating plugin surfaces.

**Architecture:** Keep ForgeFlow's schema/runtime/artifact model as the source of truth. Translate reference skills into cross-cutting ForgeFlow docs/skills only where they improve operator behavior or regression resistance.

**Tech Stack:** Markdown docs/skills, existing ForgeFlow validation scripts, optional Claude plugin smoke test.

---

## Source inventory snapshot

External repo inspected: `https://github.com/tmdgusya/engineering-discipline`

Useful remaining source assets:

- `skills/systematic-debugging/root-cause-tracing.md`
- `skills/systematic-debugging/condition-based-waiting.md`
- `skills/systematic-debugging/condition-based-waiting-example.ts`
- `skills/systematic-debugging/defense-in-depth.md`
- `skills/systematic-debugging/find-polluter.sh`
- `skills/milestone-planning/SKILL.md`
- `skills/karpathy/SKILL.md`
- `skills/rob-pike/SKILL.md`
- `skills/simplify/SKILL.md`

Already absorbed enough:

- clarification → `/forgeflow:clarify`
- plan-crafting → `/forgeflow:plan`
- run-plan → `/forgeflow:run`
- review-work → `/forgeflow:review` + review model docs
- long-run → `docs/long-run-model.md` + checkpoint/session state docs
- clean-ai-slop → `skills/x-deslop.md`

Do not copy:

- generated website HTML/CSS
- source repo plugin manifests as architecture
- Claude-only command names as ForgeFlow canonical names

---

## Task 1: Import debugging references as ForgeFlow-native docs

**Objective:** Preserve the concrete debugging techniques from `systematic-debugging` without bloating `x-debug.md`.

**Files:**

- Create: `docs/debugging/root-cause-tracing.md`
- Create: `docs/debugging/condition-based-waiting.md`
- Create: `docs/debugging/condition-based-waiting-example.ts`
- Create: `docs/debugging/defense-in-depth.md`
- Create: `docs/debugging/find-polluter.sh`
- Modify: `skills/x-debug.md`
- Modify: `README.md` or `skills/SKILLS.md` if a user-facing link is needed

**Steps:**

1. Copy the five reference files from `engineering-discipline/skills/systematic-debugging/` into `docs/debugging/`.
2. Add a short ForgeFlow note at the top of each copied markdown file: these are debugging references, not artifact contracts.
3. Update `skills/x-debug.md` with a `Reference Playbooks` section linking to the docs.
4. Keep `x-debug.md` concise; do not paste all reference content into the skill.
5. Run `make validate`.
6. Commit: `docs: add debugging reference playbooks`.

**Exit Condition:** `x-debug` points to concrete debugging playbooks and ForgeFlow validation stays green.

---

## Task 2: Add root-cause tracing to x-debug's mandatory flow

**Objective:** Make the most important debugging behavior explicit: trace from symptom to original trigger before fixing.

**Files:**

- Modify: `skills/x-debug.md`

**Steps:**

1. Add a constraint: "Do not fix at the symptom site until the original trigger has been traced or explicitly ruled out."
2. Add an execution step between `REPRODUCE` and `HYPOTHESIZE`: `TRACE SOURCE`.
3. Include allowed techniques: stack trace instrumentation, call-chain walk, input provenance, test bisection via `find-polluter.sh`.
4. Run `make validate`.
5. Commit: `docs: tighten x-debug root-cause tracing`.

**Exit Condition:** `x-debug` encodes root-cause tracing as a gate, not an optional tip.

---

## Task 3: Evaluate milestone-planning absorption for large/high-risk plans

**Objective:** Decide whether Engineering Discipline's 5-reviewer/ultraplan pattern should become a ForgeFlow large-route planning rule.

**Files:**

- Create: `docs/milestone-planning-decision.md`
- Potentially modify: `skills/plan/SKILL.md`
- Potentially modify: `docs/long-run-model.md`

**Steps:**

1. Read `engineering-discipline/skills/milestone-planning/SKILL.md` completely.
2. Compare it to ForgeFlow's current `large_high_risk` route and `plan-ledger` model.
3. Write a decision doc with one of:
   - adopt now,
   - adopt later,
   - reject.
4. If adopting now, add only a small planning rule: large/high-risk plans should include risk/dependency/test/operator review notes before execution.
5. Run `make validate`.
6. Commit: `docs: decide milestone planning absorption`.

**Exit Condition:** The ultraplan idea is either captured as a ForgeFlow-native follow-up or explicitly rejected with reasons.

---

## Task 4: Mine Karpathy/Rob Pike as review checklist language only

**Objective:** Absorb useful discipline from `karpathy` and `rob-pike` without adding another ceremonial stage.

**Files:**

- Inspect: `engineering-discipline/skills/karpathy/SKILL.md`
- Inspect: `engineering-discipline/skills/rob-pike/SKILL.md`
- Modify if valuable: `skills/review/SKILL.md`
- Modify if valuable: `docs/review-model.md`

**Steps:**

1. Extract only durable review questions:
   - smallest safe change?
   - existing pattern read first?
   - assumptions verified?
   - performance change measured before optimized?
2. Add them as optional quality-review checklist bullets if they do not duplicate existing checks.
3. Do not create `/karpathy` or `/rob-pike` commands.
4. Run `make validate` and, if plugin behavior changed, `make smoke-claude-plugin`.
5. Commit: `docs: fold discipline heuristics into review checklist`.

**Exit Condition:** Review guidance improves without increasing command/stage sprawl.

---

## Task 5: Decide whether simplify deserves a ForgeFlow surface

**Objective:** Avoid blindly importing `simplify`'s 3-agent review workflow; decide based on overlap with `/review`, `x-deslop`, and `x-qa`.

**Files:**

- Inspect: `engineering-discipline/skills/simplify/SKILL.md`
- Create: `docs/simplify-surface-decision.md` if the decision is non-trivial
- Potentially modify: `skills/x-deslop.md` or `skills/review/SKILL.md`

**Steps:**

1. Compare `simplify` against current ForgeFlow review/deslop surfaces.
2. If there is a gap, absorb the smallest checklist item only.
3. If there is no gap, document rejection in one short decision note.
4. Run `make validate`.
5. Commit only if files changed.

**Exit Condition:** No duplicate `simplify` command exists unless it has a distinct ForgeFlow-native purpose.

---

## Recommended execution order

1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 5

## Stop rule

After each task, run validation and commit before moving on. If a task starts requiring runtime changes, stop and write a narrower implementation plan before editing runtime code.
