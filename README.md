# ForgeFlow

ForgeFlow is an artifact-first delivery harness for AI coding agents.

It keeps agent work out of vibes-only chat history and pushes it through explicit stages, durable artifacts, gates, and independent review. It is **not** an agent OS, a hosted SaaS runtime, or a prompt zoo.

## At a glance

| Area | What ForgeFlow gives you |
| --- | --- |
| Workflow | clarify → plan when needed → execute → independent review → finalize |
| Evidence | `brief.json`, `run-state.json`, `plan-ledger.json`, `review-report.json`, `eval-record.json` |
| Surfaces | Claude Code plugin, Codex metadata, generated Claude/Codex/Cursor adapters, local runtime |
| Safety | no worker self-approval, schema gates, generated adapter drift checks, release version sync |
| Boundary | local artifact-first harness; not a provider orchestration service |

## Installation

전체 설치 가이드는 [`INSTALL.md`](INSTALL.md)에 있습니다.

### Claude Code plugin

Claude Code는 GitHub repo를 직접 `plugin install` 하는 게 아니라, 먼저 marketplace로 추가한 뒤 그 안의 plugin을 설치합니다.

```text
/plugin marketplace add https://github.com/gimso2x/forgeflow
/plugin install forgeflow
```

설치 후:

```text
/forgeflow:clarify <하고 싶은 작업>
/forgeflow:plan
/forgeflow:run
/forgeflow:review
/forgeflow:ship
```

`/forgeflow`는 전체 설명용 입구입니다. 실제 workflow는 `/forgeflow:clarify`부터 타세요. 짧은 `/review`, `/ship`은 다른 Claude plugin과 충돌할 수 있어 운영용으로 권장하지 않습니다.

CLI에서 검증/설치할 때는 같은 동작을 이렇게 실행할 수 있습니다.

```bash
claude plugin marketplace add https://github.com/gimso2x/forgeflow
claude plugin install forgeflow
```

이미 설치한 사용자가 최신 버전으로 올릴 때는 marketplace cache와 plugin을 둘 다 갱신합니다.

```bash
claude plugin marketplace update forgeflow
claude plugin update forgeflow@forgeflow
claude plugin list
```

`plugin update`가 "already at the latest version"이라고 나오는데 새 slash skill이 반영되지 않으면, repo의 `.claude-plugin/plugin.json` version이 올라갔는지 확인하세요. Claude Code는 plugin version 기준으로 update를 판단합니다.

### Manual adapter install

플러그인 대신 프로젝트에 adapter 파일만 복사해도 됩니다.

```bash
cp adapters/generated/claude/CLAUDE.md /path/to/your-project/CLAUDE.md
cp adapters/generated/codex/CODEX.md /path/to/your-project/CODEX.md
cp adapters/generated/cursor/HARNESS_CURSOR.md /path/to/your-project/HARNESS_CURSOR.md
```

### Project team presets

If you want project-local AI-agent presets for a Next.js app, install the fixed ForgeFlow presets instead of asking the model to invent config files.

Claude:

```bash
python3 scripts/install_agent_presets.py --adapter claude --target /path/to/your-project --profile nextjs
```

Codex:

```bash
python3 scripts/install_agent_presets.py --adapter codex --target /path/to/your-project --profile nextjs
```

Cursor:

```bash
python3 scripts/install_agent_presets.py --adapter cursor --target /path/to/your-project --profile nextjs
```

The legacy Claude wrapper still works:

```bash
python3 scripts/install_claude_agent_presets.py --target /path/to/your-project --profile nextjs
```

This creates adapter-local presets plus a generated team-init note:

```text
/path/to/your-project/.claude/agents/forgeflow-coordinator.md
/path/to/your-project/.claude/agents/forgeflow-nextjs-worker.md
/path/to/your-project/.claude/agents/forgeflow-quality-reviewer.md
/path/to/your-project/.codex/forgeflow/forgeflow-coordinator.md
/path/to/your-project/.codex/forgeflow/forgeflow-nextjs-worker.md
/path/to/your-project/.codex/forgeflow/forgeflow-quality-reviewer.md
/path/to/your-project/.cursor/rules/forgeflow-coordinator.mdc
/path/to/your-project/.cursor/rules/forgeflow-nextjs-worker.mdc
/path/to/your-project/.cursor/rules/forgeflow-quality-reviewer.mdc
/path/to/your-project/docs/forgeflow-team-init.md
```

