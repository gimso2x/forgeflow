# ForgeFlow

ForgeFlow is an artifact-first delivery harness for AI coding agents.

It is **not** an agent OS and it is **not** a prompt zoo.
It is a repo seed for running work through explicit stages, artifacts, gates, and independent review.

## What ForgeFlow does
- models work as a stage machine
- keeps state in artifacts instead of chat memory
- separates worker and reviewer roles to reduce self-approval
- isolates runtime differences behind generated adapters
- keeps small tasks light and high-risk tasks strict

## Core workflow
1. `clarify`
2. `plan`
3. `execute`
4. `spec-review`
5. `quality-review`
6. `finalize`
7. `long-run`

## Complexity routing
- **small** → `clarify -> execute -> quality-review -> finalize`
- **medium** → `clarify -> plan -> execute -> quality-review -> finalize`
- **large/high-risk** → `clarify -> plan -> execute -> spec-review -> quality-review -> finalize -> long-run`

## Why this exists
Most agent repos do at least one of these badly:
- treat chat history as state
- let the implementer implicitly approve their own work
- copy host-specific rules everywhere
- grow into a weird little religion

ForgeFlow tries not to do that.

## Repo map
- `docs/` — human-readable design docs
- `policy/canonical/` — workflow semantics, gates, review order, routing
- `schemas/` — artifact contracts
- `prompts/canonical/` — canonical role prompts
- `adapters/targets/` — target manifests
- `adapters/generated/` — generated runtime surfaces
- `runtime/` — scaffold-level runtime surfaces for orchestrator, ledger, gates, recovery
- `forgeflow_runtime/` — executable Python runtime implementation used by the local CLI
- `memory/` — inspectable local memory scaffold for reusable patterns and decisions
- `examples/artifacts/` — sample artifact fixtures
- `scripts/` — validation and generation utilities

## Quick start
```bash
make validate
make adherence-evals
make generate
make regen
make runtime-sample
```

## Runtime sample
```bash
python3 scripts/run_runtime_sample.py --fixture-dir examples/runtime-fixtures/small-doc-task --route small
python3 scripts/run_orchestrator.py execute --task-dir examples/runtime-fixtures/small-doc-task --route small --adapter codex
python3 scripts/run_orchestrator.py advance --task-dir examples/runtime-fixtures/small-doc-task --route small --current-stage clarify
python3 scripts/run_orchestrator.py advance --task-dir examples/runtime-fixtures/small-doc-task --route small --current-stage clarify --execute --adapter cursor
python3 scripts/run_orchestrator.py retry --task-dir examples/runtime-fixtures/small-doc-task --stage execute --max-retries 2
python3 scripts/run_orchestrator.py step-back --task-dir examples/runtime-fixtures/small-doc-task --route small --current-stage quality-review
python3 scripts/run_orchestrator.py escalate --task-dir examples/runtime-fixtures/small-doc-task --from-route small
```

`run_runtime_sample.py`는 fixture를 임시 workspace로 복사한 뒤 실행해서 샘플 명령만으로 tracked runtime fixture가 dirty 상태가 되지 않게 막는다. 실행 결과에는 원본 fixture 경로만 다시 싣고, 임시 workspace 경로는 노출하지 않는다. manual `execute`/`advance`/`retry` 예시는 여전히 원본 task-dir를 직접 대상으로 삼지만, `run` 샘플은 disposable copy에서만 돈다.

이 CLI는 local artifact 디렉터리를 기준으로 route 실행과 recovery helper를 노출한다. `run`은 artifact/gate 기준으로 route 상태를 진행하는 orchestration 명령이고, `execute`는 현재 stage를 어댑터로 실행한다. `advance --execute`는 다음 stage로 넘긴 뒤 바로 실행까지 붙이되, 실행이 실패하면 stage pointer를 커밋하지 않는다. medium/large route에서는 `advance`/`run` 모두 `plan-ledger.json`이 있어야 하고, `step-back`은 되감는 stage에 해당하는 review approval/evidence만 지운다. 정책 위반이나 잘못된 route가 들어오면 traceback 대신 `ERROR:` 형식의 명시적 runtime 오류를 반환한다.

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
- route 실행 검증은 `python3 scripts/run_orchestrator.py ... --adapter codex`로 따로 확인한다.

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
- local runtime 쪽 동작은 `python3 scripts/run_orchestrator.py ... --adapter claude`처럼 adapter 이름을 명시해서 검증한다.

## Real CLI smoke tests on this repo
아래 정도는 최소한 직접 돌려보고 "된다"고 말할 수 있다.

```bash
codex login status
script -qc "claude -p 'Reply with exactly: CLAUDE_OK'" /dev/null
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
```bash
make validate
```

This runs:
- structure validation
- policy validation
- generated adapter validation
- JSON Schema sample artifact validation for positive and negative fixtures
- executable adherence evals across small/medium/large and negative runtime fixtures

## Naming
The name is **ForgeFlow** because the point is to forge messy agent work into a flow with gates, evidence, and review.
Not because everything needs a dramatic fantasy backstory.
