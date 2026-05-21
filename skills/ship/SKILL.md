---
name: ship
description: "Finalize ForgeFlow work after review: summarize, verify, prepare PR/commit handoff, preserve evidence, and extract evolution rules. Use when the user types /ship or /forgeflow:ship."
version: 0.3.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must confirm review approval, intended diff scope, and final verification before shipping.
  Must not hide residual risks or unrelated dirty working tree changes.
---

# Ship

Use this skill to prepare the final handoff after review passes and extract reusable evolution rules.

`ship` does not merge, discard, clean up, or decide branch disposition. Use `finish` for branch disposition after the user gives explicit direction.

## Input

- Approved `review-report.md` or equivalent review verdict
- `brief.md` if available
- `plan.md` if available
- `implementation-notes.md` if available
- `eval-record.md` if available (from long-run, high/epic routes)
- Git diff/status
- Verification evidence

## Output Artifacts

Write a `ship-summary.md` in the active task directory using `templates/ship-summary.md` as the structure. The summary must capture:

- Changed files
- Verification commands and results
- Review verdict
- Residual risks
- Handoff action: report completed; branch disposition remains pending for `finish`
- Quantitative summary (from execute metrics)

Evolution rule artifacts (optional, when reusable patterns are found):

- `~/.forgeflow/evolution/active/<rule-name>.md` for global-advisory scope
- `.forgeflow/evolution/active/<rule-name>.md` for project scope

## Exit Condition

- Working tree state is understood
- Final verification is green or failures are explicitly documented
- Review verdict permits shipping
- Final handoff is completed
- User gets a concise final report

## Constraints

## File write and output discipline

→ Core rules: `_shared/discipline.md`.

Follow the user language rules there: write user-facing replies and artifact prose in the user's primary language, while preserving canonical English labels, commands, paths, artifact filenames, and enum values.

Ship should preserve the final handoff evidence in the active task directory.

When artifacts such as `review-report.md` or final handoff notes are mentioned without an explicit path, preserve them under the active task directory, not the repository root and not chat-only fallback.

## Strict response constraints

→ `_shared/discipline.md`.

Bad: adding verdicts, extra rationale sections, or warnings after the requested list.
Good: if asked for exactly two checks, return exactly two checks.

Example exact-count response must be plain text lines, not a fenced block:

1. Confirm the approved README badge change is the only intended ship item.
2. Confirm the final handoff summary names the badge change and any residual risk.

No heading. No preamble. No code fence. No third line.

## Status analysis preflight

→ `_shared/preflight.md`.

## Evolution rule extraction

Ship is the evolution rule generation point for **all routes** (small, medium, high, epic). This ensures every completed task can produce reusable rules, not just high/epic.

### Rule lifecycle

```
observe (ship) → propose (ship) → activate (ship) → retire (ship or manual)
```

Ship consolidates the propose→validate→activate cycle because review has already validated the work. Evolution rules generated here are evidence-backed by the review-approved task artifacts.

### Scope decision

- **Global-advisory** (default): Rules applicable across projects. Written to `~/.forgeflow/evolution/active/<rule-name>.md`. Advisory only — cannot hard-block future tasks.
- **Project**: Rules specific to this repository's architecture/conventions. Written to `.forgeflow/evolution/active/<rule-name>.md`. Required constraints for this project.

Use project scope only when the rule depends on project-specific architecture (e.g., auth store structure, routing conventions). Default to global.

### Route-aware extraction

- **small**: Skip evolution rule extraction entirely. The change is too small to produce durable patterns.
- **medium**: Extract only if an obvious, high-confidence pattern emerges. Maximum 1-2 rules.
- **high/epic**: Full extraction. No hard limit, but prefer quality over quantity.

### Capture criteria

Extract an evolution rule when:

1. The pattern has concrete evidence from task artifacts (implementation-notes, review-report, eval-record, code diff).
2. It describes a trigger condition and expected behavior, not a vague sentiment.
3. It is not already covered by an existing active rule (check `~/.forgeflow/evolution/active/` and `.forgeflow/evolution/active/`).
4. It will actually save time or prevent mistakes in future tasks.

