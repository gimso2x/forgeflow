# Engineering Discipline → ForgeFlow Absorption Execution Plan

> **For Hermes:** Keep ForgeFlow as the workflow skeleton. Absorb operating ideas, not folder religion. Execute in order: P0 first, then P1, then P2. Do not widen scope mid-flight.

**Goal:** Improve ForgeFlow's operator clarity and onboarding by absorbing the best human-facing ideas from `tmdgusya/engineering-discipline` while preserving ForgeFlow's stronger artifact/runtime validation model.

**Architecture:** Treat `engineering-discipline` as a reference for operator UX, review explanation, and milestone storytelling. Treat ForgeFlow as the canonical runtime and schema truth. The work here is documentation and operator-surface hardening first — not a runtime rewrite.

**Tech Stack:** Markdown docs, README/help text, Python CLI help surface, existing ForgeFlow tests.

---

## One-line judgment

`engineering-discipline` is better at **explaining disciplined work to humans**. `forgeflow` is better at **enforcing disciplined work through artifacts, runtime state, and validation**. We should import the first strength into the second system.

---

## Comparison summary

### What Engineering Discipline does better
1. Clear request-to-execution storytelling
2. Strong hard-gate language in skills
3. Very readable explanation of information-isolated review
4. Better long-run / milestone operator narrative
5. More approachable install and usage framing

### What ForgeFlow already does better
1. Real runtime state machine
2. Real schema-backed artifacts
3. Mechanical route/gate enforcement
4. Checkpoint/session-state/recovery substrate
5. CI + fixtures + negative validation

### What must not be copied
- skill-pack-centric architecture
- plugin marketplace structure as system design
- markdown-only state truth
- trigger-phrase magic as the primary workflow contract
- generic review language that weakens `spec-review -> quality-review`

---

## Phase plan

### P0 — High value, low risk, immediate
Make ForgeFlow easier to understand and operate without changing its core semantics.

### P1 — Stronger operator docs and discipline language
Add sharper explanation and stage-level rule surfaces.

### P2 — Long-run operator model hardening
Document milestone/checkpoint behavior more clearly and tighten optional operator surfaces.

---

# P0 Tasks

## P0-1: Add a request-journey overview to README

**Objective:** Let a first-time reader understand the whole ForgeFlow flow in under one minute.

**Files:**
- Modify: `README.md`
- Modify: `docs/workflow.md`

**Output Artifacts:**
- updated `README.md`
- updated `docs/workflow.md`

**Task details:**
1. Add a compact “request journey” section near the top of `README.md`
2. Show the operator journey from request → `clarify` → route selection → execution/review/finalize
3. Explicitly separate:
   - canonical `clarify-first`
   - direct CLI fallback
4. Mirror the same explanation in `docs/workflow.md`
5. Keep route names and stage names exactly aligned with canonical policy

**Why this is P0:**
This is the cheapest possible clarity win.

**Verification:**
- Read `README.md` and confirm a newcomer can see the flow without opening policy files
- Run: `pytest -q tests/test_runtime_orchestrator.py`

**Exit Condition:**
ForgeFlow's top-level docs explain the lifecycle cleanly without inventing new concepts.

---

## P0-2: Add a dedicated review-isolation explainer

**Objective:** Explain, in plain language, why worker self-report is not approval evidence.

**Files:**
- Create: `docs/review-model.md`
- Modify: `README.md`

**Output Artifacts:**
- new `docs/review-model.md`
- README link to the review model doc

**Task details:**
1. Write a standalone review model doc with these sections:
   - why review exists
   - what `spec-review` checks
   - what `quality-review` checks
   - what reviewers may trust
   - what reviewers must not trust
2. Make it explicit that execution logs and worker self-report are not sufficient approval basis
3. Preserve ForgeFlow's current structured review semantics; do not replace them with a generic PASS/FAIL-only model
4. Link the new doc from `README.md`

**Why this is P0:**
This is one of Engineering Discipline's clearest strengths and ForgeFlow can absorb it without touching runtime code.

**Verification:**
- Review `docs/review-model.md` for consistency with `docs/workflow.md`
- Run: `make validate`

**Exit Condition:**
ForgeFlow has an explicit review model document that matches current policy/runtime semantics.

---

## P0-3: Tighten operator shell examples

**Objective:** Make the CLI usage story feel intentional instead of half-discovered.

**Files:**
- Modify: `README.md`
- Modify: `scripts/run_orchestrator.py`

**Output Artifacts:**
- updated runtime sample section in README
- improved CLI `--help` copy

**Task details:**
1. Group README examples by operator intent:
   - start a new task
   - run current route
   - inspect state
   - resume/recover
