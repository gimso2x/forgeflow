# ForgeFlow

ForgeFlow는 AI coding agent 작업을 채팅 기억이 아니라 **명시적인 stage, 로컬 artifact, gate, evidence, 독립 review**로 진행하게 만드는 artifact-first delivery harness입니다. Claude Code와 Codex에서 같은 workflow를 쓰도록 돕고, 작은 수정은 가볍게, 리스크 있는 작업은 계획과 검증을 남기게 합니다.

## How it works

ForgeFlow는 agent가 바로 코드를 고치기 전에 요청을 실행 가능한 작업으로 정리하게 합니다. 작업 크기와 위험도를 보고 route를 고른 뒤, 필요한 만큼 계획을 만들고, 실행 결과를 artifact로 남기고, 독립 review를 거쳐 마무리합니다.

기본 흐름은 하나입니다.

```text
user request
  -> clarify
  -> plan/specify when needed
  -> run
  -> review
  -> ship/finish
```

이 흐름은 사용자가 stage 명령을 하나하나 대신 운영하라는 뜻은 아니다. "계획을 세워주세요" 같은 요청은 agent-owned decomposition으로 받아서 agent가 다음 단계와 artifact를 정리해야 합니다. 다만 stage 경계를 넘을 때는 닫힌 질문으로 멈춘다: `다음 스텝으로 /forgeflow:run을 진행하시겠습니까? (y/n)`.

## Installation

ForgeFlow는 보통 Claude Code plugin이나 Codex plugin으로 설치해서 씁니다. No hidden local environment is assumed.

수동 adapter 복사, local runtime, maintainer 검증, Windows wrapper 같은 자세한 절차는 [INSTALL.md](INSTALL.md)를 보세요.
Native Windows PowerShell에서 local runtime까지 검증할 때는 [docs/windows.md](docs/windows.md)의 wrapper 흐름을 사용하세요.

```powershell
.\scripts\setup.ps1
.\scripts\validate.ps1
.\scripts\run_orchestrator.ps1 init --task-id my-task-001 --objective "Update README quickstart" --risk low
```

### 1. Set up dependencies

```bash
make setup
```

### 2. Check environment

```bash
make check-env
```

### 3. Validate

```bash
make validate
```

### 4. Inspect the operator shell

```bash
make setup
make check-env
make orchestrator-help
```

### 5. Run the safe sample

```bash
make setup
make check-env
make runtime-sample
```

### 6. Start your own task

```bash
python3 scripts/run_orchestrator.py init \
  --task-id my-task-001 \
  --objective "Update README quickstart" \
  --risk low
```

Other manual `run_orchestrator.py` commands mutate their target `--task-dir`. Make targets are read-only where noted.

### 7. Inspect the fixture state

```bash
make setup
make check-env
make orchestrator-status
```

### 8. Use an adapter

```bash
cp adapters/generated/claude/CLAUDE.md /path/to/your-project/CLAUDE.md
cp adapters/generated/codex/CODEX.md /path/to/your-project/CODEX.md
```

### Claude Code Plugin

Claude Code에서는 ForgeFlow marketplace를 추가한 뒤 plugin을 설치합니다.

```text
/plugin marketplace add https://github.com/gimso2x/forgeflow
/plugin install forgeflow
```

터미널에서 설치할 때는 같은 작업을 Claude CLI로 실행할 수 있습니다.

```bash
claude plugin marketplace add https://github.com/gimso2x/forgeflow
claude plugin install forgeflow
```

설치 후에는 namespaced slash skill로 시작합니다.

```text
/forgeflow:clarify <하고 싶은 작업>
/forgeflow:plan
/forgeflow:run
/forgeflow:review
/forgeflow:ship
/forgeflow:finish
```

`/review`, `/ship` 같은 짧은 이름은 다른 plugin과 충돌할 수 있으므로 `/forgeflow:<stage>` 형식을 권장합니다.

### Codex Plugin

Codex에서는 local plugin marketplace에 ForgeFlow를 등록한 뒤 Codex Desktop에서 install/enable합니다.

```bash
curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - -- --force
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python -
```

