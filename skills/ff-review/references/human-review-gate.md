# Human Review Gate

Use this reference after automated `/forgeflow:ff-review` has produced `review-report.md`.

Reference policy: `docs/review-model.md`.

Classify whether a human decision-partner review is required. Human review is a separate decision-partner gate, not an automated reviewer role.

## Mandatory human review triggers

Human review is required when any condition below matches:

| # | Trigger | Reason |
|---|---------|--------|
| 1 | Public API, CLI surface, or workflow contract changes | External dependency impact |
| 2 | Authentication, authorization, permission, or secret changes | Security risk |
| 3 | Data persistence, creation, update, delete, or migration changes | Data integrity |
| 4 | New dependency or lockfile change | Supply-chain risk |
| 5 | Environment variable, config file, or deployment setting changes | Operations risk |
| 6 | Security-adjacent code changes, including input validation, error handling, or network boundaries | Indirect security impact |
| 7 | State machine, business rule, payment, or settlement logic changes | Business logic risk |
| 8 | Cross-module contract or interface signature changes | Integration risk |

When a mandatory trigger is detected, record `Decision: required` in the Human Review Gate section of `review-report.md`, with the trigger number and reason.

## Skip criteria

Human review may be skipped only when **all** of these are true:

- Change scope is small/localized and repeats an established pattern.
- Risk is low, rollback is easy, and no state/data/security/permission behavior changes are involved.
- Automated verification is fresh and sufficient.
- Similar prior work repeatedly received LGTM without discussion.
- No cross-role automated-review conflict is present.
- None of the mandatory human review triggers above are matched.

## Required conditions

Human review is required when any of these are true:

- Public API, CLI surface, workflow contract, or artifact schema changes.
- State, data persistence, deletion, migration, or branch-disposition behavior changes.
- Security, permissions, authentication, secrets, or error-recovery behavior changes.
- Broad impact, difficult rollback, or unclear ownership boundaries.
- Repeated design disagreement or cross-role reviewer conflict.
- Any p1/p2 finding is rejected or marked `risk_accepted` rather than fixed.
- Automated review is blocked, weakly evidenced, or missing required artifacts.

## Human Review Packet

When human review is required, append a **Human Review Packet** section to `review-report.md` with:

- decision needed: concrete question/tradeoff for the human reviewer
- context: design intent and selected tradeoffs
- automated evidence: verdict, blockers, residual risks, verification quality
- recommended discussion prompts: questions rather than edit commands
- handoff target: `ship` only after human decision is recorded, otherwise `execute`

When human review is skipped, record the skip reason in `review-report.md` and make it explicit that automated review is the final review gate for this task.
