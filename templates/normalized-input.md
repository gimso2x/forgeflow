# Standalone Review Normalized Input

<!-- ForgeFlow standalone review normalization template. Fill before reviewer judgment begins. -->
<!-- Required shape: brief / evidence / scope / constraints. Evidence must be fetched or provided; never fabricate. -->

## brief
- **title**: <!-- explicit or inferred review target -->
- **description**: <!-- user description, PR/body summary, commit message, artifact heading, or inferred summary -->
- **source**: <!-- explicit | inferred -->

## evidence

<!-- stable evidence IDs are the handoff boundary between adapters and reviewer roles. Keep IDs stable, unique within this file, and cite them from review-report.md role-pass records. If evidence is sampled or truncated, the item ID still points to the sampled content and its limitation note. -->

### Evidence Item 1
- **id**: <!-- e.g., E1; unique evidence ID, do not reuse for another item -->
- **type**: <!-- diff | file | artifact | url | command_output | reported_summary | missing -->
- **source**: <!-- gh pr diff <n> | git diff <range> | file-read:path | web_extract:url | run-ledger.md | etc. -->
- **fetch_status**: <!-- success | partial | failed | not_applicable; must match input-source.md Evidence Source Map -->
- **evidence_level**: <!-- observed | reported | missing -->
- **truncated**: <!-- true | false -->
- **limitations**: <!-- none | auth/fetch failure | sampled | truncated:<N/M lines> | missing file | other visible limitation -->
- **content**:
  ```text
  <!-- concrete fetched/provided evidence, or null for missing evidence -->
  ```

## scope
- **files**: <!-- changed/listed files, or none -->
- **ranges**: <!-- commit ranges, hunk ranges, URL content bounds, or none -->
- **exclusions**: <!-- paths/areas excluded by user scope or adapter limits -->
- **rationale**: <!-- why this is the review boundary -->
- **scope_source_map**: <!-- map each in-scope file/range/content bound to normalized evidence ID(s), e.g., src/app.ts=E1 or url:section-2=E2; use none only for blocked/missing scope evidence -->

## constraints
- **roles**: <!-- spec-reviewer | quality-reviewer | security-reviewer | ux-reviewer | perf-reviewer -->
- **focus**: <!-- user-requested or inferred focus areas -->
- **user_rules**: <!-- exact user restrictions, or none -->
- **inferred_rules**: <!-- route/input-derived constraints, large diff sampling, test-only focus, etc. -->
- **ignored_flags**: <!-- e.g., --focus ignored because --type wins, or none -->

### Role trigger matrix
<!-- For each supported reviewer role, record whether it ran or was skipped and cite the normalized evidence ID(s) or explicit non-trigger signal that made the decision. Do not route a role from chat-only context. -->
- **spec-reviewer**: <!-- run | skipped | blocked — trigger: brief/spec present, --type, route, or none; evidence: E1,E2 | none -->
- **quality-reviewer**: <!-- run | skipped | blocked — trigger: default, --type, route, or none; evidence: E1,E3 | none -->
- **security-reviewer**: <!-- run | skipped | blocked — trigger: auth/input/secrets/network/filesystem/dependency signal, --type/--focus, or explicit non-trigger; evidence: E2 | none -->
- **ux-reviewer**: <!-- run | skipped | blocked — trigger: UI/text/route/form/a11y signal, --type/--focus, or explicit non-trigger; evidence: E4 | none -->
- **perf-reviewer**: <!-- run | skipped | blocked — trigger: query/loop/cache/batching/memory signal, --type/--focus, or explicit non-trigger; evidence: E5 | none -->

## role evidence map
<!-- Before reviewer roles start, map each active role to the evidence IDs it may use. This prevents roles from silently relying on unnormalized or chat-only evidence. Use `none — <reason>` only when a role is intentionally blocked or no evidence type exists for that role. -->
<!-- Consistency guard: every role listed in constraints.roles must be `run` or `blocked` in the Role trigger matrix and must have a non-empty evidence map entry or an explicit blocked rationale. Any role marked `run` here must also appear in constraints.roles. -->
- **spec-reviewer**: <!-- E1, E2 | none — reason -->
- **quality-reviewer**: <!-- E1, E3 | none — reason -->
- **security-reviewer**: <!-- E2 | none — not triggered -->
- **ux-reviewer**: <!-- E4 | none — not triggered -->
- **perf-reviewer**: <!-- E5 | none — not triggered -->

## role input packet readiness
<!-- Fill once per active or blocked reviewer role before judgment, and refresh after any Evidence Escalation Log entry, new evidence item, scope change, constraint change, or role-routing change. READY means the role has a trigger decision, allowed evidence IDs, scoped files/ranges/exclusions, constraints/focus flags, visible limitations, and a packet freshness check sourced only from this normalized input. BLOCKED means one or more packet fields are missing or stale; the role must not judge until the missing/stale field is normalized or recorded as unavailable. Skipped roles may use SKIPPED with an explicit non-trigger reason. -->
- **spec-reviewer**: <!-- READY | BLOCKED | SKIPPED — packet fields present/missing/stale: trigger,evidence_ids,scope,constraints,limitations,packet_freshness; reason -->
- **quality-reviewer**: <!-- READY | BLOCKED | SKIPPED — packet fields present/missing/stale: trigger,evidence_ids,scope,constraints,limitations,packet_freshness; reason -->
- **security-reviewer**: <!-- READY | BLOCKED | SKIPPED — packet fields present/missing/stale: trigger,evidence_ids,scope,constraints,limitations,packet_freshness; reason -->
- **ux-reviewer**: <!-- READY | BLOCKED | SKIPPED — packet fields present/missing/stale: trigger,evidence_ids,scope,constraints,limitations,packet_freshness; reason -->
- **perf-reviewer**: <!-- READY | BLOCKED | SKIPPED — packet fields present/missing/stale: trigger,evidence_ids,scope,constraints,limitations,packet_freshness; reason -->

