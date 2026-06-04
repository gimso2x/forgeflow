# Standalone Mode Reference

When review is invoked without prior clarify/plan/execute stages — no resolved task directory (`~/.forgeflow/projects/<project-slug>/tasks/<id>/` by default) with pipeline artifacts — it operates in **standalone mode**. The review becomes an independent inspection gate, not a pipeline post-step.

## Input type detection

Detect input type by pattern, in this priority order:

1. **URL** — String starts with `https://` or `http://`. Known patterns:
   - `github.com/<owner>/<repo>/pull/<n>` → GitHub PR. Fetch via `gh pr diff <n>` or `gh pr view <n> --json title,body,files`.
   - `github.com/<owner>/<repo>/commit/<sha>` → GitHub commit. Fetch via `gh api repos/<owner>/<repo>/commits/<sha>`.
   - `github.com/<owner>/<repo>/compare/<a>...<b>` → GitHub compare. Fetch via `gh api repos/<owner>/<repo>/compare/<a>...<b>`.
   - Any other URL → Fetch page content via `web_extract` or `curl`. Extract main content, strip navigation/chrome.
   - **Failure handling**: If fetch returns 404, auth error, or empty content, record as `blocked: input fetch failed — <url>`. Do not proceed with guessed content.

2. **Repo path** — String is a local directory path that exists on disk and contains a `.git/` directory or is inside a git worktree.
   - No branch/commit specified → use current worktree diff (`git diff HEAD`) and working tree state.
   - Branch range specified (`main..feature`) → `git diff <range>`.
   - Single commit → `git show <sha> --stat` + `git diff <sha>~1 <sha>`.
   - **Failure handling**: If directory doesn't exist or isn't a git repo, record as `blocked: invalid repo path — <path>`.

3. **Diff/patch** — Input contains unified diff markers (`--- a/`, `+++ b/`, `@@`), is provided with `--diff` flag, or is a local file path ending in `.diff` or `.patch`.
   - For `.diff` / `.patch` paths, read the file first and record `input-source.md` with original input as the file path and fetch command/source as `file-read:<path>`.
   - Parse hunks: extract file paths from `---`/`+++` headers, line ranges from `@@` markers.
   - Build a virtual file map: for each file in the diff, record additions, deletions, and context lines.
   - **Failure handling**: If diff cannot be parsed (no markers, malformed hunks), attempt to treat as file bundle. If neither works, record as `blocked: unparseable diff input`.

4. **File bundle** — One or more file paths provided. Verified to exist on disk.
   - Read each file. For each file, detect language and structure.
   - Build evidence from file contents. Scope = the listed files.
   - **Failure handling**: If any file doesn't exist, record as `blocked: missing input file — <path>`. Do not skip silently.

5. **Existing artifact** — Path to a resolved `tasks/` directory or specific artifact file (e.g., `review-report.md`, `implementation-notes.md`).
   - Read the artifact. Use its content as evidence.
   - If it's a task directory, read all artifacts found inside for context.
   - **Failure handling**: If path doesn't exist, fall through to other detection. Do not assume artifact format.

6. **Ambiguous input** — If no type matches, ask the user to clarify the input type. Do not guess and proceed with wrong assumptions.

## Synthetic task directory bootstrapping

When standalone mode is detected, create a synthetic task directory:

```
<task-dir>
├── input-source.md      # Raw input provenance (URL, path, diff metadata)
├── normalized-input.md   # Brief + evidence + scope + constraints (auto-generated)
└── review-report.md      # Output (written during review)
```

Create `input-source.md` from `templates/input-source.md`. It records:
- Input type detected
- Source classification rationale: why the type was selected, plausible ambiguities considered, and whether ambiguity was resolved or blocked
- Original input value (URL, path, diff snippet)
- Fetch command used (if applicable)
- Access posture and mutation check for each fetch method, proving evidence collection stayed read-only/verification-only and did not comment, approve, label, dispatch CI, deploy, write product files, change branches, or perform destructive cleanup
- Fetch Method Ledger rows when multiple commands/API/source labels produce evidence, tying each fetch posture and mutation check to the evidence IDs it produced
- Fetch result status (success/partial/failed)
- Missing/truncated evidence notes
- Evidence Source Map linking each normalized evidence ID to the fetch command/API/source label or Fetch Method Ledger row, normalized evidence type, fetch status, fetched_at timestamp/run label, freshness status, evidence level, and integrity
- Timestamp

Create `normalized-input.md` from `templates/normalized-input.md`. It records the 4-field structure (see Input Normalization below).

Before any reviewer roles begin, fill the template's **role evidence map**. Map every active reviewer role to the normalized evidence IDs it may cite; for inactive or blocked roles, write `none — <reason>`. Evidence IDs must be stable and unique within `normalized-input.md`; never reuse an ID for a different file, diff hunk, command output, or sampled content. Roles must not cite chat-only or unnormalized evidence. If a role needs additional material, add it as a new evidence item in `normalized-input.md` first, including type, source, fetch status, fetched_at timestamp/run label, freshness status, evidence level, and limitation/truncation notes, then mirror the same type/status/freshness/level plus provenance in `input-source.md` Evidence Source Map.

After the role evidence map is filled, perform a routing consistency check: every role listed in `constraints.roles` must be `run` or `blocked` in the Role trigger matrix and must have either allowed evidence IDs or an explicit blocked rationale in the role evidence map. Any role marked `run` must also appear in `constraints.roles`. A mismatch blocks reviewer judgment until normalization is corrected; do not silently add or drop roles in `review-report.md`.

