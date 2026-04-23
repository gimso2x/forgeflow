# ForgeFlow Harness V1 Redesign Plan

> **For Hermes:** Use subagent-driven-development only after this redesign backbone is accepted. Do not widen scope during implementation.

**Goal:** Re-anchor ForgeFlow so it keeps the visible workflow shape of `engineering-discipline` while replacing its prose-heavy weak points with machine-readable contracts, recovery state, adapter realism, and calibrated review policy.

**Architecture:** Keep `engineering-discipline` as the visible workflow skeleton and operator UX. Absorb `hoyeon` for artifact/ledger discipline, `gstack` for adapter + memory/eval substrate, and `superpowers` for review posture and anti-rationalization. Do not copy repo branding, plugin packaging, or folder religion from any reference.

**Tech Stack:** Markdown docs, canonical YAML policy, JSON Schema, Python validator/generator/runtime scripts.

---

## One-line judgment

새 harness는 `engineering-discipline`의 **형태**를 유지하고, 그 내부를 `artifact-first state machine`으로 바꿔야 합니다. 
문서 중심 하네스는 보기엔 그럴듯하지만, 오래 가면 드리프트와 자기합리화에 먹힙니다.

---

## What to absorb vs what to reject

### Keep from engineering-discipline
- visible workflow skeleton
- complexity routing
- worker / validator / reviewer separation
- long-run / milestone mindset

### Absorb from hoyeon
- machine-readable plan ledger
- typed verification gates
- bounded recovery semantics
- phase-owned artifacts instead of chat-derived state

### Absorb from gstack
- canonical policy -> generated adapter pipeline
- host adapter registry
- inspectable local checkpoint / memory / eval store
- restore-from-artifacts instead of summary theater

### Absorb from superpowers
- spec-review before quality-review
- adversarial but calibrated review posture
- anti-rationalization rules
- methodology tests for the harness itself

### Reject from all references
- branding-specific folder names
- plugin marketplace as core architecture
- persona zoo
- prompt-only guarantees without schemas/gates
- forced full ceremony on tiny tasks

---

## Target position

ForgeFlow V1 should be:
- **engineering-discipline outside**
- **hoyeon ledger inside**
- **gstack adapter/memory substrate underneath**
- **superpowers review stance at the gates**

That combination is stronger than any one reference repo by itself.

---

## V1 design principles

1. **Chat is never source of truth**
   - Only artifacts, ledgers, and generated state count.
2. **Implementation and judgment must stay separated**
   - No self-approval.
3. **Adapter changes surface, never semantics**
   - Runtime-specific wording may change; stage/gate meaning may not.
4. **Review should be skeptical, not theatrical**
   - Block only on real downstream risk.
5. **Recovery should reload artifacts, not trust summaries**
   - Resume from durable state pointers.
6. **Small work stays light**
   - The harness must not punish trivial tasks with enterprise cosplay.

---

## Proposed V1 backbone

### 1. Workflow model — keep the current visible shape

Canonical stages remain:
1. `clarify`
2. `plan`
3. `execute`
4. `spec-review`
5. `quality-review`
6. `finalize`
7. `long-run`

Canonical routes remain:
- `small` -> `clarify -> execute -> quality-review -> finalize`
- `medium` -> `clarify -> plan -> execute -> quality-review -> finalize`
- `large_high_risk` -> `clarify -> plan -> execute -> spec-review -> quality-review -> finalize -> long-run`

**Decision:** keep this stable. Do not rename stages just because another repo had cooler words.

### 2. Artifact model — tighten ownership

Keep the existing artifact family, but clarify ownership:
- `brief` -> clarify output
- `plan` -> planning intent for humans
- `plan-ledger` -> machine execution truth
- `decision-log` -> append-only execution decisions
- `run-state` -> current route/stage/gate/retry/blocker/evidence state
- `review-report` -> spec or quality review verdict
- `eval-record` -> adherence/eval evidence
- `checkpoint` -> resumable tactical state pointer for long-run work

