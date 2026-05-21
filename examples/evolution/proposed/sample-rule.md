# verify-before-ship
<!-- Run verification commands before presenting branch-disposition options -->
Trigger: ship stage entry with approved review-report.md
Stage: ship
Mode: required_project_rule
Apply: Re-run plan verification commands and record results in ship-summary.md before merge/PR/keep/discard options
Skip: When verification was run within the same session and evidence_index already shows PASS for all gates