## role input packets
<!-- For every READY or BLOCKED reviewer role, write the compact packet the lead hands to that role. Each packet must be copied from normalized fields above, not chat memory or hidden adapter state. Skipped roles may be listed as `none — <explicit non-trigger reason>`. -->
- **spec-reviewer**: <!-- trigger=<matrix row>; evidence_ids=<role evidence map IDs>; scope=<files/ranges/exclusions>; constraints=<roles/focus/user_rules/inferred_rules/ignored_flags>; limitations=<evidence limitations/truncation/fetch failures>; packet_freshness=<current after latest evidence/scope/constraint/routing change> -->
- **quality-reviewer**: <!-- trigger=<matrix row>; evidence_ids=<role evidence map IDs>; scope=<files/ranges/exclusions>; constraints=<roles/focus/user_rules/inferred_rules/ignored_flags>; limitations=<evidence limitations/truncation/fetch failures>; packet_freshness=<current after latest evidence/scope/constraint/routing change> -->
- **security-reviewer**: <!-- trigger=<matrix row>; evidence_ids=<role evidence map IDs>; scope=<files/ranges/exclusions>; constraints=<roles/focus/user_rules/inferred_rules/ignored_flags>; limitations=<evidence limitations/truncation/fetch failures>; packet_freshness=<current after latest evidence/scope/constraint/routing change> -->
- **ux-reviewer**: <!-- trigger=<matrix row>; evidence_ids=<role evidence map IDs>; scope=<files/ranges/exclusions>; constraints=<roles/focus/user_rules/inferred_rules/ignored_flags>; limitations=<evidence limitations/truncation/fetch failures>; packet_freshness=<current after latest evidence/scope/constraint/routing change> -->
- **perf-reviewer**: <!-- trigger=<matrix row>; evidence_ids=<role evidence map IDs>; scope=<files/ranges/exclusions>; constraints=<roles/focus/user_rules/inferred_rules/ignored_flags>; limitations=<evidence limitations/truncation/fetch failures>; packet_freshness=<current after latest evidence/scope/constraint/routing change> -->

## role capability hints
<!-- Optional, advisory only. Record any harness-selected reviewer model/profile/tooling hints for auditability, but role capability hints must not affect routing, evidence IDs, evidence levels, verdict enums, approval rules, or the human review gate. Use capability language such as strongest reasoning available or standard reasoning/coding model; do not require provider-specific requirements. -->
- **spec-reviewer**: <!-- strongest reasoning available | standard reasoning | not_applicable; reason -->
- **quality-reviewer**: <!-- standard reasoning/coding model | strongest reasoning available; reason -->
- **security-reviewer**: <!-- strongest reasoning available | standard reasoning | not_applicable; reason -->
- **ux-reviewer**: <!-- standard reasoning | strongest reasoning available; reason -->
- **perf-reviewer**: <!-- standard reasoning | strongest reasoning available; reason -->

## review ownership plan
<!-- Fill before any delegated or parallel reviewer pass starts. This keeps team-mode absorption declarative: exactly one lead owns aggregation, each member owns at most one pass, cross-role conflicts stay visible for human-gate decisions, and no role may spawn unmanaged child work or mutate product files. Member assignments are role claims, not a task scheduler: members must not create additional reviewer roles, reassign scope, resolve conflicts privately, or write outside their assigned review-report section. -->
- **lead_reviewer**: <!-- exactly one identifier or role responsible for normalization, role routing, aggregation, conflicts, and human gate -->
- **member_assignments**:
  - <!-- role=<reviewer> scope=<artifact section/evidence IDs> claim_marker=<role=... scope=... at=<ISO8601>> writes=<review-report section only> -->
- **aggregation_owner**: <!-- must match lead_reviewer -->
- **child_work_policy**: <!-- no unmanaged child work; evidence gaps use Evidence Escalation Log -->
- **role_reassignment_policy**: <!-- lead-only; members cannot create/reassign roles or broaden scope -->
- **conflict_policy**: <!-- unresolved cross-role conflicts stay in review-report.md and trigger Human Review Gate; lead aggregates but does not silently choose a winner -->
- **product_mutation_policy**: <!-- forbidden during review; findings hand back to execute -->

## normalization gate
<!-- Complete this gate before any reviewer role starts. If any item is FAIL, review verdict is blocked until the missing provenance is fixed or explicitly recorded as unavailable. -->
- **brief_present**: <!-- PASS | FAIL -->
- **evidence_present_or_blocked**: <!-- PASS | FAIL; PASS means at least one concrete evidence item exists OR fetch failure is recorded as blocked -->
- **scope_explicit**: <!-- PASS | FAIL -->
- **constraints_explicit**: <!-- PASS | FAIL -->
- **limitations_visible**: <!-- PASS | FAIL; truncation, auth failures, sampling, excluded paths, and ignored flags are listed above -->

## adapter handoff checklist
<!-- Complete before reviewer judgment. If any item is FAIL, the lead reviewer blocks approval unless the limitation is explicitly narrowed by a human. -->
- **source_classified**: <!-- PASS | FAIL; input-source.md explains detected type and ambiguity outcome -->
- **fetch_reproduced**: <!-- PASS | FAIL; every evidence ID maps to a command/API/source label -->
- **normalization_complete**: <!-- PASS | FAIL; brief/evidence/scope/constraints are filled above -->
- **limitations_visible**: <!-- PASS | FAIL; failed/partial/truncated/missing evidence remains visible -->
- **canonical_review_ownership**: <!-- PASS | FAIL; no adapter-specific verdict/report/auto-approval path -->