설치 후 Codex Desktop을 재시작하고 local marketplace에서 ForgeFlow를 enable합니다. 그 다음 Claude와 같은 slash-style prompt로 사용합니다.

```text
/forgeflow:clarify <하고 싶은 작업>
/forgeflow:plan
/forgeflow:run
/forgeflow:review
/forgeflow:ship
/forgeflow:finish
```

Codex plugin, `CODEX.md`, project preset의 차이는 [docs/codex-desktop.md](docs/codex-desktop.md)에 정리되어 있습니다.

### Manual adapter install

generated adapter만 복사하려면:

```bash
cp adapters/generated/codex/CODEX.md /path/to/your-project/CODEX.md
```

Claude Code를 수동 adapter 방식으로 쓰려면:

```bash
cp adapters/generated/claude/CLAUDE.md /path/to/your-project/CLAUDE.md
```

### Project team presets

Next.js 프로젝트에는 project-local preset을 설치할 수 있습니다.

```bash
python3 scripts/install_agent_presets.py --adapter claude --target /path/to/your-project --profile nextjs
python3 scripts/install_agent_presets.py --adapter codex --target /path/to/your-project --profile nextjs
python3 scripts/install_claude_agent_presets.py --target /path/to/your-project --profile nextjs
```

설치되는 파일:

- `.claude/agents/forgeflow-coordinator.md`
- `.codex/forgeflow/forgeflow-coordinator.md`
- `.codex/rules/forgeflow-nextjs-worker.mdc`

The installer reads `package.json` and documents only scripts that actually exist.

### Local runtime install

로컬 runtime으로 ForgeFlow를 실행하려면 저장소를 clone한 뒤 setup합니다.

```bash
git clone https://github.com/gimso2x/forgeflow.git /path/to/forgeflow
cd /path/to/your-project
make -C /path/to/forgeflow setup
make -C /path/to/forgeflow check-env
```

### Local monitoring summary

```bash
make setup
make check-env
make monitor-summary
make monitor-summary-json
```

### Updating an existing checkout

```bash
git -C /path/to/forgeflow pull
make -C /path/to/forgeflow setup
make -C /path/to/forgeflow check-env
make -C /path/to/forgeflow validate
```

Commands use `-C` so they work regardless of current shell location. Run this after every pull, especially when a new release adds dependencies.

Claude/Codex plugin cache 안에서 `/forgeflow:init`이 실행되면 ForgeFlow는 cache 아래에 `.forgeflow/tasks/...`를 만들지 않고 실패해야 합니다. 이 경우 traceback 없이 `ERROR:`로 끝나야 하며, 일반 프로젝트 경로에 `plugin/marketplace` 같은 이름이 들어간 것만으로 막으면 안 됩니다.

```bash
python3 scripts/run_orchestrator.py init \
  --task-dir /path/to/your-project/.forgeflow/tasks/<task-id> \
  --task-id <task-id> \
  --objective "<objective>" \
  --risk low
```

Maintainer verification before release or plugin update:

```bash
make validate
make smoke-claude-plugin
```

`make smoke-claude-plugin`은 writes starter artifacts through `/forgeflow:init` 경로도 검증합니다.

## Quickstart

처음 설치했다면 위 Installation 섹션의 numbered steps를 따르세요.

## Operator shell

운영자 CLI 표면을 확인하려면:

```bash
make setup
make check-env
make runtime-sample
make orchestrator-help
make orchestrator-status
python3 scripts/run_orchestrator.py execute --task-dir examples/runtime-fixtures/small-doc-task --route small --adapter codex
python3 scripts/run_orchestrator.py execute --task-dir examples/runtime-fixtures/small-doc-task --route small --adapter claude --real
python3 scripts/run_orchestrator.py run --task-dir examples/runtime-fixtures/small-doc-task --min-route medium
python3 scripts/run_orchestrator.py advance --task-dir examples/runtime-fixtures/small-doc-task --route small --current-stage clarify --execute --adapter codex
```