The installer refuses global config targets such as `~/.claude`, `~/.codex`, `~/.cursor`, direct `.claude/agents`, direct `.codex/forgeflow`, and direct `.cursor/rules`. Team presets belong to the project, not your global agent config. The installer reads `package.json` and documents only scripts that actually exist.

For first-time project onboarding, add starter docs:

```bash
python3 scripts/install_agent_presets.py --adapter claude --target /path/to/your-project --profile nextjs --with-starter-docs
```

This creates missing starter templates without overwriting existing project docs:

```text
/path/to/your-project/docs/PRD.md
/path/to/your-project/docs/ARCHITECTURE.md
/path/to/your-project/docs/ADR.md
/path/to/your-project/docs/UI_GUIDE.md
```

`docs/forgeflow-team-init.md` becomes the quick onboarding note: installed presets, created starter docs, active role prompts, review contract, failure handling, package scripts, and the recommended `/forgeflow:clarify` first run. This intentionally does **not** install `stepN.md`, auto-commit, auto-push, or a second runtime. Those patterns are useful demos in other harnesses, but ForgeFlow keeps the canonical path artifact-first.

Claude projects can opt into a tiny project-local safety bundle:

```bash
python3 scripts/install_agent_presets.py --adapter claude --target /path/to/your-project --profile nextjs --hook-bundles basic-safety
```

`basic-safety` installs `.claude/settings.json` and `.claude/hooks/forgeflow/basic_safety_guard.py` in the target project. It blocks obviously destructive Bash commands such as `rm -rf`, `git reset --hard`, `git push --force`, and `DROP TABLE`. This is a guardrail, not a sandbox. It is Claude-only for now, opt-in only, and the installer refuses to overwrite an existing `.claude/settings.json`.

### Local monitoring summary

ForgeFlow task artifacts are local files, so the first observability layer is just a read-only local summary:

```bash
make setup
make check-env
make monitor-summary
make monitor-summary-json
```

`make monitor-summary` runs the monitor with the repo-managed Python environment against `.forgeflow/tasks`, showing the recent task summary in Markdown. `make monitor-summary-json` uses the same read-only monitor and repo-managed environment for automation-friendly JSON output. Both targets read `run-state.json`, `review-report.json`, `eval-record.json`, and `decision-log.json` when present, then report task counts, blocked/error counts, review rejects, artifact parse errors, and repeated failure messages. They do not mutate artifacts, call an LLM, run tests, send notifications, or start a dashboard. Good. Dashboards reproduce when fed after midnight.

### Local runtime install

```bash
make setup
make check-env
make validate
```

### Updating an existing checkout

```bash
git -C /path/to/forgeflow pull
make -C /path/to/forgeflow setup
make -C /path/to/forgeflow check-env
make -C /path/to/forgeflow validate
```

Use `make -C /path/to/forgeflow ...` so dependency refresh and validation run inside the ForgeFlow checkout regardless of the current shell location. Re-run `setup` before `check-env` and `validate` so a new release adds dependencies without leaving the local runtime stale.

## What ForgeFlow does
- models work as a stage machine
- keeps state in artifacts instead of chat memory
- separates worker and reviewer roles to reduce self-approval
- isolates runtime differences behind generated adapters
- keeps small tasks light and high-risk tasks strict

## How it works

ForgeFlow는 `engineering-discipline`의 좋은 뼈대 — clarification, complexity routing, worker/validator split — 를 가져오되, 여기에 **artifact contract + executable runtime + generated adapters**를 붙인 쪽입니다.