**Decision:** split human-readable plan from machine ledger everywhere meaningful. Markdown plan is not runtime state.

### 3. Ledger model — absorb hoyeon without copying the repo

Introduce a dedicated execution ledger artifact.

Recommended path:
- `examples/artifacts/plan-ledger.sample.json`
- runtime usage: `<task-dir>/plan-ledger.json`

Minimum schema fields:
- `schema_version`
- `task_id`
- `route`
- `tasks[]`
  - `id`
  - `title`
  - `depends_on[]`
  - `files[]`
  - `parallel_safe`
  - `status`
  - `required_gates[]`
  - `evidence_refs[]`
  - `attempt_count`
  - `blocked_reason`
- `contracts_ref`
- `current_task_id`
- `last_review_verdict`

**Decision:** ledger becomes the runtime execution truth for multi-step work.

### 4. Contracts model — conditional, not mandatory theater

Add a lightweight contracts artifact only when parallelism or interface churn justifies it.

Recommended path:
- `docs/contracts/<slug>.md`

Required only if:
- multiple tasks run in parallel
- public interfaces/types/schemas change
- handoff between components is non-trivial

Contract contents:
- frozen surfaces
- interface invariants
- forbidden churn areas
- handoff guarantees

**Decision:** contracts are optional by default, mandatory only when real collision risk exists.

### 5. Review model — keep hard ordering, improve calibration

Current ordering stays:
- `spec-review` first
- `quality-review` second

But policy should explicitly encode:
- reviewer distrusts implementer claims
- reviewer uses artifacts/evidence, not summaries
- reviewer distinguishes:
  - blocking defects
  - important follow-ups
  - advisory notes
- default is approval when the artifact is actionable and safe enough for the next phase

**Decision:** keep adversarial posture, reject nitpicky theater.

### 6. Verification gate model — typed and inspectable

Add per-task verification gates in ledger/state.

Recommended gate types:
- `machine` -> lint/test/build/static validation
- `validator` -> isolated verification pass
- `scenario` -> e2e or user-flow proof
- `human` -> explicit user/operator signoff

Each gate must name proof:
- exact command
- artifact path
- evidence reference

**Decision:** no generic “verified” vibes. Every gate needs proof.

### 7. Recovery/state model — compact pointers, not transcript worship

Introduce persistent resumable state for long-run sessions.

Recommended surface:
- `runtime/session-state.schema.json`
- local file per run/session under runtime-owned state directory or task dir

Required fields:
- `task_id`
- `route`
- `current_stage`
- `current_task_id`
- `plan_ref`
- `plan_ledger_ref`
- `run_state_ref`
- `latest_checkpoint_ref`
- `next_action`

On resume:
- re-read artifacts
- rehydrate state from files
- do not trust compacted transcript summaries as authority

**Decision:** resume must be artifact reload, not narrative guesswork.

### 8. Adapter model — make realism first-class

Current manifest realism work was correct. Keep going.

Target manifests should continue to own:
- `generated_filename`
- `recommended_location`
- `surface_style`
- `handoff_format`
- `session_persistence`
- `workspace_boundary`
- `review_delivery`

Add next if needed:
- `context_reset_behavior`
- `tool_call_visibility`
- `review_surface_constraints`

**Decision:** manifests stay declarative. Do not bury host behavior in generator code branches unless forced.

### 9. Memory/eval model — gstack-style substrate, local-only bias

Add inspectable local storage for:
- checkpoints
- timeline entries
- durable learnings
- eval results

Recommended structure:
- `memory/checkpoints/`
- `memory/learnings/`
- `memory/timeline/`
- `evals/adherence/`
- `evals/benchmarks/`

Rules:
- checkpoints are tactical and resumable
- learnings are durable and reusable
- evals are benchmark evidence, not status spam

**Decision:** local, inspectable, boring storage wins over magical hidden memory.

---

## Concrete repo-level changes for V1

