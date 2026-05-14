# ForgeFlow 설치 가이드

## 빠른 설치 선택

- Claude Code를 쓰나요? → **Claude Code plugin 설치** 섹션으로 가세요.
- Codex Desktop/CLI를 쓰나요? → **Codex Plugin 설치** 섹션으로 가세요.
- Gemini CLI를 쓰나요? → **Gemini CLI extension 설치** 섹션으로 가세요.
- CLI/CI에서만 쓸 건가요? → **Python 패키지 설치** 섹션으로 가세요.
- 그냥 프로젝트에 지침만 복사할 건가요? → **수동 복사** 섹션으로 가세요.
- Antigravity를 쓰나요? → **Antigravity** 섹션으로 가세요.


ForgeFlow는 세 가지 방식으로 쓸 수 있습니다.

1. **Claude Code 플러그인** — Claude Code에서 ForgeFlow 규칙/스킬 표면을 설치해서 사용 → [상세 가이드](docs/guides/claude-code.md)
2. **Codex 플러그인** — Codex Desktop에 plugin을 등록해서 사용 → [상세 가이드](docs/guides/codex.md)
3. **Gemini CLI extension** — Gemini CLI extension으로 ForgeFlow context를 설치해서 사용
4. **Python 패키지 / Local CLI** — `pip install`로 runtime CLI를 프로젝트별로 고정해서 사용 → [상세 가이드](docs/guides/local-cli.md)

## Gemini CLI extension 설치

Gemini CLI는 ForgeFlow를 extension으로 설치합니다. 설치 후 Gemini CLI를 재시작해야 extension context가 로드됩니다.

```bash
gemini extensions install https://github.com/gimso2x/forgeflow
```

이미 checkout을 개발 중이면 복사 설치 대신 link로 바로 테스트합니다. root `GEMINI.md`는 Gemini extension bootstrap이고, 실제 ForgeFlow adapter context는 `@./adapters/generated/gemini/GEMINI.md`로 include합니다.

```bash
gemini extensions link /home/ubuntu/work/forgeflow
gemini extensions validate /home/ubuntu/work/forgeflow
```

업데이트:

```bash
gemini extensions update forgeflow
```

사용:

```bash
cd /path/to/your-project
gemini
```

Gemini 안에서는 ForgeFlow stage를 명시해서 시작합니다.

```text
Use ForgeFlow. Start /forgeflow:clarify for: README quickstart를 현재 설치 방식에 맞게 갱신.
Create task artifacts under .forgeflow/tasks/<task-id>/ and preserve clarify -> plan -> execute -> spec-review -> quality-review -> finalize.
```

프로젝트에 역할 preset과 root instruction도 고정하고 싶을 때만 아래 project-local 설치를 추가합니다. 기존 `GEMINI.md`는 기본 보존됩니다.

```bash
python3 /home/ubuntu/work/forgeflow/scripts/install_agent_presets.py \
  --adapter gemini \
  --target /path/to/your-project \
  --profile nextjs \
  --install-gemini-md
```

runtime에서 Gemini CLI를 실제 adapter로 호출할 때는 명시적으로 `--real --assert-real`을 씁니다.

```bash
python3 /home/ubuntu/work/forgeflow/scripts/run_orchestrator.py exec-stage \
  --task-dir /path/to/your-project/.forgeflow/tasks/<task-id> \
  --route small \
  --adapter gemini \
  --real \
  --assert-real
```

## Python 패키지/runtime CLI

> CLI 명령어·프로필·시각화 등 상세 usage는 [Local CLI 가이드](docs/guides/local-cli.md) 참고.

runtime만 재현 가능하게 설치하려면 editable install이나 Git URL install을 씁니다.

```bash
# repo checkout에서 local development
python3 -m pip install -e .
forgeflow --help
forgeflow status --task-dir examples/runtime-fixtures/small-doc-task

# 다른 프로젝트에서 GitHub main을 직접 설치
python3 -m pip install "forgeflow-runtime @ git+https://github.com/gimso2x/forgeflow.git"
forgeflow-runtime --help
```

제공되는 console script는 둘입니다.

- `forgeflow`: 기본 runtime orchestrator entrypoint
- `forgeflow-runtime`: 이름 충돌을 피하고 싶을 때 쓰는 같은 entrypoint

