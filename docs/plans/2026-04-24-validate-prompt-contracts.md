# Validate Prompt Contracts Implementation Plan

> **For Hermes:** Execute this plan task-by-task with focused validation after each slice.

**Goal:** Add Hoyeon-style `validate_prompt` output contracts to ForgeFlow skills and verify them mechanically.

**Architecture:** Keep validation adapter-neutral. Store `validate_prompt` in skill frontmatter, add a Python validator that checks presence/quality for canonical runtime skills, and include it in `make validate`. Do not wire Claude-only hooks yet.

**Tech Stack:** Markdown frontmatter, Python stdlib, Makefile validation, Claude plugin smoke.

---

## Acceptance Criteria

- Canonical ForgeFlow runtime skills define non-empty `validate_prompt` frontmatter.
- Validator rejects missing, tiny, or malformed `validate_prompt` contracts.
- Validator is included in `make validate`.
- Skill docs still obey exact-output smoke tests.
- `make validate` and `make smoke-claude-plugin` pass.

---

## Task 1: Add validate_prompt validator

**Objective:** Create a mechanical check for skill output contracts.

**Files:**
- Create: `scripts/validate_skill_contracts.py`
- Modify: `Makefile`

**Rules:**
- Check canonical skill files:
  - `skills/clarify/SKILL.md`
  - `skills/specify/SKILL.md`
  - `skills/plan/SKILL.md`
  - `skills/run/SKILL.md`
  - `skills/review/SKILL.md`
  - `skills/ship/SKILL.md`
  - `skills/x-debug.md`
  - `skills/x-deslop.md`
  - `skills/x-qa.md`
  - `skills/x-learn.md`
  - `skills/x-spec-review.md`
  - `skills/x-resume.md`
  - `skills/x-office-hours.md`
  - `skills/x-tdd.md`
- Parse YAML-like frontmatter without external dependencies.
- Require `validate_prompt` to exist, span at least two non-empty lines, and include at least one modal word: `must`, `requires`, `forbid`, `never`, or `only`.
- Include `validate-skill-contracts` in `make validate`.

**Verification:**
```bash
python3 scripts/validate_skill_contracts.py
make validate
```

---

## Task 2: Add contracts to workflow skills

**Objective:** Give core workflow skills explicit output contracts.

**Files:**
- Modify: `skills/clarify/SKILL.md`
- Modify: `skills/specify/SKILL.md`
- Modify: `skills/plan/SKILL.md`
- Modify: `skills/run/SKILL.md`
- Modify: `skills/review/SKILL.md`
- Modify: `skills/ship/SKILL.md`

**Contract shape:**
```yaml
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must produce/describe the declared output artifact when file writing is explicitly allowed.
  Must not write outside the explicit task directory or current project workspace.
```

**Verification:**
```bash
make validate
make smoke-claude-plugin
```

---

## Task 3: Add contracts to cross-cutting skills

**Objective:** Give cross-cutting skills explicit output contracts without broadening command surface.

**Files:**
- Modify: `skills/x-debug.md`
- Modify: `skills/x-deslop.md`
- Modify: `skills/x-qa.md`
- Modify: `skills/x-learn.md`
- Modify: `skills/x-spec-review.md`
- Modify: `skills/x-resume.md`
- Modify: `skills/x-office-hours.md`
- Modify: `skills/x-tdd.md`

**Verification:**
```bash
make validate
make smoke-claude-plugin
```

---

## Task 4: Final verification and commit series

**Objective:** Prove the contracts are stable with the existing plugin smoke.

**Steps:**
1. Run `make validate`.
2. Run `make smoke-claude-plugin`.
3. Confirm `git status --short` is clean after commit.
