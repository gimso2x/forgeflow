# Harness Onboarding Absorption Implementation Plan

> **For Hermes:** Implement directly with strict TDD for behavior changes. Keep this PR to the first absorption slice only.

**Goal:** Absorb the useful onboarding layer from `harness_framework`/OMC without importing their runtime, auto-commit loop, or parallel control plane.

**Architecture:** Extend the existing project-local preset installer so teams can optionally generate ForgeFlow starter docs and get a richer onboarding/prompt-contract note. Starter docs are templates only; canonical workflow remains `brief`/`plan-ledger`/`run-state`/`review-report` based. Hook bundles and monitoring stay out of this first slice.

**Tech Stack:** Python stdlib installer, markdown templates, pytest, existing ForgeFlow validation suite.

---

## Source Review Summary

- `jha0313/harness_framework` provides useful starter docs (`PRD.md`, `ARCHITECTURE.md`, `ADR.md`, `UI_GUIDE.md`) and a simple hook example, but its `stepN.md + scripts/execute.py` runtime uses automatic branch/commit/push behavior that conflicts with ForgeFlow's artifact-first and review-split model.
- `Yeachan-Heo/oh-my-claudecode` provides strong examples of prompt/role visibility and operations surfaces, but ForgeFlow already has adapter presets, hooks, and canonical artifacts. Absorb visibility, not runtime mass.
- First slice: starter docs + richer `docs/forgeflow-team-init.md` + README onboarding docs.

## Non-Goals

- Do not add `stepN.md` or `phases/index.json` as canonical artifacts.
- Do not add auto-commit, auto-push, or headless execution loops.
- Do not install hooks by default.
- Do not add a monitoring script in this PR.
- Do not add external dependencies.

---

### Task 1: Add failing installer tests for starter docs

**Objective:** Prove `--with-starter-docs` creates starter docs and preserves existing docs.

**Files:**
- Modify: `tests/test_agent_preset_install.py`

**Steps:**
1. Add a test that runs `scripts/install_agent_presets.py --with-starter-docs` and asserts these files exist:
   - `docs/PRD.md`
   - `docs/ARCHITECTURE.md`
   - `docs/ADR.md`
   - `docs/UI_GUIDE.md`
2. Assert contents include ForgeFlow-specific question/template language, not raw `{placeholder}` markers.
3. Add a test that pre-creates `docs/PRD.md`, runs installer with `--with-starter-docs`, and asserts the original content is unchanged.
4. Run:
   ```bash
   pytest tests/test_agent_preset_install.py::test_installer_can_generate_starter_docs_without_placeholders tests/test_agent_preset_install.py::test_installer_does_not_overwrite_existing_starter_docs -q
   ```
   Expected: FAIL because CLI option and template copy logic do not exist yet.

### Task 2: Add failing tests for team-init onboarding sections

**Objective:** Prove generated `forgeflow-team-init.md` acts as onboarding/prompt-contract note, not just install log.

**Files:**
- Modify: `tests/test_agent_preset_install.py`

**Steps:**
1. Add assertions after install that `docs/forgeflow-team-init.md` contains:
   - `## Starter docs`
   - `## Active role prompts`
   - `## Review contract`
   - `## Failure handling`
   - `## Recommended first run`
   - `forgeflow-coordinator`
   - `forgeflow-quality-reviewer`
2. For `--with-starter-docs`, assert created starter docs are listed.
3. Run the targeted test and confirm RED.

### Task 3: Create starter doc templates

**Objective:** Add ForgeFlow-native starter docs as source templates.

**Files:**
- Create: `templates/starter-docs/PRD.md`
- Create: `templates/starter-docs/ARCHITECTURE.md`
- Create: `templates/starter-docs/ADR.md`
- Create: `templates/starter-docs/UI_GUIDE.md`

**Template constraints:**
- Question-driven, not placeholder-only.
- Mention ForgeFlow artifacts as downstream consumers where useful.
- No `{프로젝트명}` style raw placeholders.
- No canonical runtime replacement language.

### Task 4: Implement installer option and non-overwrite copy

**Objective:** Make installer support optional starter docs generation.

**Files:**
- Modify: `scripts/install_agent_presets.py`

**Steps:**
1. Add `STARTER_DOCS_ROOT = ROOT / "templates/starter-docs"`.
2. Add `copy_starter_docs(target: Path) -> list[Path]` that copies missing templates into `target/docs/` and skips existing files.
3. Extend `install(..., with_starter_docs: bool = False)` to return created docs.
4. Add CLI flag `--with-starter-docs`.
5. Update CLI output to print created starter doc count when enabled.
6. Run targeted tests from Tasks 1-2 and confirm GREEN.

### Task 5: Enhance team-init note

**Objective:** Include active prompt contracts, review expectations, first-run checklist, and generated starter docs.

**Files:**
- Modify: `scripts/install_agent_presets.py`

**Steps:**
1. Extend `write_doc(...)` signature to accept `starter_docs: list[Path]`.
2. Add sections:
   - Starter docs
   - Active role prompts
   - Review contract
   - Failure handling
   - Recommended first run
3. Keep existing safety boundary and package scripts sections.
4. Run:
   ```bash
   pytest tests/test_agent_preset_install.py -q
   ```

### Task 6: Document the onboarding path

**Objective:** Make README match the actual installer UX.

**Files:**
- Modify: `README.md`

**Steps:**
1. Add a compact section near project-local preset install / repo map describing:
   ```bash
   python3 scripts/install_agent_presets.py --adapter claude --target /path/to/project --profile nextjs --with-starter-docs
   ```
2. Document that starter docs are skipped when existing files are present.
3. State explicitly that this does not install `stepN.md`, auto-commit, or auto-push runtime.

### Task 7: Final verification and commit

**Objective:** Prove the slice is complete and safe.

**Commands:**
```bash
pytest tests/test_agent_preset_install.py -q
make validate
python -m pytest -q
git diff --check
```

**Commit:**
```bash
git add docs/plans/2026-04-24-harness-onboarding-absorption.md scripts/install_agent_presets.py tests/test_agent_preset_install.py templates/starter-docs README.md
git commit -m "feat: add harness onboarding starter docs"
```