둘 다 기존 `python3 scripts/run_orchestrator.py ...`와 같은 orchestrator help/command surface를 실행합니다. plugin slash command 설치와는 별개입니다.

## Claude Code 플러그인

> 전체 설치·업데이트·troubleshooting은 [Claude Code 가이드](docs/guides/claude-code.md) 참고.

Claude Code는 GitHub repo를 직접 `plugin install` 하는 게 아니라, 먼저 marketplace로 추가한 뒤 그 안의 plugin을 설치합니다.

```text
/plugin marketplace add https://github.com/gimso2x/forgeflow
/plugin install forgeflow
```

터미널에서 검증/설치할 때는 같은 동작을 이렇게 실행할 수 있습니다.

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

설치 후 새 Claude Code 세션을 열고 slash skill을 사용하세요. 기본 입구는 `/forgeflow:clarify`지만, 새 작업 폴더와 task-local agent scaffold를 먼저 만들고 싶으면 `/forgeflow:init`으로 시작합니다. agent가 자연스럽게 다음 stage를 이어 받아야지 사용자가 매번 workflow 운영자가 될 필요는 없습니다.

설치 직후 검증은 repo checkout에서 post-install smoke 한 줄로 합니다. 이 명령은 generated plugin/adapter 파일, canonical `small`/`medium`/`high` route vocabulary, `claude plugin validate`, `/forgeflow:clarify` dry-run, `/forgeflow:init` disposable fixture write를 확인합니다. 실패하면 reinstall/restart/check next step을 출력합니다.

```bash
scripts/smoke.sh
```

```text
/forgeflow:init --task-id <id> --objective "<objective>" --risk low|medium|high
/forgeflow:clarify <하고 싶은 작업>
/forgeflow:plan
/forgeflow:execute
/forgeflow:review
/forgeflow:ship
/forgeflow:finish
```

`/forgeflow:ship`은 검증·리뷰 evidence를 묶어 final handoff/report를 만드는 단계입니다. branch disposition은 여기서 하지 않습니다. `/forgeflow:finish`는 그 다음에 merge, PR, keep, or discard 같은 branch disposition을 explicit user direction으로 결정하는 단계입니다.

짧은 이름(`/clarify`, `/plan`, `/review`, `/ship`)도 동작할 수 있지만, 다른 Claude plugin/gstack skill과 충돌할 수 있습니다. 운영에서는 **항상 `/forgeflow:<stage>` 네임스페이스 형식**을 권장합니다. 특히 `/review`와 `/ship`은 충돌 가능성이 높습니다.

요구사항을 먼저 더 단단히 뽑아야 하는 작업도 별도 `specify` stage 없이 `/forgeflow:clarify`에서 brief를 보강한 뒤 `/forgeflow:plan`으로 넘어갑니다.

`/forgeflow`는 전체 workflow 설명/입구입니다. 실제 작업 진행은 보통 `/forgeflow:clarify`부터 시작하지만, 그 다음 `/forgeflow:plan`/`run`을 쓰는 이유를 agent가 정리해 줘야지 사용자에게 계획 작성을 떠넘기면 안 됩니다. 사용자가 매번 workflow 운영자가 될 필요는 없습니다. 다만 stage 경계를 넘을 때는 agent가 멈추고 닫힌 질문으로 확인합니다: `다음 스텝으로 `/forgeflow:execute`을 진행하시겠습니까? (y/n)`.

### Init이 만드는 것

`/forgeflow:init`은 설치 작업이 아닙니다. 이미 설치된 ForgeFlow를 사용해서 현재 프로젝트 안의 `.forgeflow/tasks/<task-id>/` 또는 명시한 `--task-dir`에 task-local scaffold를 만드는 작업입니다. 그래서 plugin 설치 디렉터리, marketplace cache, 전역 Claude/Codex 설정은 건드리지 않습니다.

CLI로 같은 동작을 검증할 수 있습니다.

```bash
python3 scripts/run_orchestrator.py init \
  --task-id docs-001 \
  --objective "Update user documentation" \
  --risk low
```

생성물:

