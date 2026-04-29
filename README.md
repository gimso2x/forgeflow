# ForgeFlow

ForgeFlow는 AI coding agent 작업을 채팅 기록이 아니라 **명시적인 단계, 로컬 artifact, gate, 독립 review**로 통제하기 위한 artifact-first delivery harness입니다.

Claude Code plugin, Codex plugin/adapter, 로컬 runtime을 통해 같은 workflow 규칙을 여러 agent 표면에 적용합니다. ForgeFlow는 agent OS, SaaS runtime, prompt 모음집이 아닙니다. 작업을 더 예측 가능하게 만들기 위한 로컬 실행 규약과 검증 도구입니다.

## At a Glance

| 영역 | ForgeFlow가 제공하는 것 |
| --- | --- |
| Workflow | clarify -> plan/specify when needed -> run -> review -> ship/finish |
| Evidence | `brief.json`, `run-state.json`, `plan-ledger.json`, `review-report.json`, `eval-record.json` 같은 durable artifact |
| Surfaces | Claude Code plugin, Codex metadata/plugin entry, generated Claude/Codex adapters, local runtime |
| Safety | worker self-approval 방지, schema gate, adapter drift check, release/version sync check |
| Boundary | 로컬 artifact-first harness. provider orchestration service나 hosted runtime이 아님 |

## 언제 쓰나

ForgeFlow는 agent에게 "알아서 해줘"라고 맡기기에는 리스크가 있는 작업에 맞습니다.

- 요구사항을 먼저 정리하고 성공 조건을 남겨야 하는 작업
- 코드 변경, review, 검증 evidence가 분리되어야 하는 작업
- 작은 수정은 가볍게 처리하되, medium/high risk 작업은 plan과 review gate를 강제하고 싶은 경우
- Claude Code, Codex, local CLI가 같은 작업 규칙을 공유해야 하는 경우

반대로 단순한 일회성 질문, 순수 brainstorming, agent runtime이 필요 없는 문서 메모에는 과합니다.

## 빠른 시작

ForgeFlow 자체 runtime을 확인하려면 저장소에서 다음을 실행합니다.

```bash
make setup
make check-env
make validate
```

Windows PowerShell에서는 wrapper를 사용할 수 있습니다.

```powershell
.\scripts\setup.ps1
.\scripts\validate.ps1
```

샘플 task를 안전하게 실행하려면:

```bash
make runtime-sample
```

직접 task artifact를 만들 때:

```bash
python3 scripts/run_orchestrator.py init \
  --task-id my-task-001 \
  --objective "Update README quickstart" \
  --risk low
```

기본 artifact 위치는 현재 프로젝트의 `.forgeflow/tasks/<task-id>/`입니다.

Claude/Codex plugin cache 안에서 `/forgeflow:init`이 실행되면 ForgeFlow는 cache 아래에 `.forgeflow/tasks/...`를 만들지 않고 실패해야 합니다. 이 경우 traceback 없이 `ERROR:`로 끝나야 하며, 일반 프로젝트 경로에 `plugin/marketplace` 같은 이름이 들어간 것만으로 막으면 안 됩니다.

```bash
python3 scripts/run_orchestrator.py init \
  --task-dir /path/to/your-project/.forgeflow/tasks/<task-id> \
  --task-id <task-id> \
  --objective "<objective>" \
  --risk low
```

전체 설치와 업데이트 절차는 [INSTALL.md](INSTALL.md)를 보세요.

## Claude Code 플러그인

Claude Code에서는 repo를 직접 `plugin install` 하는 대신 marketplace로 추가한 뒤 plugin을 설치합니다.

```text
/plugin marketplace add https://github.com/gimso2x/forgeflow
/plugin install forgeflow
```

터미널에서 설치/검증할 때는 같은 동작을 이렇게 실행할 수 있습니다.

```bash
claude plugin marketplace add https://github.com/gimso2x/forgeflow
claude plugin install forgeflow
```

설치 후 기본 흐름은 namespaced slash skill을 사용합니다.