Do not capture:

- Task status, session chatter, or one-off observations
- Patterns so obvious they don't need enforcement
- Rules without evidence

### Anti-patterns

| Anti-Pattern | Why It Fails |
|---|---|
| Proposing rules without evidence | Rules without grounding become cargo cult |
| Auto-generating trivial rules | Noise drowns signal |
| Retiring rules silently | Lost history makes the same mistake recur |

## Procedure

1. Check git status and diff only if command execution is allowed.
2. Run final verification only if command execution is allowed.
3. Ensure review passed; do not ship blocked work.
4. Confirm there is no unresolved blocker, and that handoff evidence is preserved in the active task directory before preparing the final summary.

5. **Artifact completeness gate**: Before writing final handoff language, inspect `review-report.md`, `implementation-notes.md`, and the draft/final `ship-summary.md` for unresolved template residue. If `TODO`, `TBD`, `FIXME`, unresolved `<!-- ... -->`, or angle-bracket placeholders such as `<task-id>`, `<branch-name>`, or `<...>` remain as artifact-writing residue, stop and route back to `/forgeflow:execute` or `/forgeflow:review`. Do not preserve unfinished placeholders as ship evidence. Intentional Markdown checkboxes, code snippets, command output, or literal examples are not blockers by themselves.

6. **Final Polish and Simplification Loop**: Analyze the **actually changed code** (`git diff HEAD~1 HEAD` or equivalent) for quality before shipping. This is a read-first analysis: if modifications are needed, hand back to execute rather than editing code during ship.

#### Analysis (read-only)

- **Phase 1: Identification**: Focus exclusively on the diff. Ignore noise from unrelated files.
- **Phase 2: Triple-Lens Analysis**:
    - **Lens 1 (Code Reuse)**: Identify new logic that duplicates existing utils, constants, or types.
    - **Lens 2 (Code Quality)**: Identify stringly-typed code, redundant wrappers, and abstraction boundary violations.
    - **Lens 3 (Efficiency)**: Identify hot-path inefficiencies, missed concurrency, and redundant resource reads.

#### If issues found

If the Triple-Lens analysis identifies meaningful improvements:
- Record each finding in `ship-summary.md` under a "Simplification candidates" section.
- **Always ask the user** (auto-break, even under `--auto`): "품질 개선 후보가 발견되었습니다. `/forgeflow:execute`로 돌아가 수정하시겠습니까? (y/n)"
- Do NOT modify code during ship. Ship is verification + handoff, not implementation.

#### If no issues found

Proceed to the final summary step directly.
If `--auto` is active (see `_shared/automation.md`), invoke `/forgeflow:finish` after writing `ship-summary.md`.

7. **Extract evolution rules**: Review task artifacts for reusable patterns. For each valid candidate:
   1. Check existing active rules (`~/.forgeflow/evolution/active/` and `.forgeflow/evolution/active/`) for duplicates.
   2. Determine scope: global-advisory (default) or project (project-specific architecture only).
   3. Write the rule in **compact format** (6 lines, no `.md` extension) directly to the matching `active/` directory:
      ```
      # <rule-id>
      <one-line summary>
      Trigger: <when to apply>
      Stage: <clarify | plan | execute | review | multiple>
      Mode: <advisory | required_project_rule>
      Apply: <what to do when trigger matches>
      Skip: <when NOT to apply>
      ```
   4. Global → `~/.forgeflow/evolution/active/<rule-name>`, Project → `.forgeflow/evolution/active/<rule-name>`. Create directories if they do not exist.
   5. Report what rules were created and why.

8. Write `ship-summary.md` to the active task directory. Include the Quantitative Summary section with metrics from `implementation-notes.md` → Metrics.
9. Preserve artifacts/evidence instead of burying them in chat.

Never discard, merge, PR, or destructive-clean from `ship`; hand branch disposition to `finish` and require explicit confirmation there.

## Output mode examples

If asked:

```text
/forgeflow:ship Dry run only. List exactly two ship checks. Do not write files. Do not run commands.
```

Return exactly two ship checks. Do not add command equivalents, git actions, artifact writes, or a final verdict unless requested.