이 CLI는 local artifact 디렉터리를 기준으로 route 실행과 recovery helper를 노출한다. `run`은 artifact/gate 기준으로 route 상태를 진행하는 orchestration 명령이다. `execute`는 현재 stage를 어댑터로 실행한다. `advance --execute`는 다음 stage로 넘긴 뒤 바로 실행까지 붙인다.

## Using ForgeFlow in Codex

Codex에서는 repo 루트의 `CODEX.md`가 지속 표면이다. generated adapter를 복사해서 쓴다.

```bash
cp adapters/generated/codex/CODEX.md ./CODEX.md
codex exec "Read CODEX.md first, then summarize the ForgeFlow stage order in one sentence."
```

## Using ForgeFlow in Claude Code

Claude Code에서는 repo 루트의 `CLAUDE.md`가 지속 표면이다.

```bash
cp adapters/generated/claude/CLAUDE.md ./CLAUDE.md
claude -p "Read CLAUDE.md first, then reply with the ForgeFlow review order."
```

## Claude Code prompt templates

### Small task template

```bash
claude -p '
Read CLAUDE.md first.
Task: <what to change>
Follow ForgeFlow. Treat this as a small route task.
State the route you are using.
'
```

### Medium task template

```bash
claude -p '
Read CLAUDE.md first.
Task: <what to build or change>
Follow ForgeFlow. Treat this as a medium route task.
State the route you are using.
Start with clarify, then produce a plan.
'
```

### Large / high-risk task template

```bash
claude -p '
Read CLAUDE.md first.
Task: <high-risk change>
Follow ForgeFlow. Treat this as a large/high-risk route task.
State the route you are using.
Start with clarify, then plan, then execute.
Do not merge spec-review and quality-review.
'
```

## What ForgeFlow does

- Claude Code plugin metadata and skills
- Codex plugin metadata and skills
- Generated Claude/Codex adapter instructions
- Canonical workflow policy and JSON schemas
- Local validation, sample fixtures, and runtime support tools

ForgeFlow는 hosted agent service나 SaaS runtime이 아닙니다. agent가 로컬 프로젝트에서 더 예측 가능하게 일하도록 만드는 workflow 규약과 검증 도구입니다.

## The Basic Workflow

1. `clarify` - 요청을 목표, 제약, 성공 조건, route로 정리합니다.
2. `plan` / `specify` - medium 이상이거나 모호한 작업을 실행 가능한 계획으로 쪼갭니다.
3. `run` - 승인된 brief와 plan 범위 안에서 작업합니다.
4. `review` - 결과를 evidence와 artifact 기준으로 독립 검토합니다.
5. `ship` / `finish` - handoff를 정리하고, 필요하면 PR/merge/keep/discard 같은 branch 결정을 다룹니다.

작업 중 생성되는 대표 artifact는 `brief.json`, `plan-ledger.json`, `run-state.json`, `review-report.json`입니다. 세부 contract는 [docs/artifact-model.md](docs/artifact-model.md)와 [docs/review-model.md](docs/review-model.md)를 보세요.

## Validation

로컬 개발/문서 변경 후 기본 검증. fresh clone이라면 setup부터 시작하세요.

```bash
make setup
make check-env
make validate
```

## Naming

스킬 이름은 `/forgeflow:<stage>` 형식을 사용합니다. 짧은 이름(`/review`, `/ship`)은 다른 plugin과 충돌할 수 있으므로 namespaced 형식을 권장합니다.

## Philosophy

- Artifact over chat memory
- Evidence over claims
- Stage gates over vibes
- Independent review over self-approval
- One workflow across Claude Code and Codex

## Further Reading

- [INSTALL.md](INSTALL.md) - 설치, 업데이트, 상세 사용법
- [docs/workflow.md](docs/workflow.md) - stage와 route 규칙
- [docs/artifact-model.md](docs/artifact-model.md) - artifact-first model
- [docs/review-model.md](docs/review-model.md) - 독립 review contract
- [docs/adapter-model.md](docs/adapter-model.md) - Claude/Codex adapter boundary
- [docs/codex-desktop.md](docs/codex-desktop.md) - Codex Desktop 사용법
- [scripts/README.md](scripts/README.md) - local scripts와 validation helper

## License

MIT.
