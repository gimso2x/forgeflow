# Review Role Routing

Use this reference from `skills/ff-review/SKILL.md` before selecting reviewer roles, assigning role/model hints, applying specialist profiles, handling cross-role conflicts, or writing role-pass records.

## Role definitions

Role-specific triggers decide which passes run. Detailed checklist items and role-specific evidence requirements live in `skills/ff-review/references/role-checklists.md`; load that reference before executing any role pass and cite the exact `Checklist version: YYYY-MM-DD` value in `review-report.md` as `Checklist Version`.

Before each role begins, the lead reviewer must provide the role input packet required by `role-checklists.md` from `normalized-input.md` only and cite its **role input packet readiness** row. Missing, `BLOCKED`, or chat-only packets block that role instead of allowing inferred evidence.

Before running roles, write a compact role routing rationale in `review-report.md`: list `Active roles` and `Skipped roles` explicitly. For every role that runs or is intentionally skipped, cite the route rule, `--type`/`--focus` flag, file-type heuristic, specialist profile, or explicit non-trigger that decided it. A missing skipped-role reason is a routing gap.

In standalone mode, fill `normalized-input.md` → `Role trigger matrix` before any role begins. Each supported role must have one row marked `run`, `skipped`, or `blocked`, with the normalized evidence ID(s) or explicit non-trigger signal that drove the decision. Do not activate architecture/security/ux/perf from chat-only intuition; first normalize the path, diff hunk, artifact, or command output that shows the trigger.

### spec-reviewer

**Trigger**: Always runs in pipeline mode. In standalone mode, runs when a brief/requirement/spec document exists (auto-generated or user-provided).

**Checklist source**: `skills/ff-review/references/role-checklists.md#spec-reviewer` (in addition to the Spec Review rubric).

**Standalone-specific**: When no explicit spec exists, the auto-generated brief becomes the de facto spec. The spec-reviewer checks whether the code/diff does what the brief describes: no more, no less. Flag scope that does not trace back to the brief as `major: unexplained scope`.

### quality-reviewer

**Trigger**: Always runs in both pipeline and standalone mode.

**Checklist source**: `skills/ff-review/references/role-checklists.md#quality-reviewer` (in addition to the Quality Review rubric).

**Deep code analysis**: When diff/code input is available, apply the 7-angle analysis from `skills/ff-review/references/deep-code-analysis.md`. Each finding must pass CONFIRMED/PLAUSIBLE verification. Metrics-based checks and diff-level analysis run in parallel; neither replaces the other.

**Standalone-specific**: Without implementation-notes, the quality-reviewer works from the code/diff directly. Apply heuristics without referencing executor claims.

### architecture-reviewer

**Trigger**: Runs when `--focus architecture` is specified, or when in-scope changes touch module boundaries, public interfaces, shared abstractions, framework/layering patterns, dependency direction, state ownership, or broad refactors.

**Trigger evidence**: Cite the role trigger matrix row and normalized evidence IDs for the architecture/module-boundary/shared-pattern signal before opening findings.

**Checklist source**: `skills/ff-review/references/role-checklists.md#architecture-reviewer`.

**Review priority**: Prioritize existing patterns, shared module reuse, avoiding unnecessary new implementations, architectural consistency, then local code quality. For projects that explicitly prefer functional style, flag new classes, singletons, or service-class abstractions unless normalized evidence shows an existing project convention requiring them.

### security-reviewer

**Trigger**: Runs when `--focus security` is specified, or when in-scope changes touch authentication/authorization, input validation/sanitization, secret/key handling, API/network boundaries, file system operations, or dependency additions.

**Trigger evidence**: Cite the role trigger matrix row and normalized evidence IDs for the auth/input/secrets/network/filesystem/dependency signal before opening findings.

**Checklist source**: `skills/ff-review/references/role-checklists.md#security-reviewer`.

### ux-reviewer

**Trigger**: Runs when `--focus ux` is specified, or when in-scope changes touch UI component files, CSS/styling, user-facing text/labels/messages, route/page definitions, or form handling code.

**Trigger evidence**: Cite the role trigger matrix row and normalized evidence IDs for the UI/text/route/form/accessibility signal before opening findings.

**Checklist source**: `skills/ff-review/references/role-checklists.md#ux-reviewer`.

### perf-reviewer

**Trigger**: Runs when `--focus perf` is specified, or when in-scope changes touch database queries/ORM calls, loops over large collections, caching layers, network call batching, or memory-intensive operations.

**Trigger evidence**: Cite the role trigger matrix row and normalized evidence IDs for the query/loop/cache/batching/memory signal before opening findings.

**Checklist source**: `skills/ff-review/references/role-checklists.md#perf-reviewer`.

## Routing rules

**Pipeline mode** (route-aware):

- small: quality-reviewer only, using **fast-review** depth
- medium: quality-reviewer only (medium-full may add spec-reviewer)
- high/epic: spec-reviewer (pass 1) -> quality-reviewer (pass 2), sequential gates
- Any route: architecture/security/ux/perf-reviewer triggered by file-type heuristics above