```text
user request
    |
clarify ─── request -> brief + route
    |
    |── small
    |     |
    |     execute ─── worker output + evidence
    |        |
    |     quality-review ─── independent review, no self-approval
    |        |
    |     finalize
    |
    |── medium
    |     |
    |     plan ─── explicit steps + expected artifacts
    |        |
    |     execute ─── worker output + evidence
    |        |
    |     quality-review ─── independent review
    |        |
    |     finalize
    |
    |── large / high-risk
          |
          plan ─── richer plan + risk surface
             |
          execute
             |
          spec-review ─── did we build the right thing?
             |
          quality-review ─── did we build it well enough?
             |
          finalize
             |
          long-run ─── checkpointed retention path
```

You do not need to memorize this. The point is that every stage leaves files behind: `brief.json`, `run-state.json`, `plan-ledger.json`, `review-report.json`, and friends. Chat memory is not the source of truth. Good. Chat memory lies.

## Core workflow
ForgeFlow의 기본 입구는 `/forgeflow:clarify`다. 다만 이건 intake stage라는 뜻이지, 사용자가 stage 명령을 하나하나 대신 운영하라는 뜻은 아니다.

Claude Code plugin으로 설치하면 아래 namespaced slash skill을 바로 쓴다:

1. `/forgeflow:clarify`
2. `/forgeflow:specify` when requirements need to be formalized
3. `/forgeflow:plan`
4. `/forgeflow:run`
5. `/forgeflow:review`
6. `/forgeflow:ship`
7. `/forgeflow:finish` when the branch disposition is needed

`/forgeflow`는 전체 workflow 설명/입구이고, 실제 진행은 `/forgeflow:clarify`, `/forgeflow:plan`, `/forgeflow:run`, `/forgeflow:review`, `/forgeflow:ship`처럼 단계별로 쓰는 게 맞다. `/forgeflow:ship`은 검증·리뷰 evidence를 묶은 final handoff/report 단계이고, branch disposition은 하지 않는다. `/forgeflow:finish`는 그 다음 선택지다: merge, PR, keep, or discard 같은 branch disposition을 explicit user direction으로 결정한다. 짧은 `/review`나 `/ship`은 gstack 같은 다른 Claude plugin skill과 충돌할 수 있으니 운영 문서에서는 namespaced form을 정본으로 둔다.

`/forgeflow:clarify`는 요청을 실행 가능한 brief로 정리하고, 필요한 route를 결정하는 기본 입구다. 요청이 이미 충분히 명확하면 질문을 늘리지 말고 바로 brief/route를 확정해야 한다.

`/forgeflow:plan`은 plan을 만드는 단계다. 여기서 사용자에게 "계획을 세워주세요"라고 되묻는 건 UX 실패다. 사용자는 방향만 주면 되고, task 분해와 verification 설계는 agent 책임이다.

`/forgeflow:run` 직전에도 기본값은 재승인 대기가 아니라 실행 준비 완료다. 같은 scope 안의 repo 작업이면 plan을 다시 허락받느라 멈추지 말고, 범위 변경이나 새 외부 side effect가 생길 때만 멈춘다.

짧게 말하면: `clarify`는 intake, `plan`은 agent-owned decomposition, `run`은 execution이다. 중간에 사용자를 workflow operator처럼 세워두지 않는다.

아무 state도 없는데 operator가 `start`/`run`으로 바로 진입하는 경우는 예외다. 이때만 runtime이 fallback으로 auto routing을 적용할 수 있다. 다만 이건 convenience layer일 뿐이고, workflow 의미론의 본체는 여전히 `clarify-first`다. 핵심은 `clarify를 먼저 생각하라`는 뜻이지 `사용자에게 다음 slash command를 매번 시키라`는 뜻이 아니다.

## Request journey
대충 이렇게 흘러간다.

### Canonical path
`user request -> clarify -> route selection -> execute path -> review path -> finalize`

- `clarify`가 brief와 route를 만든다
- route가 정해지면 해당 complexity path를 따른다
- review는 항상 execution 뒤에 붙고, 필요한 gate를 통과해야 finalize할 수 있다

### Operator fallback path
`operator start/run -> persisted state reuse or auto-route -> same canonical stages`

