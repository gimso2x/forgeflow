# Standalone Review Normalized Input

<!-- ForgeFlow standalone review normalization template. Fill before reviewer judgment begins. -->
<!-- Required shape: brief / evidence / scope / constraints. Evidence must be fetched or provided; never fabricate. -->

## brief
- **title**: <!-- explicit or inferred review target -->
- **description**: <!-- user description, PR/body summary, commit message, artifact heading, or inferred summary -->
- **source**: <!-- explicit | inferred -->

## evidence

### Evidence Item 1
- **id**: <!-- e.g., E1 -->
- **type**: <!-- diff | file | artifact | url | command_output | reported_summary | missing -->
- **source**: <!-- gh pr diff <n> | git diff <range> | file-read:path | web_extract:url | run-ledger.md | etc. -->
- **evidence_level**: <!-- observed | reported | missing -->
- **truncated**: <!-- true | false -->
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
