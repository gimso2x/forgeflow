# Standalone Review Normalized Input

<!-- ForgeFlow standalone review normalization template. Fill before reviewer judgment begins. -->
<!-- Required shape: brief / evidence / scope / constraints. Evidence must be fetched or provided; never fabricate. -->

## brief
- **title**: <!-- explicit or inferred review target -->
- **description**: <!-- user description, PR/body summary, commit message, artifact heading, or inferred summary -->
- **source**: <!-- explicit | inferred -->

## evidence

<!-- stable evidence IDs are the handoff boundary between adapters and reviewer roles. Keep IDs stable and cite them from review-report.md role-pass records. If evidence is sampled or truncated, the item ID still points to the sampled content and its limitation note. -->

### Evidence Item 1
- **id**: <!-- e.g., E1 -->
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

## constraints
- **roles**: <!-- spec-reviewer | quality-reviewer | security-reviewer | ux-reviewer | perf-reviewer -->
- **focus**: <!-- user-requested or inferred focus areas -->
- **user_rules**: <!-- exact user restrictions, or none -->
- **inferred_rules**: <!-- route/input-derived constraints, large diff sampling, test-only focus, etc. -->
- **ignored_flags**: <!-- e.g., --focus ignored because --type wins, or none -->

## role evidence map
<!-- Before reviewer roles start, map each active role to the evidence IDs it may use. This prevents roles from silently relying on unnormalized or chat-only evidence. Use `none — <reason>` only when a role is intentionally blocked or no evidence type exists for that role. -->
- **spec-reviewer**: <!-- E1, E2 | none — reason -->
- **quality-reviewer**: <!-- E1, E3 | none — reason -->
- **security-reviewer**: <!-- E2 | none — not triggered -->
- **ux-reviewer**: <!-- E4 | none — not triggered -->
- **perf-reviewer**: <!-- E5 | none — not triggered -->

## normalization gate
<!-- Complete this gate before any reviewer role starts. If any item is FAIL, review verdict is blocked until the missing provenance is fixed or explicitly recorded as unavailable. -->
- **brief_present**: <!-- PASS | FAIL -->
- **evidence_present_or_blocked**: <!-- PASS | FAIL; PASS means at least one concrete evidence item exists OR fetch failure is recorded as blocked -->
- **scope_explicit**: <!-- PASS | FAIL -->
- **constraints_explicit**: <!-- PASS | FAIL -->
- **limitations_visible**: <!-- PASS | FAIL; truncation, auth failures, sampling, excluded paths, and ignored flags are listed above -->
