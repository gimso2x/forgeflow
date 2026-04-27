# So2x P0 Absorption Task

Date: 2026-04-28
Owner: ForgeFlow
Status: completed

## Goal

Absorb the useful P0 execution contracts from `so2x-flow` and `so2x-harness` into ForgeFlow without copying their whole scaffold.

## Source Repos

- `/home/ubuntu/work/so2x-flow`
- `/home/ubuntu/work/so2x-harness`

## Scope

### P0 items to implement

1. Add a cross-cutting `safe-commit` skill.
   - Source inspiration: `so2x-harness/templates/claude/skills/safe-commit.md`
   - ForgeFlow adaptation: require secret scan, file-size/scope sanity, verification evidence, and a final `SAFE` / `UNSAFE` disposition.
2. Add a cross-cutting `check-harness` skill.
   - Source inspiration: `so2x-harness/templates/claude/skills/check-harness.md`
   - ForgeFlow adaptation: score entry points, shared context, execution habits, verification, maintainability.
3. Add a lightweight plan/spec gate contract.
   - Source inspiration: `so2x-harness/templates/claude/hooks/spec-gate.sh` and `so2x-flow/tests/test_workflow_contracts.py`
   - ForgeFlow adaptation: encode required sections as a repository contract test first, not a heavy shell hook.
4. Keep the workflow small.
   - Do not import so2x scaffold structure wholesale.
   - Do not add unrelated CLI commands.
   - Do not mass-copy templates.

## Acceptance Criteria

- `skills/safe-commit/SKILL.md` exists and documents:
  - input artifacts
  - output artifact/report shape
  - secret scan requirement
  - file-size/scope drift checks
  - verification evidence checks
  - final `SAFE` / `UNSAFE` disposition
- `skills/check-harness/SKILL.md` exists and documents:
  - five scoring categories
  - score scale
  - output artifact/report shape
  - actionable fixes
- `skills/SKILLS.md` lists both cross-cutting skills.
- Contract tests assert the new skills and minimum plan/spec gate language.
- Existing validation remains green:
  - `python -m pytest tests/test_plugin_skill_contracts.py -q`
  - `python -m pytest tests/test_forgeflow_ux_contract.py -q`
  - `make validate`

## Non-goals

- No full so2x scaffold import.
- No new installed hook until the contract proves useful.
- No changes to ForgeFlow stage-boundary UX.
- No automatic stage chaining.

## Implementation Notes

- Treat these as cross-cutting skills: callable at any stage, but they must not redefine the main stage order.
- Prefer explicit evidence over agent self-report.
- If a check cannot be run, label it missing/reported instead of pretending it passed.