### P0 — immediate architecture/doc changes
1. Add `docs/harness-v1-principles.md`
2. Add `docs/ledger-model.md`
3. Add `docs/checkpoint-model.md`
4. Update `docs/architecture.md` to name `plan-ledger` explicitly
5. Update `docs/artifact-model.md` to separate plan vs plan-ledger ownership
6. Update `docs/recovery-policy.md` to promote artifact reload over summary replay
7. Update `README.md` to explain the redesign stance in one short section

### P1 — schema/runtime changes
1. Add `schemas/plan-ledger.schema.json`
2. Add `schemas/checkpoint.schema.json`
3. Add sample artifacts for both
4. Extend `validate_sample_artifacts.py`
5. Extend orchestrator to read/write `plan-ledger.json`
6. Add adherence eval fixtures using ledger-aware state
7. Add a session-state pointer artifact for resume flow

### P2 — adapter/eval changes
1. Extend adapter manifests only if a real runtime difference is proven
2. Add methodology evals that check process adherence, not just runtime success
3. Add local memory/eval layout docs and first fixture set

---

## What not to do next

- do not rename everything to match reference repos
- do not add plugin ecosystems
- do not add more stages just to feel sophisticated
- do not build hidden memory magic
- do not make contracts mandatory for tiny tasks
- do not let review devolve into style nit collection

---

## Recommended execution order

### Task 1: Document the redesign invariants
**Objective:** freeze the redesign thesis before code changes widen scope.

**Files:**
- Create: `docs/harness-v1-principles.md`
- Modify: `docs/architecture.md`
- Modify: `README.md`

**Verification:**
- Read the docs and confirm they explicitly state:
  - engineering-discipline form retained
  - plan vs plan-ledger separation
  - spec-review before quality-review
  - artifact reload for resume

### Task 2: Introduce the ledger model
**Objective:** define machine execution truth for multi-step work.

**Files:**
- Create: `docs/ledger-model.md`
- Create: `schemas/plan-ledger.schema.json`
- Create: `examples/artifacts/plan-ledger.sample.json`
- Modify: `docs/artifact-model.md`

**Verification:**
- `python3 scripts/validate_sample_artifacts.py`
- schema validates the positive sample and rejects at least one negative sample

### Task 3: Introduce checkpoint/session-state contracts
**Objective:** make long-run resume reload from artifacts instead of summaries.

**Files:**
- Create: `docs/checkpoint-model.md`
- Create: `schemas/checkpoint.schema.json`
- Create: `examples/artifacts/checkpoint.sample.json`
- Modify: `docs/recovery-policy.md`

**Verification:**
- `python3 scripts/validate_sample_artifacts.py`
- docs consistently distinguish checkpoint vs durable learning

### Task 4: Wire ledger semantics into runtime
**Objective:** make orchestrator/runtime read and update machine state, not just route state.

**Files:**
- Modify: `forgeflow_runtime/orchestrator.py`
- Modify: `scripts/run_orchestrator.py`
- Modify: `tests/test_runtime_orchestrator.py`
- Modify: adherence fixtures under `examples/runtime-fixtures/`

**Verification:**
- `pytest tests/test_runtime_orchestrator.py -q`
- `python3 scripts/run_adherence_evals.py`

### Task 5: Add methodology evals
**Objective:** verify the harness process itself instead of trusting docs.

**Files:**
- Create: `evals/adherence/README.md`
- Create/modify tests for phase-order, review-order, and approval semantics

**Verification:**
- `make validate`
- eval output shows process checks, not just file presence

---

## Final recommendation

**Build V1 as a stricter ForgeFlow, not a Frankenstein merge.**
The right move is:
- keep `engineering-discipline` as the external skeleton
- add `plan-ledger + checkpoint` as the internal truth layer
- keep adapters declarative and generated
- keep review skeptical but calibrated
- make recovery artifact-based

이렇게 가면 새 harness가 됩니다.
반대로 레퍼런스 repo 구조를 섞기 시작하면 또 하나의 잡탕 prompt zoo가 됩니다.
