# ForgeFlow

ForgeFlow는 AI coding agent 작업을 채팅 기억이 아니라 **명시적인 stage, 로컬 artifact, gate, evidence, 독립 review**로 진행하게 만드는 artifact-first delivery harness입니다. Claude Code와 Codex에서 같은 workflow를 쓰도록 돕고, 작은 수정은 가볍게, 리스크 있는 작업은 계획과 검증을 남기게 합니다.

현재 릴리즈는 **v0.3.0**입니다. 이 버전은 자연어 요구사항에서 계획 초안을 만들고, runtime/profile artifact를 읽고, Codex plugin 설치 상태를 진단하고, Mermaid/Markdown으로 작업 상태를 시각화하는 운영 보조 도구를 포함합니다.

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

사용자가 매번 stage를 운영해야 한다는 뜻은 아닙니다. 보통은 하고 싶은 일을 말하면 agent가 `/forgeflow:clarify`에서 요구사항을 정리하고, stage 경계에서 다음 단계로 넘어갈지 확인합니다.

## Installation

ForgeFlow는 보통 Claude Code plugin이나 Codex plugin으로 설치해서 씁니다.

수동 adapter 복사, local runtime, maintainer 검증, Windows wrapper 같은 자세한 절차는 [INSTALL.md](INSTALL.md)를 보세요.
Native Windows PowerShell에서 local runtime까지 검증할 때는 [docs/windows.md](docs/windows.md)의 wrapper 흐름을 사용하세요.

```powershell
.\scripts\setup.ps1
.\scripts\validate.ps1
.\scripts\run_orchestrator.ps1 init --task-id my-task-001 --objective "Update README quickstart" --risk low
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

## The Basic Workflow

1. `clarify` - 요청을 목표, 제약, 성공 조건, route로 정리합니다.
2. `plan` / `specify` - medium 이상이거나 모호한 작업을 실행 가능한 계획으로 쪼갭니다.
3. `run` - 승인된 brief와 plan 범위 안에서 작업합니다.
4. `review` - 결과를 evidence와 artifact 기준으로 독립 검토합니다.
5. `ship` / `finish` - handoff를 정리하고, 필요하면 PR/merge/keep/discard 같은 branch 결정을 다룹니다.

작업 중 생성되는 대표 artifact는 `brief.json`, `plan-ledger.json`, `run-state.json`, `review-report.json`입니다. 세부 contract는 [docs/artifact-model.md](docs/artifact-model.md)와 [docs/review-model.md](docs/review-model.md)를 보세요.

## What's Inside

- Claude Code plugin metadata and skills
- Codex plugin metadata and skills
- Generated Claude/Codex adapter instructions
- Canonical workflow policy and JSON schemas
- Local validation, sample fixtures, and runtime support tools
- v0.3.0 helpers for plan drafting, profile inspection, visual rendering, and Codex plugin diagnosis

ForgeFlow는 hosted agent service나 SaaS runtime이 아닙니다. agent가 로컬 프로젝트에서 더 예측 가능하게 일하도록 만드는 workflow 규약과 검증 도구입니다.

## v0.3.0 operator helpers

v0.3.0은 “작업을 시켰다”에서 끝내지 않고, 계획·진단·시각화·성능 확인까지 로컬 artifact로 붙잡는 쪽으로 정리했습니다.

- Natural language plan generation: `forgeflow_runtime/natural_language_plan.py`가 이슈 본문, brief, 자유 문장 요구사항을 schema-valid `plan.json` 초안으로 바꿉니다. 완성품이 아니라 plan stage에서 다듬는 안전한 초안입니다.
- Profile artifact CLI: `scripts/forgeflow_profile.py`로 `pipeline-profile.json`을 요약하고 병목을 보고, 두 task profile을 비교할 수 있습니다.
- Visual companion tooling: `scripts/forgeflow_visual.py`는 `brief.json`, `plan.json`, `review-report.json`을 Mermaid 또는 Markdown으로 렌더링합니다. 브라우저 companion은 `node scripts/visual-companion.cjs`로 띄웁니다.
- Codex plugin doctor: `scripts/codex_plugin_doctor.py`가 Codex CLI, local marketplace, plugin root, project preset/CODEX 상태를 읽기 전용으로 점검합니다.

빠른 예시는 아래처럼 실행합니다.

```bash
python3 scripts/forgeflow_profile.py summary .forgeflow/tasks/<task-id>
python3 scripts/forgeflow_visual.py plan .forgeflow/tasks/<task-id>/plan.json --format mermaid
python3 scripts/codex_plugin_doctor.py --project .
python3 scripts/smoke_codex_plugin.py --project /path/to/nextjs-app
```

세부 명령은 [scripts/README.md](scripts/README.md)에 있습니다.

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