- direct CLI 진입은 우회 경로다
- state가 있으면 기존 route/state를 재사용한다
- state가 없으면 brief/checkpoint 기준으로 auto routing을 시도한다
- 그래도 실제 stage 진행 순서는 canonical policy를 벗어나지 않는다

## Complexity routing
fallback auto routing이 route를 고르면 canonical policy는 아래 순서를 따른다.

- **small** → `clarify -> execute -> quality-review -> finalize`
- **medium** → `clarify -> plan -> execute -> quality-review -> finalize`
- **large/high-risk** → `clarify -> plan -> execute -> spec-review -> quality-review -> finalize -> long-run`

## Review model
ForgeFlow는 review를 형식적인 승인 단계로 취급하지 않는다. `spec-review`와 `quality-review`는 서로 다른 질문을 던지고, worker 자기보고는 승인 근거로 취급하지 않는다.

- overview: `docs/review-model.md`
- workflow semantics: `docs/workflow.md`
- long-run retention: `docs/long-run-model.md`
- review-summary decision: `docs/review-summary-decision.md`
- machine contracts: `schemas/review-report.schema.json`

## Why this exists
Most agent repos do at least one of these badly:
- treat chat history as state
- let the implementer implicitly approve their own work
- copy host-specific rules everywhere
- grow into a weird little religion

ForgeFlow tries not to do that.

## Repo map
- `docs/` — human-readable design docs, including `docs/evolution-model.md` for the global advisory/project-local enforcement contract
- `policy/canonical/` — workflow semantics, gates, review order, routing, global-advisory/project-enforced self-evolution policy
- `examples/evolution/` — deterministic project-local HARD rule examples; validated against the canonical evolution policy
- `scripts/forgeflow_evolution.py inspect` / `list` / `adopt` / `dry-run --rule <id>` / gated `execute --rule <id>` / `retire --rule <id> --reason <why>` / `restore --rule <id> --reason <why>` / `doctor` / `effectiveness --rule <id>` / `promotion-plan --rule <id> [--write]` / `proposal-review --proposal <path>` / `proposal-approve --proposal <path> --approval <approval> --approver <name> --reason <why>` / `proposal-approvals --proposal <path>` / `promotion-gate --proposal <path>` / `promotion-decision --proposal <path> --decision approve_policy_gate --decider <name> --reason <why> [--write]` / `promotion-ready --proposal <path>` / `promote --proposal <path> --i-understand-this-mutates-project-policy` / `promotions` / `audit` — evolution policy/runtime-safety summaries, explicitly acknowledged project-local rule execution, lifecycle retirement/restoration, read-only health/effectiveness/promotion-planning checks, optional proposal persistence/review, append-only approval ledger, promotion marker listing, and audit inspection
- `schemas/` — artifact contracts
- `prompts/canonical/` — canonical role prompts
- `adapters/targets/` — target manifests
- `adapters/generated/` — generated runtime surfaces
- `runtime/` — scaffold-level runtime surfaces for orchestrator, ledger, gates, recovery
- `forgeflow_runtime/` — executable Python runtime implementation used by the local CLI
- `memory/` — inspectable local memory scaffold for reusable patterns and decisions
- `examples/artifacts/` — sample artifact fixtures
- `scripts/` — validation and generation utilities

## Quickstart

Start here if you just cloned the repo and want to know whether it works.

### 1. Set up dependencies

```bash
make setup
make check-env
```

This creates or reuses `.venv`, installs the minimal Python dependencies from `requirements.txt`, and prints actionable missing dependency errors before validation. No hidden local environment is assumed.

### 2. Validate the harness

```bash
make validate
```

Expected result: structure, policy, generated adapters, sample artifacts, and adherence evals all pass.

### 3. Smoke-test the installed Claude plugin

If Claude Code and the ForgeFlow plugin are installed, run the live slash-skill smoke test:

```bash
make smoke-claude-plugin
```

This calls `/forgeflow:<stage>` through Claude Code, checks `permission_denials == []`, rejects exact-count preambles/code fences, validates write-mode `plan.json` and `review-report.json` against schema, and fails if the repo dirty state changes. This is intentionally not part of `make validate` because it spends Claude quota and requires a logged-in Claude CLI.

