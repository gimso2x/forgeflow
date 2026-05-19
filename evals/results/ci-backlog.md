# CI 강화 백로그

**Updated:** 2026-05-20 (v1.0.3)  
**Status:** P1–P11 implemented in [`.github/workflows/validate.yml`](../../.github/workflows/validate.yml)

---

## Implemented (v1.0.3)

| ID | Item | Status |
|----|------|--------|
| P1 | Template inventory (10 files incl. ship-summary) | Done |
| P2 | Frontmatter contract (`name`, `description`, `validate_prompt`) | Done |
| P3 | Template cross-reference (`skills/*/SKILL.md`) | Done |
| P4 | Route scoring parity (4 core docs) | Done |
| P5 | Review/ship artifact contract (single `review-report.md`, ship-summary template) | Done |
| P6 | SKILLS.md ↔ skill dirs sync | Done |
| P7 | GEMINI.md @ import existence (11 paths incl. long-run) | Done |
| P8 | Codex defaultPrompt slash completeness | Done (v1.0.3) |
| P9 | evals/evals.json schema validation | Done |
| P10 | Exit Condition lint (workflow skills, forgeflow router excluded) | Done |
| P11 | CHANGELOG release links (`[Unreleased]`, `[VERSION]`) | Done |

---

## Remaining (optional / out of scope)

| Item | Notes |
|------|-------|
| `validate_prompt` semantic enforcement | Requires LLM runtime |
| AI eval CI (iteration-2) | External AI + cost |
| v0.x pytest / windows-smoke | Intentionally removed in v1.0.0 |
| Route table arrow normalization CI | Cosmetic `→` vs `->` only |

---

## CI step summary (validate.yml)

1. No Python files
2. All `skills/*/SKILL.md` exist
3. Plugin JSON valid (5 manifests)
4. Release version consistency (`VERSION` ↔ manifests ↔ CHANGELOG section)
5. Templates exist (10)
6. Skill frontmatter contract
7. Template cross-references
8. Route scoring parity
9. Review/ship artifact contract
10. SKILLS.md inventory sync
11. GEMINI.md imports
12. evals.json schema
13. Exit Condition sections
14. CHANGELOG release links
