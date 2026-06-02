# ForgeFlow Skills Audit Report

Date: 2026-06-02
Release: v1.11.1
Auditor: skill-creator

## Summary

9 skills audited. Found **3 critical**, **5 moderate**, **2 minor** issues.

## 1. Version Consistency

| Skill | Version | Note |
|-------|---------|------|
| clarify | 0.6.0 | |
| execute | 0.7.0 | highest |
| ship | 0.4.0 | |
| ff-plan | 0.6.0 | |
| ff-review | 0.5.0 | |
| long-run | 0.5.0 | |
| forgeflow | 0.3.0 | lowest — entry point, rarely changed |
| benchmark | 0.3.0 | |
| ff-config | 0.6.0 | |

**Verdict**: Skill schema versions are independent from release VERSION. This is by design (documented in SKILL.md Conventions). No action needed, but version spread (0.3.0–0.7.0) suggests some skills haven't been updated since early iterations.

## 2. Frontmatter Schema Inconsistency — 🔴 Critical

Two different schemas coexist:

**Schema A** (clarify, forgeflow):
```yaml
intent: "..."
inputs: [...]
outputs: [...]
```

**Schema B** (execute, ship, ff-plan, ff-review, long-run, benchmark, ff-config):
```yaml
validate_prompt: |
  ...
dependencies: [...]
```

**Problem**: `clarify` and `forgeflow` lack `validate_prompt` — the field that gates whether the skill executed correctly. `forgeflow` also uses `intent`/`inputs`/`outputs` which no other skill uses.

**Fix**: Add `validate_prompt` to `clarify` and `forgeflow`. Remove unused `intent`/`inputs`/`outputs` from `forgeflow` (or migrate all skills to a unified schema — bigger effort).

## 3. Dependencies Inconsistency — 🔴 Critical

All skills heavily reference `skills/_shared/` files, but dependency declarations are incomplete:

| Skill | Declared | Actual _shared Refs | Missing |
|-------|----------|-------------------|---------|
| clarify | (none) | 8 | `discipline.md`, `context-resume.md`, `isolation.md` |
| execute | `preflight.md` | 10 | `discipline.md`, `isolation.md`, `automation.md` |
| ship | (none) | 7 | `discipline.md`, `isolation.md`, `context-resume.md` |
| ff-plan | `isolation.md` | 7 | `discipline.md`, `context-resume.md` |
| ff-review | (none) | 14 | `discipline.md`, `isolation.md`, `preflight.md`, `context-resume.md` |
| long-run | `discipline.md`, `isolation.md` | 3 | OK (or over-declared) |
| forgeflow | (none) | 6 | `discipline.md`, `automation.md`, `context-resume.md` |
| benchmark | `discipline.md`, `isolation.md` | 3 | OK |
| ff-config | `automation.md`, `isolation.md` | 5 | OK |

**Problem**: Dependencies field is advisory (no runtime enforcement), but inconsistency makes it hard to track what each skill actually needs. `ff-review` has 14 _shared refs but declares zero dependencies.

**Fix**: Either:
- (A) Update all skills to declare their actual _shared dependencies
- (B) Remove the `dependencies` field entirely and rely on inline `→ _shared/xxx.md` pointers (already used)

Recommend **(A)** — dependencies serve as documentation even without runtime enforcement.

## 4. validate_prompt vs Actual Procedure — 🟡 Moderate

### 4a. clarify — No validate_prompt

Missing entirely. Should cover:
- Must produce `brief.md` with route selection
- Must bootstrap task workspace if missing
- Must include scope boundary and acceptance criteria

### 4b. forgeflow — No validate_prompt

Missing entirely. Should cover:
- Must route to correct stage skill
- Must read project defaults when present
- Must handle template resolution correctly

### 4c. ship — validate_prompt mentions "four safe outcomes"

```
Must present exactly four safe outcomes: merge locally, push and create PR, keep branch, or discard work.
```

Actual SKILL.md also has `--cleanup-only` mode and worktree-specific handling. The "exactly four" constraint may be too rigid.

### 4d. ff-plan — validate_prompt is thin

Covers artifact-first and epic roadmap, but misses:
- Contract-first traceability for medium/high/epic
- Plan-mode adaptation guardrails
- Refactor mode requirement traceability

### 4e. ff-review — validate_prompt is thin

Covers role separation and blocker gate, but misses:
- Standalone mode input detection
- Synthetic task directory bootstrapping
- Artifact completeness gate
- Evidence discipline

## 5. Description Trigger Optimization — 🟡 Moderate

### Good triggers (already solid):
- **clarify**: "first for new implementation/refactor/debug requests" — strong contextual trigger
- **execute**: "asks to implement after clarify/plan" — good chain awareness
- **ff-config**: "Toggle auto-chaining and worktree isolation" — specific capability

### Weak triggers:
- **forgeflow**: Too generic — "Artifact-first delivery workflow" doesn't differentiate from general coding. Should emphasize "when user wants structured multi-stage workflow" or "when user mentions clarify/plan/execute/review/ship stages"
- **benchmark**: "cross-adapter benchmark tests" — niche, only triggers on explicit `/benchmark`. Could add "compare Claude vs Codex vs Cursor" type triggers
- **long-run**: "Record reusable learnings" — passive. Should trigger on "extract patterns", "what did we learn", "evolution rules"
- **ff-review**: "Perform independent ForgeFlow review" — could add "audit code changes", "review PR", "check implementation against plan"

## 6. Missing validate_prompt Fields — 🔴 Critical

`clarify` and `forgeflow` are the **entry points** of the entire workflow — they are the most important skills to validate. Yet they have no `validate_prompt`.

**Recommended validate_prompt for clarify:**
```yaml
validate_prompt: |
  Must produce brief.md with route selection, scope boundary, and acceptance criteria.
  Must bootstrap task workspace (<task-dir>/) if missing.
  Must include WHERE grounding for non-trivial work.
  Must detect tech stack and auto-detect verification gates.
  Must not skip scope boundary definition or route rationale.
```

**Recommended validate_prompt for forgeflow:**
```yaml
validate_prompt: |
  Must route to correct stage skill based on user input.
  Must read <storage-root>/defaults.md when present for auto/isolation settings.
  Must resolve template root before reading any template.
  Must not invent artifact structure when templates are missing.
```

## 7. Minor Issues

### 7a. forgeflow SKILL.md has orphaned JSON block

```
# Benchmark
{
}
```

In `skills/benchmark/SKILL.md` — empty JSON block after the heading, likely leftover from template.

### 7b. _shared files not versioned

`_shared/` files have no version tracking. Changes to `discipline.md` or `automation.md` affect all skills silently.

## Recommendations (Priority Order)

1. **Add `validate_prompt` to `clarify` and `forgeflow`** — highest impact, lowest effort
2. **Unify frontmatter schema** — decide on Schema A or B, migrate all skills
3. **Update `dependencies` declarations** to match actual _shared usage
4. **Strengthen weak descriptions** for forgeflow, benchmark, long-run, ff-review
5. **Expand thin validate_prompts** for ff-plan and ff-review
6. **Clean up benchmark orphaned JSON block**
