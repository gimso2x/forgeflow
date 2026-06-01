# Evolution Rule Extraction

Use this reference during `/forgeflow:ship` when extracting reusable evolution rules from approved task evidence.

Ship is the evolution rule generation point for **all routes** (small, medium, high, epic). This ensures every completed task can produce reusable rules, not just high/epic.

## Rule lifecycle

```text
observe (ship) -> propose (ship) -> activate (ship) -> retire (ship or manual)
```

Ship consolidates the propose->validate->activate cycle because review has already validated the work. Evolution rules generated here are evidence-backed by the review-approved task artifacts.

## Scope decision

- **Global-advisory** (default): Rules applicable across projects. Written to `~/.forgeflow/evolution/active/<rule-name>.md`. Advisory only; cannot hard-block future tasks.
- **Project**: Rules specific to this repository's architecture/conventions. Written to `.forgeflow/evolution/active/<rule-name>.md`. Required constraints for this project.

Use project scope only when the rule depends on project-specific architecture (e.g., auth store structure, routing conventions). Default to global.

## Route-aware extraction

- **small**: Skip evolution rule extraction entirely. The change is too small to produce durable patterns.
- **medium**: Extract only if an obvious, high-confidence pattern emerges. Maximum 1-2 rules.
- **high/epic**: Full extraction. No hard limit, but prefer quality over quantity.

## Capture criteria

Extract an evolution rule when:

1. The pattern has concrete evidence from task artifacts (`implementation-notes.md`, `review-report.md`, `eval-record.md`, code diff).
2. It describes a trigger condition and expected behavior, not a vague sentiment.
3. It is not already covered by an existing active rule (check `~/.forgeflow/evolution/active/` and `.forgeflow/evolution/active/`).
4. It will actually save time or prevent mistakes in future tasks.

Do not capture:

- Task status, session chatter, or one-off observations
- Patterns so obvious they do not need enforcement
- Rules without evidence

## Extraction decision checklist

Extract an evolution rule if any answer is yes:

| # | Question | Example |
|---|----------|---------|
| 1 | Did the task repeat the same mistake at least twice? | scope boundary alert twice |
| 2 | Did execute add a file that was not in the plan? | unplanned test file |
| 3 | Did verification require at least two retries? | lint fix loop |
| 4 | Did the task apply an environment workaround? | ELOOP avoidance |
| 5 | Did review request changes and require re-review? | review re-request |
| 6 | Is this project setting meaningfully different from other projects? | Vite symlink issue |
| 7 | Will this pattern apply to future similar tasks? | medium test-after scope |

## Mandatory extraction triggers

If these patterns are observed, do not skip evolution rule extraction, except on small route:

1. **verification retry >= 2**: Verification failed and was retried at least twice.
2. **scope boundary violation**: A file outside plan scope was added.
3. **workaround applied**: An environment problem required a workaround.
4. **review re-request**: Review findings were fixed and re-reviewed.

For each mandatory trigger, use rule ID format `<trigger-type>-<task-slug>` (for example, `workaround-vite-eloop`, `scope-test-file-inclusion`).

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Proposing rules without evidence | Rules without grounding become cargo cult. |
| Auto-generating trivial rules | Noise drowns signal. |
| Retiring rules silently | Lost history makes the same mistake recur. |
