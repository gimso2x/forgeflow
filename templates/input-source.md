---
schema: input-source/v1
input_type: <!-- URL|GitHub PR|GitHub commit|GitHub compare|repo path|git range|diff/patch|file bundle|existing artifact|ambiguous -->
---

# Standalone Review Input Source

<!-- ForgeFlow standalone review provenance template. Created before normalized-input.md. -->
<!-- Preserve raw input provenance. Do not include reviewer judgment here. -->

## Detected Input Type
<!-- URL | GitHub PR | GitHub commit | GitHub compare | repo path | git range | diff/patch | file bundle | existing artifact | ambiguous -->

## Source Classification Rationale
- **Why this type**: <!-- concrete signal used, e.g., URL pattern, .git presence, diff markers, explicit file list -->
- **Ambiguities considered**: <!-- plausible alternate source classes considered, or none -->
- **Ambiguity outcome**: <!-- resolved | blocked; block if classification would require guessing -->

## Original Input
<!-- Exact user-provided URL, path, range, diff summary, or file list. -->

## Fetch Method
- **Adapter/Tool**: <!-- Claude Code | Codex | Gemini CLI | Cursor | gh | git | web_extract | file-read | not_applicable -->
- **Command/API Label**: <!-- exact command/API/source label used, or not_applicable -->
- **Access Posture**: <!-- read_only | verification_only | not_applicable; state-changing remote/API actions are forbidden for review evidence fetch -->
- **Mutation Check**: <!-- PASS | FAIL; PASS means the fetch method did not comment, approve, label, dispatch CI, deploy, write product files, change branches, or perform destructive cleanup -->

## Fetch Method Ledger
<!-- Required when more than one command/API/source label was used. Keep one row per evidence-producing fetch so access posture and mutation checks are auditable per evidence source, not only for the overall adapter. -->
- **F1**: <!-- evidence_ids=E1,E2; adapter/tool=<tool>; command/API/source=<exact label>; access_posture=read_only|verification_only|not_applicable; mutation_check=PASS|FAIL; result=success|partial|failed|not_applicable -->

## Fetch Status
<!-- success | partial | failed | not_applicable -->

## Evidence Notes
- **Missing Evidence**: <!-- none or list missing required inputs -->
- **Truncated Evidence**: <!-- none or what was truncated and why -->
- **Integrity**: <!-- complete | partial | failed | truncated:<N/M lines> -->

## Evidence Source Map
<!-- One row per normalized evidence item. IDs must match normalized-input.md. This keeps fetch provenance auditable before reviewer roles cite evidence. Include the normalized evidence type/status/freshness/level and fetch posture pointer here so handoff reviewers can detect mismatches without re-reading chat logs. -->
- **E1**: <!-- source label or command/API used; fetch_id=F1|not_applicable; type=diff|file|artifact|url|command_output|reported_summary|missing; status=success|partial|failed|not_applicable; fetched_at=<ISO8601 timestamp|run label|not_applicable>; freshness_status=current|stale|unknown; evidence_level=observed|reported|missing; integrity=complete|partial|failed|truncated:<N/M lines> -->

## Timestamp
<!-- ISO timestamp or run label -->