- Runtime state: `brief.json`, `run-state.json`, `checkpoint.json`, `session-state.json`
- Draft docs: `.forgeflow/tasks/my-task-001/docs/PRD.md`, `.forgeflow/tasks/my-task-001/docs/ARCHITECTURE.md`, `.forgeflow/tasks/my-task-001/docs/QA.md`, `.forgeflow/tasks/my-task-001/docs/DECISIONS.md`
- Task docs: `.forgeflow/tasks/my-task-001/tasks/init-summary.md`, `.forgeflow/tasks/my-task-001/tasks/feature/<objective-slug>.md`, `.forgeflow/tasks/my-task-001/tasks/qa/<objective-slug>.md`
- Task-local Claude agent prompts: `.forgeflow/tasks/my-task-001/.claude/agents/planner.md`, `.forgeflow/tasks/my-task-001/.claude/agents/implementer.md`, `.forgeflow/tasks/my-task-001/.claude/agents/qa.md`, `.forgeflow/tasks/my-task-001/.claude/agents/reviewer.md`
- Task-local Claude skills: `.forgeflow/tasks/my-task-001/.claude/skills/plan/SKILL.md`, `.forgeflow/tasks/my-task-001/.claude/skills/build/SKILL.md`, `.forgeflow/tasks/my-task-001/.claude/skills/qa-fix/SKILL.md`, `.forgeflow/tasks/my-task-001/.claude/skills/review/SKILL.md`
- Pointer: `CLAUDE.md`

결과 JSON에는 `selected_architecture`가 포함됩니다. 높은 리스크나 security/migration/refactor/architecture 작업은 더 엄격한 `fan-out/fan-in + producer-reviewer` 흐름을 선택합니다. init 직후 권장 다음 단계는 `status` 확인 후 `/forgeflow:clarify`입니다. 생성된 문서는 최종 명세가 아니라 시작 초안입니다.

## 수동 Claude Code 설치

플러그인 설치가 안 되는 환경이면 generated adapter를 프로젝트 루트에 복사합니다.

```bash
git clone https://github.com/gimso2x/forgeflow.git /tmp/forgeflow
cp /tmp/forgeflow/adapters/generated/claude/CLAUDE.md ./CLAUDE.md
```

Claude Code는 프로젝트 루트의 `CLAUDE.md`를 읽습니다.

검증:

```bash
claude -p "Read CLAUDE.md first. Reply with the ForgeFlow stage order."
```

## Codex 설치

> 전체 설치·preset·bootstrap은 [Codex 가이드](docs/guides/codex.md) 참고.

Codex에서는 ForgeFlow plugin을 설치한 뒤 Claude와 같은 slash-style prompt로 시작합니다.

- `/forgeflow:init`
- `/forgeflow:clarify`
- `/forgeflow:plan`
- `/forgeflow:execute`
- `/forgeflow:review`
- `/forgeflow:ship`
- `/forgeflow:finish`

사용자 입장에서는 Claude plugin과 같은 형태로 입력하면 됩니다.

### Codex plugin 등록

Codex 앱의 local plugin marketplace에 ForgeFlow를 노출하려면 checkout 없이 bootstrap installer를 실행합니다.

```bash
curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - -- --dry-run
curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - --
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python - -- --dry-run
irm https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python - --
```

이 bootstrap은 임시 디렉터리에 ForgeFlow archive를 내려받은 뒤 `scripts/install_codex_plugin.py`를 실행합니다. 설치 후 임시 checkout은 삭제됩니다.

기존 plugin copy나 다른 marketplace entry를 교체해야 할 때만 `--force`를 추가합니다. 먼저 `--dry-run --force`로 삭제 범위를 확인하세요.

```bash
curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - -- --dry-run --force
curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - -- --force
```

--force deletes ~/plugins/forgeflow before copying the current ForgeFlow checkout. It excludes `.git`, `.venv`, `.forgeflow`, `__pycache__`, and `.pytest_cache`. It also replaces only the existing `forgeflow` entry inside `~/.agents/plugins/marketplace.json`; other marketplace entries are preserved.

설치된 plugin 버전 확인:

```powershell
(Get-Content "$HOME\plugins\forgeflow\.codex-plugin\plugin.json" | ConvertFrom-Json).version
```

이미 ForgeFlow checkout 안에 있다면 로컬 스크립트를 직접 실행해도 됩니다.

```bash
python3 scripts/install_codex_plugin.py
```

Windows PowerShell:

```powershell
.\scripts\install_codex_plugin.ps1
```

이 명령은 `~/plugins/forgeflow`에 plugin copy를 만들고 `~/.agents/plugins/marketplace.json`에 local source entry를 추가합니다.