### 4. Inspect the operator shell

```bash
make setup
make check-env
make orchestrator-help
```

`make orchestrator-help` shows the local CLI surface for `start`, `run`, `status`, `resume`, `advance`, `retry`, `step-back`, `escalate`, and `execute` through the repo-managed Python environment.

### 5. Run the safe sample

```bash
make setup
make check-env
make runtime-sample
```

`make runtime-sample` uses the repo-managed Python environment to copy the fixture to a disposable workspace before running, so tracked sample artifacts stay clean.

### 6. Start your own task

```bash
python3 scripts/run_orchestrator.py init \
  --task-id my-task-001 \
  --objective "Update README quickstart" \
  --risk low
```

By default this writes task artifacts under the **current project**:

```text
./.forgeflow/tasks/my-task-001/brief.json
./.forgeflow/tasks/my-task-001/run-state.json
./.forgeflow/tasks/my-task-001/checkpoint.json
./.forgeflow/tasks/my-task-001/session-state.json
```

Use `--task-dir` only when you intentionally want a custom artifact directory:

```bash
python3 scripts/run_orchestrator.py init \
  --task-dir work/my-task \
  --task-id my-task-001 \
  --objective "Update README quickstart" \
  --risk low
```

This creates schema-valid starter artifacts and leaves the task at `clarify`.

### 7. Inspect the fixture state

```bash
make setup
make check-env
make orchestrator-status
```

Read-only status inspection is repo-managed through `make orchestrator-status`. Other manual `run_orchestrator.py` commands mutate their target `--task-dir`; use `run_runtime_sample.py` for demos unless mutation is intentional.

### 8. Use an adapter in another project

```bash
cp adapters/generated/codex/CODEX.md /path/to/your-project/CODEX.md
cp adapters/generated/claude/CLAUDE.md /path/to/your-project/CLAUDE.md
```

Generated adapters carry ForgeFlow semantics into a host agent. Do not hand-edit generated adapter files; change canonical policy/docs/prompts and regenerate instead.


## Operator shell
권장 경로는 `clarify`부터 brief와 route를 만든 뒤 진행하는 것이다. local runtime을 직접 만지는 표면은 operator fallback일 뿐이다.

```bash
make setup
make check-env
make orchestrator-help
make runtime-sample
make orchestrator-status
python3 scripts/run_orchestrator.py execute --task-dir examples/runtime-fixtures/small-doc-task --route small --adapter codex
python3 scripts/run_orchestrator.py execute --task-dir examples/runtime-fixtures/small-doc-task --route small --adapter claude --real
python3 scripts/run_orchestrator.py run --task-dir examples/runtime-fixtures/small-doc-task --min-route medium
python3 scripts/run_orchestrator.py advance --task-dir examples/runtime-fixtures/small-doc-task --route small --current-stage clarify --execute --adapter cursor
```

Full operator examples live in `docs/operator-shell.md`. `run_runtime_sample.py`는 fixture를 임시 workspace로 복사한 뒤 실행해서 샘플 명령만으로 tracked runtime fixture가 dirty 상태가 되지 않게 막는다. manual `run_orchestrator.py` 명령은 대상 `--task-dir`를 실제로 변경하므로 demo에는 disposable sample runner를 쓰는 게 맞다.

이 CLI는 local artifact 디렉터리를 기준으로 route 실행과 recovery helper를 노출한다. `run`은 artifact/gate 기준으로 route 상태를 진행하는 orchestration 명령이다. `run`/`start`는 operator fallback surface라서, route를 명시하지 않으면 persisted state를 재사용하거나 brief/checkpoint 기준으로 auto routing을 시도한다. 그래도 workflow의 정본은 여전히 `clarify-first`다. `execute`는 현재 stage를 어댑터로 실행한다. 기본 실행은 안전한 stub이고, 실제 CLI 호출은 `--real`을 붙인 경우에만 탄다. 결과 payload의 `execution_mode`로 `stub`/`real`을 확인해야 한다. `advance --execute`는 다음 stage로 넘긴 뒤 바로 실행까지 붙이되, 실행이 실패하면 stage pointer를 커밋하지 않는다. medium/large route에서는 `advance`/`run` 모두 `plan-ledger.json`이 있어야 하고, `step-back`은 되감는 stage에 해당하는 review approval/evidence만 지운다. 정책 위반이나 잘못된 route가 들어오면 traceback 대신 `ERROR:` 형식의 명시적 runtime 오류를 반환한다.

