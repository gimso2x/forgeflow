# ForgeFlow Skills Audit Report

Date: 2026-06-09 (refreshed)
Release: v2.0.1 (distribution) / forgeflow skill 1.12.1
Status: **reference only** — not a runtime skill (see `skills/SKILLS.md` U2)

## Summary

13 public skills audited. Distribution is slim markdown-only (prompt + template contract only; no legacy runtime package).

### Frontmatter schemas (current contract)

| Schema | Applies to | Required frontmatter |
|--------|------------|----------------------|
| **Router A** | `forgeflow`, `clarify` | `name`, `description`, `version`, `validate_prompt`, `intent`, `inputs`, `outputs`, `dependencies` |
| **Standard B** | all other public skills | `name`, `description`, `version`, `validate_prompt`, `dependencies` (recommended: `author`) |

`scripts/validate_advisory_contract.py` enforces Router A on `forgeflow` and `clarify`. `make validate-skills` enforces Standard B minimum fields on all public skills.

### Active inventory (2026-06-09)

| Skill | Version | Eval fixtures |
|-------|---------|---------------|
| forgeflow | 1.12.1 | indirect / router |
| clarify | 0.6.0 | yes |
| ff-plan | 0.6.0 | yes |
| execute | 0.7.0 | yes |
| ff-review | 0.6.0 | yes |
| ship | 0.4.0 | yes |
| long-run | 0.5.0 | yes |
| benchmark | 0.3.0 | yes |
| ff-loop | 0.1.0 | yes (prompt + SKILL.md) |
| qa | 0.1.0 | yes |
| unstuck | 0.1.0 | yes |
| status | 0.1.0 | yes |
| ff-config | 0.6.0 | yes |

Total eval cases: **133** (`evals/evals.json`, ids 0..132).

### Known intentional exceptions

- **`status`**: read-only; prints to user, does not write task artifacts (`skills/SKILLS.md` rule #2 exception).
- **CHANGELOG history**: may mention removed adapters (Antigravity, etc.) — not live contract.

### Maintainer follow-ups

See `docs/maintainer-backlog.md` (#158 modularity, #159 standalone review).