2. Keep the “clarify-first is canonical” rule visible
3. Keep direct CLI auto-route clearly labeled as fallback
4. Ensure `scripts/run_orchestrator.py --help` and subcommand help use the same hierarchy language

**Why this is P0:**
The runtime exists already. The shell story just needs to stop sounding accidental.

**Verification:**
- Run: `make orchestrator-help`
- Run: `pytest -q tests/test_runtime_orchestrator.py`

**Exit Condition:**
README examples and CLI help tell the same operator story.

---

# P1 Tasks

## P1-1: Add harder stage-level non-negotiables to docs

**Objective:** Turn existing semantics into sharper operator-facing rules.

**Files:**
- Modify: `docs/workflow.md`
- Modify: `README.md`
- Optionally modify later prompt source docs under `prompts/canonical/`

**Output Artifacts:**
- strengthened stage docs

**Task details:**
1. For `clarify`, `execute`, `spec-review`, `quality-review`, `finalize`, add 2-5 blunt rules each
2. Make sure every rule maps back to existing policy/runtime behavior
3. Do not add fake constraints that the runtime cannot support

**Why this is P1:**
Useful, but less urgent than onboarding and review clarity.

**Verification:**
- Read through `docs/workflow.md` and compare rule language to actual runtime behavior
- Run: `make validate`

**Exit Condition:**
Stage docs are more forceful without becoming fiction.

---

## P1-2: Add an operator-shell guide

**Objective:** Pull procedural operator guidance out of README once README starts bloating.

**Files:**
- Create: `docs/operator-shell.md`
- Modify: `README.md`

**Output Artifacts:**
- new operator guide doc
- README link to it

**Task details:**
1. Write an operator guide covering:
   - clarify-first normal path
   - fallback direct CLI path
   - start/run/status/resume/advance/retry/step-back/escalate at a high level
2. Keep the guide descriptive and repo-accurate
3. Do not claim commands or outputs that don't exist

**Why this is P1:**
Great for usability, but only after README and review docs are cleaned up.

**Verification:**
- Check every documented command against `scripts/run_orchestrator.py --help`
- Run: `pytest -q tests/test_runtime_orchestrator.py`

**Exit Condition:**
ForgeFlow has a single place for operator usage without overloading README.

---

# P2 Tasks

## P2-1: Add a long-run operator model doc

**Objective:** Explain milestone/checkpoint/recovery behavior in human terms.

**Files:**
- Create: `docs/long-run-model.md`
- Modify: `README.md`
- Modify: `docs/recovery-policy.md` (if present and still thin)

**Output Artifacts:**
- new `docs/long-run-model.md`
- linked recovery/long-run docs

**Task details:**
1. Explain what `long-run` is for
2. Explain when a task should escalate into milestone-oriented work
3. Explain what gets persisted (`checkpoint`, `session-state`, related review refs)
4. Explain how resume should work at a conceptual level
5. Keep this doc aligned with ForgeFlow's artifact-first truth sources; do not replace them with markdown checkpoint truth

**Why this is P2:**
Important, but lower priority than the top-level readability and review model fixes.

**Verification:**
- Read doc against current runtime/recovery semantics
- Run: `make validate`

**Exit Condition:**
A reader can understand long-run semantics without reverse-engineering the runtime.

---

## P2-2: Evaluate whether `review-summary` deserves a first-class command

**Objective:** Decide whether operator review surfaces need one more CLI affordance.

**Files:**
- Inspect: `scripts/run_orchestrator.py`
- Inspect: `forgeflow_runtime/orchestrator.py`
- Potentially create follow-up plan, not immediate implementation

**Output Artifacts:**
- decision note in docs or follow-up plan

**Task details:**
1. Check whether current `status` + review artifacts already cover operator needs
2. If not, define what a `review-summary` command would output
3. Do not implement blindly in this phase unless the value is obvious and low-risk

**Why this is P2:**
This is convenience, not core clarity.

**Verification:**
- N/A for now; decision quality matters more than rushing implementation

**Exit Condition:**
We have either a justified follow-up plan or a justified “not needed yet” decision.

---

## Recommended execution order

1. `P0-1`
2. `P0-2`
3. `P0-3`
4. `P1-1`
5. `P1-2`
6. `P2-1`
7. `P2-2`

---

## Practical rule for the next implementation session

Do not try to “absorb engineering-discipline” in one giant pass.
That would be stupid.
Treat this as a sequence of small ForgeFlow-native hardening steps.

---

## Success metric

ForgeFlow should still be the more serious runtime harness — it just shouldn't require repo archaeology to understand why it's good.