## Using ForgeFlow in Codex
Codex에서는 repo 루트의 `CODEX.md`가 지속 표면이다. generated adapter를 그대로 복사해서 쓰고, 프로젝트별 보조 규칙은 별도 문서에 두는 게 맞다. generated 파일을 손으로 덕지덕지 고치기 시작하면 다음 regenerate 때 다시 개판 난다.

```bash
cp adapters/generated/codex/CODEX.md ./CODEX.md
codex exec "Read CODEX.md first, then summarize the ForgeFlow stage order in one sentence."
codex exec "Use ForgeFlow rules. Inspect examples/runtime-fixtures/small-doc-task and explain which artifacts gate finalize."
```

권장 흐름:
- ForgeFlow semantics는 `CODEX.md`에서 고정한다.
- 실제 작업 지시는 issue/brief/plan artifact와 함께 Codex prompt로 넘긴다.
- route 실행 검증은 `python3 scripts/run_orchestrator.py ... --adapter codex`로 따로 확인한다. 실제 Codex CLI를 호출하려면 `--real`을 붙이고, payload의 `execution_mode`가 `real`인지 본다.

## Using ForgeFlow in Claude Code
Claude Code에서는 repo 루트의 `CLAUDE.md`가 지속 표면이다. 이것도 똑같이 generated adapter를 복사해서 쓴다. Claude용 팁을 추가하고 싶으면 README나 별도 docs에 쓰지, canonical semantics를 `CLAUDE.md`에서 멋대로 바꾸면 안 된다.

```bash
cp adapters/generated/claude/CLAUDE.md ./CLAUDE.md
claude -p "Read CLAUDE.md first, then reply with the ForgeFlow review order."
claude -p "Use ForgeFlow rules. Inspect examples/runtime-fixtures/small-doc-task and explain why worker self-report is not enough for finalize."
```

권장 흐름:
- Claude는 `CLAUDE.md`로 stage/gate semantics를 읽는다.
- 실제 구현 요청은 brief와 artifact 경로를 함께 준다.
- local runtime 쪽 동작은 `python3 scripts/run_orchestrator.py ... --adapter claude`처럼 adapter 이름을 명시해서 검증한다. 실제 Claude Code를 호출하려면 `--real`을 붙이고, payload의 `execution_mode`가 `real`인지 본다.

## Real CLI smoke tests on this repo
아래 정도는 최소한 직접 돌려보고 "된다"고 말할 수 있다.

```bash
codex login status
script -qc "claude -p 'Reply with exactly: CLAUDE_OK'" /dev/null
python3 scripts/run_orchestrator.py execute --task-dir examples/runtime-fixtures/small-doc-task --route small --adapter codex --real
python3 scripts/run_orchestrator.py execute --task-dir examples/runtime-fixtures/small-doc-task --route small --adapter claude --real
```

이 저장소에서 실제로 검증할 때는, generated adapter를 temp git repo에 복사한 뒤 한 줄짜리 확인 프롬프트를 던져서 Codex/Claude가 instruction file을 읽는지 먼저 보는 게 제일 덜 멍청하다.

## Claude Code prompt templates
아래는 그냥 복붙해서 시작하면 된다. 핵심은 항상 `Read CLAUDE.md first`로 시작하고, route/stage/artifact/gate를 명시하는 것이다.

### Small task template
```bash
claude -p '
Read CLAUDE.md first.

Task:
- <what to change>
- <scope boundary>

Follow ForgeFlow.
Treat this as a small route task.
State the route you are using.
Briefly clarify the task.
Then execute.
Do not treat your own summary as sufficient evidence for finalize.
List what evidence or artifacts justify quality-review and finalize.
'
```