**Standalone mode**:

- No `--type` flag: quality-reviewer always runs; spec-reviewer runs if brief exists; other roles run only when file-type heuristics trigger.
- `--type spec`: spec-reviewer only
- `--type quality`: quality-reviewer only
- `--type architecture`: architecture-reviewer only
- `--type security`: security-reviewer only
- `--type ux`: ux-reviewer only
- `--type perf`: perf-reviewer only
- `--type all`: run all 6 roles regardless of file-type heuristics
- `--focus <role>`: alias for `--type <role>`
- **`--type` and `--focus` combined**: `--type` wins. `--focus` is ignored with a warning. Do not run two conflicting role sets.

Human review is a separate decision-partner gate, not an automated reviewer role.

## Role model hints

When a harness supports role-specific model selection, bind by capability rather than provider name and keep the decision advisory:

- spec-reviewer, architecture-reviewer, security-reviewer, and unresolved cross-role conflict aggregation -> strongest reasoning available.
- quality-reviewer -> standard reasoning/coding model; upgrade to strongest reasoning for broad refactors, weak verification, or many interacting files.
- ux-reviewer and perf-reviewer -> standard reasoning model unless normalized evidence shows accessibility, query-planning, caching, or large-data risk.

Record any non-default role/model assignment in the role-pass record, adapter notes, or `review-report.md` Reviewer Role Summary as a hint only. Model choice must never change role routing, evidence requirements, evidence IDs, evidence levels, verdict enums, approval rules, or the human review gate.

In standalone mode, if role/model or specialist profile selection is known before reviewer judgment, record it in `normalized-input.md` -> `role capability hints`. Use provider-neutral capability language (`strongest reasoning available`, `standard reasoning/coding model`, or `not_applicable`) and treat the section as audit metadata only.

## Specialist profiles

Specialist profiles define focused review lenses tied to the `specialist` field in `brief.md` YAML frontmatter. When review reads `brief.md`, it extracts the specialist primary and secondary values and automatically applies the corresponding assertion sets below. These assertions supplement, not replace, standard reviewer role checklists.

| Specialist | Focus | Key Assertions |
|---|---|---|
| security | auth/permissions/input validation | no hardcoded secrets, input sanitization, auth boundary checks, no eval/exec of untrusted input |
| ux | UI/text/accessibility | consistent terminology, a11y compliance, clear error messages, loading states for async operations |
| perf | performance/memory/latency | no N+1 queries, lazy load where appropriate, cache strategy documented, pagination/streaming for large datasets |
| correctness | logic/error handling/edge cases | edge cases covered, error propagation complete, idempotency where required, no unchecked error paths |
| maintainability | structure/naming/duplication/readability | DRY adherence, single responsibility, naming convention consistency, no unnecessary abstractions, clear intent, consistent abstraction level, short focused functions, magic values extracted |

Application logic:

1. Read `brief.md` YAML frontmatter `specialist.primary` and `specialist.secondary`.
2. For each non-`none` specialist value, activate the corresponding assertion set.
3. Every activated assertion must be checked and explicitly recorded in findings.
4. Primary specialist assertions are checked first and carry higher severity weight.
5. Secondary specialist assertions supplement the primary lens.
6. Record activated specialist profile(s) in `review-report.md` -> `specialist_profile` frontmatter field, including assertion count.
7. If `brief.md` has no specialist field or both values are `none`, skip specialist assertions and rely on standard reviewer role checklists only.

## Cross-role conflicts

When two roles produce conflicting findings:

1. Record both findings in the report with their role label.
2. Add a `requires human decision` marker in Findings.
3. Do not resolve the conflict by choosing one side. The human final judgment gate handles this.

## Role output structure

Each finding includes the reviewer role and evidence classification:

```markdown
- **Role**: spec-reviewer | quality-reviewer | architecture-reviewer | security-reviewer | ux-reviewer | perf-reviewer
- **Evidence Source**: <artifact/diff/command/source label>
- **Evidence Level**: observed | reported | missing
```

The report includes a **Reviewer Role Summary** section:

```markdown
## Reviewer Role Summary
- spec-reviewer: <verdict>, <N> findings (<blockers> blockers, <majors> major)
- quality-reviewer: <verdict>, <M> findings (<blockers> blockers, <majors> major)
- [other roles if triggered]
- Cross-role conflicts: <count>
```

Each active role must also leave a role-pass record, even when it finds nothing: markdown claim marker (`role=<reviewer> scope=<artifact section/evidence IDs> at=<ISO8601>`), trigger rationale, checklist version used, criteria basis, scope/evidence IDs inspected, evidence freshness (`current | stale | unknown`) with fetched_at/run label, observed verification command(s) or explicit no-command rationale, limitations/truncation, Independence Check, finding counts, and role verdict.
