# x-learn Compound Implementation Plan

> **For Hermes:** Execute this plan task-by-task. Keep learning capture local, structured, and evidence-based.

**Goal:** Strengthen ForgeFlow `x-learn` with Hoyeon-style compound learning: extract durable lessons from artifacts, classify them, de-duplicate them, and append JSONL records safely.

**Architecture:** Add a small Python CLI (`scripts/forgeflow_learn.py`) that reads task artifacts and writes `memory/learnings.jsonl`. Keep `x-learn` as the user-facing skill contract. Do not add a new slash command.

**Tech Stack:** Python stdlib, JSONL, markdown docs, pytest, Makefile validation.

---

## Acceptance Criteria

- `scripts/forgeflow_learn.py` supports `extract <task_dir> --output <jsonl>` and `validate <jsonl>`.
- Learning entries require `id`, `timestamp`, `source`, `type`, `problem`, `cause`, `rule`, `evidence`, and `tags`.
- Temporary task progress, secrets, raw dumps, and duplicate learnings are rejected or skipped.
- `skills/x-learn.md` documents PR/comment/artifact synthesis and duplicate checks.
- `make validate` passes.

---

## Task 1: Add learning CLI tests first

**Objective:** Lock expected behavior before implementation.

**Files:**
- Create: `tests/test_forgeflow_learn.py`

**Test cases:**
1. Extracts a learning from `decision-log.json` + `review-report.json` into JSONL.
2. Skips duplicate rule/evidence combinations.
3. Rejects entries with secret-looking evidence.
4. Validates existing JSONL successfully.

**Verification:**
```bash
pytest tests/test_forgeflow_learn.py -q
```
Expected first run: fails because `scripts/forgeflow_learn.py` does not exist.

---

## Task 2: Implement `scripts/forgeflow_learn.py`

**Objective:** Provide a minimal, deterministic learning extractor.

**Files:**
- Create: `scripts/forgeflow_learn.py`

**Commands:**
```bash
python3 scripts/forgeflow_learn.py extract <task_dir> --output memory/learnings.jsonl
python3 scripts/forgeflow_learn.py validate memory/learnings.jsonl
```

**Rules:**
- Read `decision-log.json`, `review-report.json`, and `eval-record.json` if present.
- Extract only records that can produce a concrete future-facing `rule`.
- Use stable ID from SHA-256 of `type|problem|cause|rule|evidence`.
- Skip duplicate IDs already present in output.
- Block evidence containing obvious secret markers: `api_key`, `token=`, `password=`, `BEGIN PRIVATE KEY`.

**Verification:**
```bash
pytest tests/test_forgeflow_learn.py -q
```

---

## Task 3: Add smoke target and docs

**Objective:** Make compound learning part of regular validation and update the skill contract.

**Files:**
- Modify: `Makefile`
- Modify: `skills/x-learn.md`

**Changes:**
- Add `learn-smoke` target running `pytest tests/test_forgeflow_learn.py -q`.
- Include it in `make validate`.
- Update `x-learn` with:
  - input sources: decision-log, review-report, eval-record, PR comments when provided
  - problem type taxonomy
  - duplicate check
  - secret/raw dump filters
  - JSONL schema

**Verification:**
```bash
make validate
make smoke-claude-plugin
```

---

## Task 4: Final verification

**Objective:** Prove the new learning layer does not destabilize existing flows.

**Steps:**
1. Run `make validate`.
2. Run `make smoke-claude-plugin`.
3. Commit changes.
