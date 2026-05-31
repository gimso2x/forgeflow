# Review Role Checklists

These role checklists are loaded by `skills/review/SKILL.md` during role-based review. Keep operator routing and output structure in the main skill; keep detailed per-role assertions here to reduce main-skill surface area.

Checklist version: 2026-05-31

## Evidence requirements by role

Every role must anchor findings in the normalized `brief / evidence / scope / constraints` bundle and must label whether evidence is `observed`, `reported`, or `missing`. Do not let one role's evidence substitute for another role's checklist.

Before starting a role pass, confirm the `normalization gate` in `normalized-input.md` is complete. A role may proceed only when brief, evidence/blocker, scope, constraints, and limitations are explicit; otherwise the role records `blocked: incomplete normalized input` instead of guessing missing provenance.

Before starting a role pass, the lead reviewer must hand the role a compact **role input packet** sourced only from `normalized-input.md`:

- active role name and trigger decision from the Role trigger matrix
- allowed evidence IDs from the role evidence map
- scoped files/ranges/exclusions relevant to that role
- constraints/focus flags and any ignored conflicting flags
- visible limitations/truncation/missing evidence for those evidence IDs

The role-pass record in `review-report.md` must echo that packet by citing the trigger decision, evidence IDs inspected, limitations seen, and any Evidence Escalation Log entry created. If the packet is missing, stale, or relies on chat-only/hidden adapter state, the role records `blocked: missing role input packet` rather than proceeding.

- `spec-reviewer`: cite the exact requirement source (`brief.md`, `plan.md` Design Intent/Review Criteria, user-provided spec, or normalized standalone brief) and the implementation evidence that satisfies or violates it.
- `quality-reviewer`: cite directly observed code, diff hunks, metrics, or verification output. Executor claims from `implementation-notes.md` are reported evidence until independently checked.
- `security-reviewer`: cite the trust boundary, data flow, secret/auth surface, dependency change, or input path under review. If exploitability cannot be confirmed from available evidence, mark confidence and missing evidence explicitly.
- `ux-reviewer`: cite user-facing text, UI state, route/page, form, accessibility attribute, or screenshot-equivalent source when available. Do not infer unseen UI behavior from code names alone.
- `perf-reviewer`: cite the hot path, query/loop/cache boundary, payload size, or benchmark/trace evidence. If no runtime measurement exists, classify the concern as static evidence and record measurement as missing evidence when needed.

## spec-reviewer

Use in addition to the Spec Review rubric.

- ☐ Every acceptance criterion has a corresponding evidence trace
- ☐ No unexplained additions beyond stated scope
- ☐ No silent removals of existing functionality
- ☐ All referenced files/paths/symbols exist in the reviewed scope
- ☐ Error handling is complete (no unchecked error paths for in-scope code)
- ☐ Public API changes are backward-compatible or explicitly breaking
- ☐ Configuration changes have migration path or are additive

## quality-reviewer

Use in addition to the Quality Review rubric.

- ☐ No dead code introduced (unreachable branches, unused imports, commented-out blocks)
- ☐ Naming follows existing codebase conventions (compare with nearby files)
- ☐ No magic numbers/strings — constants are named
- ☐ Error messages are actionable (tell the reader what to do, not just what failed)
- ☐ No copy-pasted blocks that should be shared utilities
- ☐ Logging follows project conventions (level, format, structured fields)
- ☐ Thread safety / concurrency issues in shared state (if applicable)
- ☐ File size: no changed file exceeds the project's documented line limit (default 300 lines for components, 300 for general source files). If oversized, flag as `major: quality / maintainability` with the file name and line count
- ☐ Code intent is clear without reading comments — function/variable names convey purpose
- ☐ Abstraction level is consistent within a file — no mixing of high-level orchestration with low-level implementation details in the same scope
- ☐ Functions are short and focused (≤30 lines recommended); longer functions are justified or split
- ☐ Magic values (numbers, strings) are extracted to named constants or config

## security-reviewer

- ☐ No hardcoded secrets, keys, or tokens
- ☐ User input is validated and sanitized before use
- ☐ SQL queries use parameterized statements (no string interpolation)
- ☐ File paths are sanitized (no path traversal)
- ☐ Error responses don't leak internal state or stack traces
- ☐ New dependencies are from trusted sources with reasonable maintenance
- ☐ Authentication checks are present on all entry points that require them
- ☐ No eval/exec/deserialization of untrusted input

## ux-reviewer

- ☐ Text is clear and follows project voice/guidelines
- ☐ Error states are handled with user-facing messages
- ☐ Loading states exist for async operations
- ☐ Interactive elements have appropriate affordances
- ☐ Layout is consistent with adjacent screens
- ☐ Accessibility: ARIA labels, keyboard navigation, color contrast

## perf-reviewer

- ☐ No N+1 queries in loops
- ☐ Large datasets use pagination or streaming
- ☐ Expensive computations are memoized/cached where appropriate
- ☐ No unnecessary re-renders or re-computations in reactive code
- ☐ Database indexes exist for queried columns
- ☐ No blocking I/O in async contexts
