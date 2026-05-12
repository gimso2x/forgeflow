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

ForgeFlow는 보통 Claude Code plugin이나 Codex plugin으로 설치해서 씁니다. Python runtime/CLI만 프로젝트에 고정해서 쓰려면 패키지로 설치할 수도 있습니다.

```bash
# local development
python3 -m pip install -e .
forgeflow --help
forgeflow status --task-dir examples/runtime-fixtures/small-doc-task

# install from GitHub
python3 -m pip install "forgeflow-runtime @ git+https://github.com/gimso2x/forgeflow.git"
forgeflow-runtime --help
```

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
/forgeflow:execute
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
irm https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python - -- --force
```

설치 후 Codex Desktop을 재시작하고 local marketplace에서 ForgeFlow를 enable합니다. 그 다음 Claude와 같은 slash-style prompt로 사용합니다.

설치된 plugin 버전은 PowerShell에서 확인할 수 있습니다.

```powershell
(Get-Content "$HOME\plugins\forgeflow\.codex-plugin\plugin.json" | ConvertFrom-Json).version
```

```text
/forgeflow:clarify <하고 싶은 작업>
/forgeflow:plan
/forgeflow:execute
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

### Init scaffold

`/forgeflow:init` 또는 `scripts/run_orchestrator.py init`은 이제 빈 런타임 JSON만 만들지 않습니다. task-local 작업 폴더를 만들고, 다음 agent가 바로 이어받을 수 있는 초안과 포인터를 같이 생성합니다.

```bash
python3 scripts/run_orchestrator.py init \
  --task-id my-task-001 \
  --objective "Update README quickstart" \
  --risk low
```

기본 출력 위치는 `.forgeflow/tasks/<task-id>/`입니다. `--task-dir /path/to/task`를 주면 그 디렉터리 안에만 생성합니다. init은 기존 `brief.json`이 있으면 덮어쓰지 않고 실패합니다.

생성되는 주요 파일:

- Runtime state: `brief.json`, `run-state.json`, `checkpoint.json`, `session-state.json`
- Draft docs: `.forgeflow/tasks/my-task-001/docs/PRD.md`, `.forgeflow/tasks/my-task-001/docs/ARCHITECTURE.md`, `.forgeflow/tasks/my-task-001/docs/QA.md`, `.forgeflow/tasks/my-task-001/docs/DECISIONS.md`
- Task docs: `.forgeflow/tasks/my-task-001/tasks/init-summary.md`, `.forgeflow/tasks/my-task-001/tasks/feature/<objective-slug>.md`, `.forgeflow/tasks/my-task-001/tasks/qa/<objective-slug>.md`
- Claude task-local entry points: `.forgeflow/tasks/my-task-001/.claude/agents/planner.md`, `.forgeflow/tasks/my-task-001/.claude/agents/implementer.md`, `.forgeflow/tasks/my-task-001/.claude/agents/qa.md`, `.forgeflow/tasks/my-task-001/.claude/agents/reviewer.md`
- Claude task-local skills: `.forgeflow/tasks/my-task-001/.claude/skills/plan/SKILL.md`, `.forgeflow/tasks/my-task-001/.claude/skills/build/SKILL.md`, `.forgeflow/tasks/my-task-001/.claude/skills/qa-fix/SKILL.md`, `.forgeflow/tasks/my-task-001/.claude/skills/review/SKILL.md`
- Pointer: `CLAUDE.md`

`selected_architecture`도 결과 JSON에 포함됩니다. high risk, security, migration, refactor, architecture 계열 작업은 `fan-out/fan-in + producer-reviewer`로 올라가고, bug/fix/qa/test/regression 계열은 `pipeline + producer-reviewer`를 씁니다. 기본은 `producer-reviewer + pipeline`입니다.

생성물은 설치 디렉터리나 전역 Claude/Codex 설정을 건드리지 않습니다. 전부 `.forgeflow/tasks/<task-id>/` 또는 명시한 `--task-dir` 아래에만 생깁니다.

## What's Inside

- Claude Code plugin metadata and skills
- Codex plugin metadata and skills
- Generated Claude/Codex adapter instructions
- Canonical workflow policy and JSON schemas
- `memory/` inspectable local memory for curated, version-controlled patterns, decisions, and learnings
- Local validation, eval runner, sample fixtures, and runtime support tools
- v0.3.0 helpers for plan drafting, profile inspection, visual rendering, and Codex plugin diagnosis

ForgeFlow는 hosted agent service나 SaaS runtime이 아닙니다. agent가 로컬 프로젝트에서 더 예측 가능하게 일하도록 만드는 workflow 규약과 검증 도구입니다.

`memory/`는 cache or hidden agent state가 아닙니다. 장기적으로 남길 운영 패턴, 결정, 학습만 담는 project artifact이며 작은 curated 파일은 Git에 커밋합니다. 자세한 보존 기준은 [memory/README.md](memory/README.md)를 보세요.

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

세부 명령은 [scripts/README.md](scripts/README.md)에 있습니다. Workflow eval은 [evals/README.md](evals/README.md)의 `make evals`로 실행합니다.

Claude Code 플러그인 설치 직후에는 post-install smoke를 한 번 돌립니다. 이 한 줄은 generated 파일 존재, canonical route vocabulary, `claude plugin validate`, `/forgeflow:clarify` dry-run, `/forgeflow:init` disposable fixture write를 확인합니다. 실패하면 출력에 reinstall/restart/check next step이 같이 나옵니다.

```bash
scripts/smoke.sh
```

## Plugin smoke matrix

Claude/Codex 플러그인·프리셋 smoke는 CI의 `plugin-smoke-matrix` job에서 Linux/Windows, Claude/Codex, `small`/`medium`/`high` route label 조합으로 돕니다. 실제 Claude/Codex CLI가 있는 환경에서는 route-label dry-run까지 실행하고, 없는 GitHub runner에서는 packaging, Codex project-local preset install, doctor, non-mutating guard를 검증합니다.

로컬에서 disposable Next.js 앱으로 재현하려면:

```bash
base="/tmp/forgeflow-next-smoke-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$base"
cd "$base"
npx create-next-app@latest app --ts --eslint --app --src-dir --no-tailwind --use-npm --yes
cd app
git init && git add . && git commit -m 'initial next smoke app'
cd /home/ubuntu/work/forgeflow
python3 scripts/ci_plugin_smoke_matrix.py --surface codex --route-label medium --project "$base/app"
python3 scripts/ci_plugin_smoke_matrix.py --surface claude --route-label small --project "$base/app"
```

각 smoke는 baseline setup 이후 `git status --short`와 project content snapshot을 비교해 non-mutating 조건을 확인합니다.

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
- [evals/README.md](evals/README.md) - executable workflow eval runner

## License

MIT.