기존 plugin copy나 다른 marketplace entry를 교체하려면 `--force`를 명시하세요. 이때도 먼저 dry-run으로 삭제/교체 범위를 확인합니다.

```bash
python3 scripts/install_codex_plugin.py --dry-run --force
python3 scripts/install_codex_plugin.py --force
```

등록 후에는 Codex Desktop을 재시작하고, local marketplace에서 ForgeFlow를 install/enable합니다. Codex가 plugin 선택을 요구하면 ForgeFlow를 선택하고, 새 작업은 다음처럼 시작합니다.

```text
/forgeflow:init --task-id <id> --objective "<objective>" --risk low|medium|high
/forgeflow:clarify <하고 싶은 작업>
/forgeflow:plan
/forgeflow:execute
/forgeflow:review
/forgeflow:ship
/forgeflow:finish
```

plugin manifest의 default prompt도 이 흐름을 기준으로 합니다. `CODEX.md` 없이도 plugin skill로 시작할 수 있습니다. 프로젝트에 지속 규칙을 남기고 싶을 때만 아래 project install을 추가로 사용하세요.

### 선택: 프로젝트에 Codex 규칙 설치

plugin만으로 시작할 수 있지만, 프로젝트 단위로 ForgeFlow 규칙을 더 강하게 고정하려면 generated adapter를 복사합니다.

```bash
git clone https://github.com/gimso2x/forgeflow.git /tmp/forgeflow
cp /tmp/forgeflow/adapters/generated/codex/CODEX.md ./CODEX.md
```

Next.js 프로젝트라면 preset과 `CODEX.md`를 한 번에 설치할 수 있습니다.

```bash
python3 scripts/install_agent_presets.py --adapter codex --target /path/to/your-project --profile nextjs --install-codex-md
```

기존 `CODEX.md`는 기본적으로 보존됩니다. 교체가 의도된 경우에만 `--overwrite-codex-md`를 같이 사용하세요.

project adapter를 설치한 경우에는 Codex에 프로젝트 루트의 `CODEX.md`를 먼저 읽게 하는 방식으로 검증합니다.

```bash
codex exec "Read CODEX.md first, then summarize the ForgeFlow route model."
```

Next.js preset 설치 시 생성되는 role prompt는 `.codex/forgeflow/` 아래에 들어갑니다. 이것은 두 번째 runtime이 아니라 Codex가 참고할 project-local role preset입니다. task artifact는 프로젝트의 `.forgeflow/tasks/<task-id>/` 아래에 둡니다.

### Codex plugin 사용 흐름

권장 운영 순서는 다음과 같습니다.

1. ForgeFlow checkout에서 `scripts/install_codex_plugin.py`로 local marketplace entry를 등록합니다.
2. Codex Desktop을 재시작하고 ForgeFlow plugin을 enable합니다.
3. 새 작업에서 `/forgeflow:clarify <하고 싶은 작업>`처럼 입력합니다.
4. 필요하면 `/forgeflow:plan`, `/forgeflow:execute`, `/forgeflow:review`, `/forgeflow:ship` 순서로 진행합니다.
5. 프로젝트에 지속 규칙이 필요할 때만 `CODEX.md` 또는 Codex preset을 추가 설치합니다.
6. 실제 CLI execution까지 검증할 때만 `scripts/run_orchestrator.py ... --adapter codex --real --assert-real`을 사용합니다. `--assert-real`은 `--real` 없이 실행되면 실패하므로 CI에서 stub 실행을 실수로 성공 처리하지 않습니다.

plugin entry와 ForgeFlow skills가 기본 사용 표면입니다. `CODEX.md`, `.codex/forgeflow/`, `.forgeflow/tasks/`는 프로젝트에 더 강한 지속성과 artifact state가 필요할 때 쓰는 보강 표면입니다.

## Antigravity 설치

Antigravity는 CLI 실행 adapter가 아니라 IDE instruction adapter입니다. 그래서 `scripts/run_orchestrator.py exec-stage --adapter antigravity --real` 같은 경로를 만들지 않습니다. 프로젝트 루트의 instruction file을 IDE가 읽게 하는 방식으로 연결합니다.

```bash
git clone https://github.com/gimso2x/forgeflow.git /tmp/forgeflow
cp /tmp/forgeflow/adapters/generated/antigravity/AGENTS.md ./AGENTS.md
```