```text
/forgeflow:init --task-id <id> --objective "<objective>" --risk low|medium|high
/forgeflow:clarify <하고 싶은 작업>
/forgeflow:plan
/forgeflow:run
/forgeflow:review
/forgeflow:ship
/forgeflow:finish
```

운영에서는 짧은 `/review`, `/ship` 대신 `/forgeflow:review`, `/forgeflow:ship`처럼 namespaced form을 권장합니다. 다른 Claude plugin slash command와 충돌할 수 있기 때문입니다.

자세한 plugin 설치, 업데이트, `/forgeflow:specify`, `/forgeflow:finish` 의미는 [INSTALL.md](INSTALL.md)에 있습니다.

## Codex Plugin과 수동 Adapter

Codex에서는 ForgeFlow plugin을 설치한 뒤 Claude와 같은 slash-style prompt로 시작합니다.

```bash
python3 scripts/install_codex_plugin.py
```

Windows PowerShell:

```powershell
.\scripts\install_codex_plugin.ps1
```

설치 후 Codex Desktop을 재시작하고, local marketplace에서 ForgeFlow를 install/enable합니다. 그 다음에는 이렇게 사용합니다.

```text
/forgeflow:init --task-id <id> --objective "<objective>" --risk low|medium|high
/forgeflow:clarify <하고 싶은 작업>
/forgeflow:plan
/forgeflow:run
/forgeflow:review
/forgeflow:ship
/forgeflow:finish
```

프로젝트에 더 강한 지속 규칙을 남기고 싶을 때만 `CODEX.md` 또는 preset을 추가로 설치합니다.

generated adapter만 복사하려면:

```bash
cp adapters/generated/codex/CODEX.md /path/to/your-project/CODEX.md
```

Claude Code를 수동 adapter 방식으로 쓰려면:

```bash
cp adapters/generated/claude/CLAUDE.md /path/to/your-project/CLAUDE.md
```

Next.js 프로젝트에는 project-local preset을 설치할 수 있습니다.

```bash
python3 scripts/install_agent_presets.py --adapter codex --target /path/to/your-project --profile nextjs --install-codex-md
python3 scripts/install_agent_presets.py --adapter claude --target /path/to/your-project --profile nextjs
```

세부 옵션, overwrite 정책, preset 산출물은 [INSTALL.md](INSTALL.md)와 [docs/codex-desktop.md](docs/codex-desktop.md)를 보세요.

## 기본 Workflow

ForgeFlow의 canonical path는 다음 흐름입니다.

```text
user request
  -> clarify
  -> route selection
  -> plan/specify when needed
  -> run
  -> independent review
  -> ship
  -> finish when branch disposition is needed
```

핵심 규칙은 단순합니다.

- `clarify`는 요청을 실행 가능한 brief로 정리합니다.
- medium/high risk 작업은 실행 전에 plan/specification을 더 단단히 만듭니다.
- worker는 자기 작업을 스스로 승인하지 않습니다.
- review는 artifact와 evidence를 기준으로 독립적으로 판단합니다.
- `ship`은 final handoff/report 단계이고, branch merge/PR/keep/discard 결정은 `finish`에서 명시적으로 다룹니다.

stage 의미와 전환 규칙은 [docs/workflow.md](docs/workflow.md)에 있습니다.

이 흐름은 사용자가 stage 명령을 하나하나 대신 운영하라는 뜻은 아니다. "계획을 세워주세요" 같은 요청은 agent-owned decomposition으로 받아서 agent가 다음 단계와 artifact를 정리해야 합니다. 다만 stage 경계를 넘을 때는 닫힌 질문으로 멈춘다: `다음 스텝으로 `/forgeflow:run`을 진행하시겠습니까? (y/n)`.

## Artifact Model

ForgeFlow는 agent의 말보다 파일 artifact를 우선합니다.

대표 artifact:

- `brief.json` - 목표, 성공 조건, 제약, risk route
- `plan-ledger.json` - plan과 gate 상태
- `run-state.json` - 실행 상태와 산출물 참조
- `review-report.json` - 독립 review 결과
- `eval-record.json` - long-running 또는 higher-risk 작업의 검증 기록
- `decision-log.json` - 중요한 판단과 변경 이력