### Medium task template
```bash
claude -p '
Read CLAUDE.md first.

Task:
- <what to build or change>
- <constraints>
- <acceptance criteria>

Follow ForgeFlow.
Treat this as a medium route task.
State the route you are using.
Start with clarify, then produce a plan.
The plan must include explicit steps, expected outputs, and verification.
Do not jump straight into implementation.
After the plan, describe what artifacts must exist before execute and finalize.
'
```

### Large / high-risk task template
```bash
claude -p '
Read CLAUDE.md first.

Task:
- <high-risk change>
- <constraints>
- <acceptance criteria>
- <risk notes>

Follow ForgeFlow.
Treat this as a large/high-risk route task.
State the route you are using.
Start with clarify, then plan, then execute.
Do not merge spec-review and quality-review.
Do not claim finalize unless the required review artifacts and evidence exist.
Call out residual risk explicitly before long-run or finalize.
'
```

복붙 후 바로 바꿔야 하는 자리:
- `<what to change>` / `<what to build or change>` / `<high-risk change>`
- `<scope boundary>`
- `<constraints>`
- `<acceptance criteria>`
- `<risk notes>`

추천 습관:
- 작은 작업도 Claude가 먼저 route를 말하게 한다.
- medium 이상은 plan 없이 바로 코딩시키지 않는다.
- high-risk 작업은 review artifact와 residual risk를 꼭 따로 적게 한다.

## Current status
This repo is a **P0 seed**.
It already includes:
- design docs
- canonical policy files
- JSON schemas for core artifacts
- generated adapters for Claude / Codex / Cursor
- target-specific installation guidance captured in manifest metadata and rendered into generated adapters
- validation scripts
- sample artifact fixtures

It now includes a **minimal local runtime orchestrator CLI** for artifact-directory execution plus the explicit `runtime/` and `memory/` scaffold surfaces promised by the design docs.
The local runtime resumes from validated checkpoints, using `run-state.json` for stage position and `plan-ledger.json` as the gate/retry/task-progress truth source on medium/large routes.
It still does **not** include provider-specific integrations or a full hosted runtime.
That boundary is deliberate.

## Design lineage
ForgeFlow borrows its best bones from four places:
- `engineering-discipline` — workflow skeleton, complexity routing, worker/validator split
- `hoyeon` — artifact contracts, schema discipline, bounded recovery
- `gstack` — canonical policy → generated adapters
- `superpowers` — adversarial review, spec-review before quality-review

## Validation
For a fresh clone, run the setup gate first so validation uses the repo-managed dependency set:

```bash
make setup
make check-env
make validate
```

This runs:
- structure validation
- policy validation
- generated adapter validation
- JSON Schema sample artifact validation for positive and negative fixtures
- executable adherence evals across small/medium/large and negative runtime fixtures

## Sharp edges worth checking

Before a release or bigger refactor, check these first:

1. **Plugin version drift** — `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and `.claude-plugin/marketplace.json` must agree. Use `scripts/check_plugin_versions.py`; do not hand-wave this.
2. **Generated adapter drift** — canonical policy, prompts, schemas, and target manifests must be regenerated and validated, or Claude/Codex/Cursor docs silently diverge.
3. **README/INSTALL contract drift** — tests intentionally pin key install and runtime phrases. If the docs get “prettier” by deleting operational anchors, validation will slap you. Good.
4. **Live plugin drift** — `make validate` is deterministic, but `make smoke-claude-plugin` depends on Claude CLI auth/quota/cache and can fail independently.
5. **Runtime stage drift** — `run`, `execute`, and `advance --execute` have different mutation semantics. Refactor these only with runtime tests beside you.
6. **Artifact compatibility** — stricter schemas can break old on-disk task artifacts unless migration or intentional rejection is covered.
7. **Legacy numbered skills** — old `skills/01-*` style docs still need quarantine/decision work; keep that as a follow-up, not a drive-by cleanup.

## Naming
The name is **ForgeFlow** because the point is to forge messy agent work into a flow with gates, evidence, and review.
Not because everything needs a dramatic fantasy backstory.