Then fill **role input packet readiness** for every active, blocked, or skipped reviewer role. Mark a role `READY` only when its trigger decision, allowed evidence IDs, scoped files/ranges/exclusions, constraints/focus flags, visible limitations, and packet freshness are all present in `normalized-input.md`. Mark it `BLOCKED` when any packet field is missing or stale and prevent that role from judging until the missing/stale field is normalized or recorded as unavailable. Mark skipped roles `SKIPPED` with an explicit non-trigger reason. After readiness is set, fill **role input packets** for every READY or BLOCKED role by copying the trigger, evidence IDs, scope, constraints, limitations, and packet freshness from normalized fields; skipped roles may be `none — <explicit non-trigger reason>`. Refresh readiness and packets after any Evidence Escalation Log entry, new evidence item, scope change, constraint change, or role-routing change. Reviewer roles must cite their packet row before judgment and must not replace missing packet fields with chat memory or hidden adapter state. When citing scope, use the `scope_source_map` evidence IDs rather than unstated adapter file lists.

Before any delegated or parallel reviewer pass begins, fill the template's **review ownership plan**. Record exactly one lead reviewer for normalization, role routing, aggregation, conflict visibility, and the human gate; record each member assignment with one reviewer role, evidence/scope IDs, claim marker, and writable report section. Each member claim marker must be unique, written to the artifact before work starts, and read back from the artifact before that member proceeds; duplicate or unreadable claim markers block delegated review. The `aggregation_owner` must match the single `lead_reviewer`; multiple leads, missing leads, or lead/aggregation-owner mismatch block approval. If no delegation is used, write `member_assignments: none — single lead review` and `claim_marker_integrity: not_applicable — single lead review`. Member assignments are role claims, not a task scheduler: members cannot create additional reviewer roles, reassign scope, broaden their evidence map, or write outside their assigned report section. Any missing lead, duplicate aggregation owner, duplicate/unreadable claim marker, unmanaged child-work allowance, member-side role reassignment, scope broadening, or product-mutation allowance blocks approval until corrected.

Before any reviewer role begins, complete the template's **normalization gate**. Scope is explicit only when `normalized-input.md` includes a `scope_source_map` that ties each in-scope file, range, or content bound to normalized evidence IDs, or records the scope evidence as blocked/missing. If `brief_present`, `evidence_present_or_blocked`, `scope_explicit`, `constraints_explicit`, or `limitations_visible` is `FAIL`, stop with `blocked` and record the missing provenance in `review-report.md`; do not let reviewer roles fill gaps by assumption.

After the role evidence map and before packet readiness, complete `normalized-input.md` → **evidence integrity check**. Verify that every evidence ID cited by `constraints.roles`, the Role trigger matrix, role evidence map, `scope_source_map`, and role input packets resolves to exactly one evidence item and matches the corresponding `input-source.md` Evidence Source Map row for source, type, fetch status, fetched_at/run label, freshness status, and evidence level. Any missing, duplicated, mismatched, stale-evidence, or stale packet reference blocks reviewer judgment until normalization is corrected or the affected role is explicitly marked blocked/limited.

Before scope/routing is finalized, fill `normalized-input.md` → **Evidence Gap Register** for every expected evidence class that is missing, partial, sampled, truncated out of trigger visibility, or blocked by fetch/auth/tool failure. Include the expected source, affected normalized field, affected reviewer roles, disposition (`blocked`, `limited`, or `not_applicable`), and reason. If there are no gaps, write `none`. Reviewer role summaries and role-pass records must cite the register so approval cannot hide unavailable PR metadata, changed-file lists, command output, referenced artifacts, or large-diff omissions behind a generic limitation note.

Before reviewer judgment, also complete the template's **adapter handoff checklist**. Mark `source_classified`, `fetch_reproduced`, `fetch_ledger_complete`, `fetch_posture_constrained`, `normalization_complete`, `limitations_visible`, and `canonical_review_ownership` as `PASS` or `FAIL`. `fetch_ledger_complete` is `PASS` only when multi-fetch evidence has one `input-source.md` Fetch Method Ledger row per evidence-producing fetch and every Evidence Source Map `fetch_id` resolves to that row; use `PASS` for single-fetch/not-applicable handoffs when the Evidence Source Map still names the source label. Any `FAIL` blocks approval unless a human explicitly narrows the review scope and records the limitation; adapters must not compensate by writing a parallel verdict or report.

If any reviewer role needs evidence outside the role evidence map, pause that role and add an **Evidence Escalation Log** entry in `review-report.md` before judgment continues. The lead reviewer must either add a new evidence item to `normalized-input.md` and mirror its provenance in `input-source.md`, or record the request as unavailable with the affected role blocked/limited. After the escalation outcome, refresh the affected role evidence map, input packet readiness, and role input packet before that role can continue; stale packets block judgment. Do not use chat memory, hidden adapter state, or unrecorded file reads to satisfy the gap.

If `.forgeflow/` doesn't exist, create it. Do not initialize a full ForgeFlow workspace — only the task directory and its files.

## Standalone constraints

- No `brief.md`, `plan.md`, `ledger.md`, or `implementation-notes.md` is expected. Do not flag their absence as findings.
- No route selection (small/medium/high/epic) — standalone mode always runs as a single comprehensive pass unless `--type` is specified.
- No execute micro-gates table — skip that section in the report.
- Evolution rule review is always `not_applicable` in standalone mode.
- The review report is the final artifact. There is no automatic ship.