Antigravity에서 실제 작업을 시작할 때는 대상 프로젝트 폴더를 IDE로 열고 Agent chat에 이렇게 요청합니다.

```text
AGENTS.md의 ForgeFlow 절차를 따라 이 작업을 진행해줘.
먼저 .forgeflow/tasks/<task-id>/ 아래에 plan artifact를 만들고,
구현 후 git diff와 테스트 결과를 기준으로 review summary를 남겨줘.
```

결과 확인은 IDE chat 말만 믿지 말고 repo artifact와 git 상태로 합니다.

```bash
git diff
find .forgeflow/tasks -maxdepth 3 -type f
```

운영 규칙:

- Antigravity IDE에서 저장소를 열고 `AGENTS.md`를 프로젝트 지침으로 사용합니다.
- ForgeFlow artifact는 `.forgeflow/tasks/<task-id>/` 아래에 남깁니다.
- IDE chat 응답은 handoff summary로만 보고, canonical state는 artifact 파일과 git diff로 확인합니다.
- Antigravity 전용 override가 필요할 때만 별도 `GEMINI.md`를 추가합니다. 기본 adapter는 `AGENTS.md` 하나로 충분합니다.
- Antigravity를 CLI adapter처럼 호출하지 않습니다. IDE chat은 실행 표면이고, git diff와 artifact 파일이 검증 표면입니다.

### Antigravity 글로벌 사용

가능합니다. 다만 generated `AGENTS.md` 전체를 글로벌 규칙에 복사하는 건 비추천입니다. Antigravity 공식 Rules 파일은 12,000자 제한이 있고, ForgeFlow generated adapter는 프로젝트별 canonical policy까지 포함해 더 깁니다.

글로벌에는 짧은 부트스트랩 규칙만 둡니다. Antigravity의 Customizations → Rules → **+ Global**에서 만들거나 `~/.gemini/GEMINI.md`에 아래 내용을 둡니다.

```markdown
# ForgeFlow global rule for Antigravity

When a workspace contains `AGENTS.md` with ForgeFlow instructions, follow it as the project harness contract.
Do not invent a ForgeFlow CLI adapter for Antigravity.
Treat Antigravity as an IDE instruction consumer.
Keep canonical task state in `.forgeflow/tasks/<task-id>/` artifacts and verify results with `git diff` and tests.
Use chat responses only as handoff summaries.
```

프로젝트별 자동 적용이 필요하면 workspace rule을 둡니다.

```bash
mkdir -p .agents/rules
cat > .agents/rules/forgeflow.md <<'EOF'
---
description: Apply ForgeFlow harness instructions in this workspace
alwaysApply: true
---

Follow the root `AGENTS.md` ForgeFlow adapter instructions for planning, implementation, review, artifact storage, and handoff summaries.
EOF
```

이 구조가 제일 안전합니다: 글로벌은 "ForgeFlow가 보이면 따르라"는 짧은 라우터, 프로젝트 루트 `AGENTS.md`는 실제 상세 계약.

## Runtime 빠른 검증

```bash
python3 scripts/run_orchestrator.py exec-stage \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --route small \
  --adapter codex \
  --real \
  --assert-real
```


## 로컬 runtime 설치

ForgeFlow 자체 runtime까지 쓰려면 저장소를 clone합니다.

```bash
git clone https://github.com/gimso2x/forgeflow.git
cd forgeflow
make setup
make validate
```

`make validate` is the deterministic validation entry point: it runs `check-env`, then the separated validation lanes in order.

- `make validate-structure`: plugin/release version drift, context paths, schema/policy/generated checks, sample artifacts, skill contracts, Claude hooks.
- `make validate-fast`: fast deterministic pytest/eval/smoke contracts; no live provider execution.
- `make validate-plugin`: static non-mutating Claude/Codex plugin smoke matrix.
- `make validate-e2e-live`: optional mutating live-agent E2E against a disposable project; run manually, not as part of default `make validate`.

`make check-env` remains a focused diagnostic target when you only want dependency/environment output.

## Windows native vs WSL2 decision tree

If you are inside WSL2, use the Unix path. Treat WSL2 as Linux, keep the checkout on the WSL filesystem, and run:

```bash
make setup
make validate
python3 scripts/run_orchestrator.py init \
  --task-id my-task-001 \
  --objective "Update README quickstart" \
  --risk low
```

