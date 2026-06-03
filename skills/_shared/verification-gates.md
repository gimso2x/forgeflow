# Verification Gate Catalog

> Shared gate definitions. Skills reference this catalog instead of duplicating gate tables.
> Each skill adds stage-specific gate selection rules on top of this base catalog.

## Base Gates

| Gate | Description | Applicable when |
|------|-------------|-----------------|
| `scope_boundary_check` | Verify no unintended files changed via git diff | All tasks |
| `contract_check` | Verify step output against stated contracts | Tasks with cross-module contracts |
| `version_consistency_check` | Verify version strings match across artifacts | Tasks referencing package versions |
| `build` | Build passes | Code tasks |
| `lint` | Linter passes | Code tasks |
| `type_check` | Type checker passes | Typed code tasks |
| `test` | Test suite passes | Code tasks with tests |

## Documentation Gates

| Gate | Description | Applicable when |
|------|-------------|-----------------|
| `screen_count_check` | Verify row counts match expected numbers | Documents with screen/page catalogs |
| `cross_document_consistency_check` | Verify terminology/version consistency across files | Multi-document deliverables |
| `document_validation` | Lint, build, test on document-only workspace | Any documentation task |
| `total_preservation_check` | Verify aggregate values (effort, count) unchanged | Tasks with summary totals |

## Stage-specific usage

- **Clarify**: selects gates by route tier (small: ≥1 fast gate; medium: lint+type_check+test; high/epic: full suite). See clarify SKILL.md step 8.
- **Plan**: adds documentation gates to the Verification Plan. See ff-plan SKILL.md Gate selection rules.
- **Execute**: applies adaptive verification per change type. See execute SKILL.md Adaptive verification.

## Route-tier minimum gates

| Route | Minimum gates |
|-------|---------------|
| small | ≥1 of build, lint, type_check (whichever is fastest) |
| medium | lint + type_check, plus test if tests exist |
| high | build + lint + type_check + test |
| epic | full suite + milestone-level integration tests |
