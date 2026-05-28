# Review Role Checklists

These role checklists are loaded by `skills/review/SKILL.md` during role-based review. Keep operator routing and output structure in the main skill; keep detailed per-role assertions here to reduce main-skill surface area.

Checklist version: 2026-05-28

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