If you are in native Windows PowerShell, use the PowerShell wrappers. They resolve `.venv\Scripts\python.exe` and Python launcher differences for you:

```powershell
.\scripts\setup.ps1
.\scripts\validate.ps1
.\scripts\run_orchestrator.ps1 init --task-id my-task-001 --objective "Update README quickstart" --risk low
```

Do not mix WSL paths and PowerShell wrappers. A checkout under `/home/...` should use `make`/`python3`; a checkout under `C:\...` should use `.\scripts\*.ps1`. Mixing them creates two virtualenvs and stupid path bugs.

Windows 전용 계약은 [Windows 가이드](docs/guides/windows.md)를 보세요.

Task artifact를 만들거나 상태를 볼 때도 wrapper를 사용하면 `.venv\Scripts\python.exe` 경로를 직접 기억하지 않아도 됩니다.

```powershell
.\scripts\run_orchestrator.ps1 init --task-id my-task-001 --objective "Update README quickstart" --risk low
.\scripts\run_orchestrator.ps1 status --task-dir .\.forgeflow\tasks\my-task-001
```

Claude plugin live smoke는 `make smoke-claude-plugin`으로 실행합니다. Unix 계열에서는 `script`가 있으면 pseudo-terminal로 Claude CLI를 감싸고, Windows처럼 `script`가 없는 환경에서는 `claude -p ... --output-format json` 직접 실행 fallback을 사용합니다. 이 live smoke는 Claude CLI 로그인, quota, plugin cache 상태의 영향을 받으므로 deterministic `make validate`와 별도로 봅니다.

샘플 실행:

```bash
make setup
make validate
make runtime-sample
```

직접 task를 만들 때:

```bash
python3 scripts/run_orchestrator.py init \
  --task-id my-task-001 \
  --objective "Update README quickstart" \
  --risk low
```

기본 저장 위치는 현재 프로젝트의 `.forgeflow/tasks/<task-id>`입니다.

```text
./.forgeflow/tasks/my-task-001/
```

원하는 위치가 따로 있을 때만 `--task-dir`를 명시합니다.

```bash
python3 scripts/run_orchestrator.py init \
  --task-dir work/my-task \
  --task-id my-task-001 \
  --objective "Update README quickstart" \
  --risk low
```

## 실제 CLI 실행과 stub 실행

기본 `exec-stage`는 안전한 stub입니다.

```bash
python3 scripts/run_orchestrator.py exec-stage \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --route small \
  --adapter codex
```

실제 Claude/Codex CLI를 호출하려면 `--real`을 붙입니다. CI나 릴리즈 검증처럼 “반드시 real이어야 하는” 경로에서는 `--assert-real`도 같이 붙입니다.

```bash
python3 scripts/run_orchestrator.py exec-stage \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --route small \
  --adapter claude \
  --real \
  --assert-real
```

`--assert-real`이 붙은 명령은 `--real` 없이 실행되면 즉시 실패합니다. 반대로 `--real` 없는 stub 실행은 결과 JSON과 stderr에 `STUB EXECUTION` 경고를 출력합니다.

```json
{
  "execution_mode": "stub",
  "dry_run": true,
  "warning": "STUB EXECUTION: no real CLI adapter ran; pass --real for live execution or --assert-real to fail fast."
}
```

`execution_mode` 확인을 사람 눈에만 맡기는 건 삽질 예약이라, CI에서는 `--assert-real`로 기계가 막게 하세요.

## 업데이트

```bash
git -C /path/to/forgeflow pull
make -C /path/to/forgeflow setup
make -C /path/to/forgeflow check-env
make -C /path/to/forgeflow validate
```

현재 shell 위치와 무관하게 ForgeFlow checkout 안에서 실행되도록 `make -C /path/to/forgeflow ...`를 사용합니다.
새 dependency가 추가된 release도 놓치지 않도록 `make setup`으로 `.venv`를 갱신한 뒤 `make check-env`와 `make validate`를 실행합니다.
수동 adapter 복사 방식이면 pull 후 다시 복사하세요.

```bash
cp adapters/generated/claude/CLAUDE.md /path/to/project/CLAUDE.md
cp adapters/generated/codex/CODEX.md /path/to/project/CODEX.md
cp adapters/generated/antigravity/AGENTS.md /path/to/project/AGENTS.md
```