artifact contract와 schema 관계는 [docs/artifact-model.md](docs/artifact-model.md), [docs/contract-map.md](docs/contract-map.md), `schemas/`를 보세요.

## Review Model

ForgeFlow review의 기본 원칙은 worker와 reviewer를 분리하는 것입니다.

- worker output은 evidence와 artifact path를 남깁니다.
- reviewer는 같은 작업을 approve할 수 없습니다.
- review 결과는 `review-report.json`으로 남고 schema validation 대상이 됩니다.
- high-risk 작업은 더 강한 evidence와 gate를 요구합니다.

자세한 review contract는 [docs/review-model.md](docs/review-model.md)에 있습니다.

## 검증 명령

로컬 개발/문서 변경 후 기본 검증:

```bash
make setup
make check-env
make validate
```

샘플 fixture 검증:

```bash
make runtime-sample
```

Claude Code plugin smoke test:

```bash
make smoke-claude-plugin
```

`make smoke-claude-plugin`은 Claude CLI 로그인, quota, plugin cache 상태에 영향을 받습니다. deterministic repo validation과는 별도입니다. 이 smoke는 dry-run slash prompts를 확인하고 `/forgeflow:init` writes starter artifacts through `/forgeflow:init` 경로도 검증합니다. Windows에서는 `script` 명령이 없어도 직접 `claude -p ... --output-format json` fallback으로 실행합니다.

### Maintainer verification before release or plugin update

```bash
make validate
make smoke-claude-plugin
claude plugin validate /path/to/forgeflow
```

release 전에는 deterministic validation과 live Claude plugin smoke를 분리해서 봅니다. `make validate`는 repo contract drift를 잡고, `make smoke-claude-plugin`은 설치된 Claude plugin, auth/quota, plugin cache 상태까지 포함한 live surface를 확인합니다.

운영자 CLI 표면을 확인하려면:

```bash
make orchestrator-help
make orchestrator-status
```

Make target과 script 설명은 [scripts/README.md](scripts/README.md)를 보세요.

## Repo Map

| 경로 | 역할 |
| --- | --- |
| `.claude-plugin/` | Claude Code plugin manifest와 plugin packaging surface |
| `.codex-plugin/` | Codex local plugin metadata |
| `adapters/generated/` | Claude/Codex generated root instruction adapters |
| `docs/` | workflow, artifact, review, adapter, architecture 설계 문서 |
| `examples/` | task fixture와 runtime sample |
| `policy/canonical/` | workflow semantics, gates, routing, review order policy |
| `prompts/` | adapter와 plugin surface가 참조하는 prompt source |
| `runtime/` | orchestrator, gates, ledger, recovery runtime package |
| `schemas/` | artifact JSON schema contract |
| `scripts/` | install, validation, generation, smoke test helper |
| `tests/` | runtime과 contract test |

## 관련 문서

- [INSTALL.md](INSTALL.md) - 설치, 업데이트, Claude/Codex adapter 사용법
- [docs/architecture.md](docs/architecture.md) - 전체 architecture
- [docs/workflow.md](docs/workflow.md) - stage와 전환 규칙
- [docs/artifact-model.md](docs/artifact-model.md) - artifact-first model
- [docs/review-model.md](docs/review-model.md) - 독립 review contract
- [docs/adapter-model.md](docs/adapter-model.md) - generated adapter boundary
- [docs/operator-shell.md](docs/operator-shell.md) - local orchestrator/operator shell
- [docs/windows.md](docs/windows.md) - Windows 사용 시 주의점
- [scripts/README.md](scripts/README.md) - scripts와 Make target 설명

## 현재 경계

ForgeFlow는 local-first harness입니다.

- provider 계정, model 선택, IDE 기능을 대신 관리하지 않습니다.
- 외부 agent를 hosting하거나 queueing하는 서비스가 아닙니다.
- generated adapter는 직접 수정하지 않습니다. canonical policy, docs, prompts를 수정한 뒤 regenerate해야 합니다.
- plugin/runtime 변경은 `make validate`와 관련 smoke test로 표면 drift를 확인해야 합니다.
