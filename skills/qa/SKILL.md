---
name: qa
description: Lightweight 3-point QA verdict on any ForgeFlow artifact. Quick Completeness, Correctness, Actionability check without full ff-review. Use when the user says /qa, quick check, 가벼운 검증, or needs fast artifact validation.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must produce a 3-point verdict (Completeness, Correctness, Actionability).
  Must not replace ff-review for pipeline stages.
  Must be usable on any markdown artifact.
dependencies:
  - skills/_shared/discipline.md
---

# QA

Lightweight 3-point QA verdict on any ForgeFlow artifact. Quick alternative to full `/forgeflow:ff-review`.

## When to use

- Quick artifact sanity check before proceeding to the next stage
- User asks for a fast validation of brief.md, plan.md, implementation-notes.md, etc.
- ff-loop wants a lightweight gate between stages without full review overhead
- CI/automation pipeline needs artifact quality signal

## When NOT to use

- Pipeline review after execute stage → use `/forgeflow:ff-review`
- Any stage that mandates ff-review per the route contract
- When review-report.md is required as an artifact

## Procedure

1. **Target selection**: Identify the artifact to validate. Default: the most recently modified artifact in `<task-dir>`. User may specify a path.

2. **Read the artifact**: Load the full content.

3. **Score 3 dimensions** (1-5 scale):

   | Dimension | What to check |
   |-----------|---------------|
   | **Completeness** | All required sections present. No empty or placeholder sections. Template fields filled. |
   | **Correctness** | Factual claims match codebase reality. No contradictions within the artifact. Cross-references resolve. |
   | **Actionability** | Next steps are concrete and unambiguous. A third party could act on them without clarification. |

4. **Compute verdict**:
   - Average ≥ 4.0 → `pass`
   - Average 3.0-3.9 → `pass_with_notes`
   - Average < 3.0 → `needs_rework`

5. **Output** (append to `implementation-notes.md` → Evidence section, or print to chat):

   ```
   QA Verdict: <pass|pass_with_notes|needs_rework>
   Completeness: <score>/5 — <one-line note>
   Correctness:  <score>/5 — <one-line note>
   Actionability:<score>/5 — <one-line note>
   Recommendations: <0-3 specific improvement items, or "none">
   ```

6. **For ff-loop integration**: If QA verdict is `needs_rework`, ff-loop should treat it as a soft failure and retry the producing stage.

## Exit Condition

- 3 scores produced with one-line notes
- Verdict computed
- Recommendations listed (or explicitly "none")
- Output recorded or printed

## Constraints

- Read-only — never edits the artifact being validated
- No cross-artifact analysis (unlike ff-review which reads brief+plan+implementation together)
- Maximum 30 seconds of agent time — this is a quick check
- Does not produce review-report.md
- Does not count as a formal review gate in the route contract
