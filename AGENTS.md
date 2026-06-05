# ForgeFlow — AGENTS.md

> AI coding agent instructions for developing or modifying this repo.

## Project

ForgeFlow: artifact-first delivery workflow for AI coding agents.
Markdown-only distribution — no runtime, no external deps. **slim, markdown-only distribution.** Do not assume the older `forgeflow_runtime/`, `schemas/`, or `tests/` trees exist — use `make validate` as the contract surface. Skills are pure Markdown (SKILL.md + YAML frontmatter), templates are Markdown artifacts.
Supports Claude Code, Codex, Gemini CLI, Cursor as adapters.

- **Version**: `VERSION` 파일이 단일 소스 (currently `1.14.0`)
- **Entry point**: `skills/forgeflow/SKILL.md` (canonical contract); root `SKILL.md` is marketplace summary only
- **Adapter config**: `docs/adapter-config.md`

## Commands

```bash
make validate              # Full contract validation (34 checks)
make validate-<target>     # Focused: -skills, -templates, -evals, -versions, -changelog-links, etc.
make demo                  # First-run workspace demo
```

No build, no test suite. Validation is the test surface — `scripts/validate_*.py` enforces markdown contract integrity.

## Architecture

```
skills/
  forgeflow/               # Main router — routes, model tiers, worktree spec, stage boundaries
  clarify/                  # Requirements → brief.md + route selection + Goal Contract
  ff-plan/                  # Plan → plan.md + Self-Critique loop (max 3 iterations)
  execute/                  # Implementation → implementation-notes.md + small-route self-verify
    references/             # Subagent prompts (implementer, quality/spec reviewer, testing)
  ff-review/                # Independent review → review-report.md + Blocker Enforcement Rule
  ship/                     # Ship + branch cleanup + model tier verification floor
  long-run/                 # Learning → eval-record.md
  ff-config/                # Project defaults (auto/isolation toggles)
  benchmark/                # Cross-adapter benchmarks
  _shared/                  # discipline.md, preflight.md, isolation.md, automation.md, context-resume.md
templates/                  # 27 artifact templates (brief, plan, review-report, ship-summary, etc.)
evals/                      # 120 eval cases (evals.json + fixture files)
scripts/                    # validate_*.py validators + telemetry/evolution helpers
docs/                       # adapter-config.md, stage-tool-boundaries.md, roadmap-improvements.md
.claude-plugin/             # Claude Code plugin config
.codex-plugin/              # Codex plugin config
.cursor-plugin/             # Cursor plugin config
.claude/skills/release.md   # Release skill (Claude Code only, not in public inventory)
GEMINI.md                   # Gemini CLI adapter
gemini-extension.json       # Gemini extension manifest
```

## Key Design Patterns (v1.11+)

- **Route model**: small (3-stage: clarify→execute→ship with self-verify), medium (5-stage), high/epic (6-stage with long-run)
- **Goal Contract** (`templates/brief.md`): 4 fields (Success Criteria, Evidence Required, Accepted Risks, Explicit Exclusions) — review uses these as PASS/FAIL contract
- **Self-Critique Loop** (`skills/ff-plan/`): plan.md gets 4-question critic pass, max 3 iterations, recorded in plan.md Self-Critique section
- **Blocker Enforcement Rule**: `approved` verdict only when Open Blockers is empty; no "minor blocker" category
- **Model Tiers**: reasoning/coding/fast per stage — adapters map tiers to concrete models
- **Worktree isolation**: fan-out workers each get isolated git worktree; pre-merge verification gate (5 items); `--no-ff` merge required for fan-in
- **Small route self-verify** (`skills/execute/`): 5-item checklist before exit (Goal Contract check, scope boundary, self-review proxy, verification gate, evidence completeness)

## Development Workflow

1. Edit `skills/<name>/SKILL.md` (canonical contract changes → `skills/forgeflow/SKILL.md` first)
2. Edit `templates/<name>.md` for artifact format changes
3. Update `docs/adapter-config.md` for adapter-specific behavior
4. Sync plugin configs: `.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `GEMINI.md`
5. Run `make validate` — all 34 checks must pass
6. Release: bump `VERSION`, update `CHANGELOG.md` (impact-axis format: 🔒🔍⚡👤), sync manifest version fields, commit via `.claude/skills/release.md`

## Code Conventions

- All artifacts are Markdown; templates live in `templates/`
- Public skills start with YAML frontmatter: `name`, `description`, `version`, `validate_prompt`. Skill `version`은 릴리즈 `VERSION`과 별개
- Version sync: release commit must align `VERSION` with `SKILL.md`, `.claude-plugin/*.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `gemini-extension.json` version fields
- Artifact storage: default `~/.forgeflow/projects/<project-slug>/tasks/<task-id>/`; local-only if explicitly configured
- Review is read-only — never edits code
- Verification uses real commands only — no hallucinated commands
- 외부 의존성 추가 금지
- Review는 읽기 전용 — 코드 수정 금지
- CHANGELOG Unreleased sections use impact axes (🔒 자동화·정합성 / 🔍 검증·정책 / ⚡ 속도·안정성 / 👤 사용자·경험)
- Prompt-driven enforcement: gates and rules enforced via prompts, not scripts

## Maintainer / Autonomous Preflight

1. `git branch --show-current` + `git status --short --branch` — stop if not target branch or if dirty paths exist from prior work
2. `git pull --ff-only`, re-read `AGENTS.md`, recheck status
3. Stage only intentional files with explicit paths — never `git add -A`
4. Do not schedule jobs, modify cron, or change external automation

## Notes

<!-- Quick-add area -->
