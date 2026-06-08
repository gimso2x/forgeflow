# Consensus Review and Drift Detection

Reference for ff-review's optional consensus review and quantitative drift detection.

## Multi-model Consensus Review (optional)

For high/epic routes, an optional consensus review can provide additional confidence. Enable via `<storage-root>/defaults.md`:

```yaml
consensus_review: true
```

When enabled:

1. After the primary review produces `review-report.md`, dispatch the same review to a different model tier if available (adapter maps the secondary model via `docs/adapter-config.md` model tier table).
2. The secondary reviewer reads the same artifacts and produces its own independent verdict.
3. Compare verdicts:
   - **Both approved** → final verdict: `approved`
   - **Both changes_requested** → final verdict: `changes_requested`, merge finding lists
   - **Disagreement** → surface the conflict in `review-report.md` → Consensus section. The lead reviewer (primary) resolves and records the rationale.
4. Record in `review-report.md` Reader Summary:
   ```
   consensus: enabled
   primary_verdict: <verdict>
   secondary_verdict: <verdict>
   final_verdict: <verdict>
   disagreement_resolution: <rationale or "none">
   ```
5. Consensus review does not replace the required spec+quality passes — it supplements them.

Adapters that only have a single model available should ignore this option silently.

## Drift Detection (medium-full/high/epic)

Quantitative drift detection compares the final implementation against the original brief and plan to catch scope creep and goal drift.

### Drift score calculation

```
drift_score = goal_drift * 0.5 + constraint_drift * 0.3 + scope_drift * 0.2
```

Each component is scored 0.0-1.0:

| Component | Source | Calculation |
|-----------|--------|-------------|
| `goal_drift` | brief.md Objective vs implementation-notes.md final status | 0.0 if objective met, 0.5 if partially met, 1.0 if objective changed substantially |
| `constraint_drift` | brief.md Constraints vs actual changes | Count violated constraints / total constraints |
| `scope_drift` | brief.md scope_files vs `git diff --name-only` | Count unplanned files / total changed files |

### Thresholds

- `drift_score ≤ 0.2` → `drift: minimal` — no action
- `0.2 < drift_score ≤ 0.4` → `drift: moderate` — record in review-report.md, no blocker
- `drift_score > 0.4` → `drift: significant` — add as finding in review-report.md, recommend scope reconciliation

### Recording

Include drift analysis in `review-report.md` → Drift Analysis section:

```
## Drift Analysis
goal_drift: <score> — <note>
constraint_drift: <score> — <note>
scope_drift: <score> — <note>
drift_score: <score> — minimal|moderate|significant
unplanned_files: <list>
missing_scope_items: <list>
```

### long-run integration

When long-run stage runs after ship, it reads the drift analysis from `review-report.md` and records it in `eval-record.md` for cross-task pattern detection. If drift_score > 0.4 consistently across tasks, long-run may propose an evolution rule for scope discipline.
