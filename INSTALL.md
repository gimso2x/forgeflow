# ForgeFlow 설치 가이드

ForgeFlow는 두 가지 방식으로 쓸 수 있습니다.

1. **프로젝트 뼈대** — 이 저장소를 clone해서 runtime, schema, generated adapter까지 직접 사용
2. **Claude Code 플러그인** — Claude Code에서 ForgeFlow 규칙/스킬 표면을 설치해서 사용

## Claude Code 플러그인

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

설치 후 새 Claude Code 세션을 열고 slash skill을 사용하세요. 기본 입구는 `/forgeflow:clarify`지만, agent가 자연스럽게 다음 stage를 이어 받아야지 사용자가 매번 workflow 운영자가 될 필요는 없습니다.

```text
/forgeflow:init --task-id <id> --objective "<objective>" --risk low|medium|high
/forgeflow:clarify <하고 싶은 작업>
/forgeflow:plan
/forgeflow:run
/forgeflow:review
/forgeflow:ship
/forgeflow:finish
```

`/forgeflow:ship`은 검증·리뷰 evidence를 묶어 final handoff/report를 만드는 단계입니다. branch disposition은 여기서 하지 않습니다. `/forgeflow:finish`는 그 다음에 merge, PR, keep, or discard 같은 branch disposition을 explicit user direction으로 결정하는 단계입니다.

짧은 이름(`/clarify`, `/plan`, `/review`, `/ship`)도 동작할 수 있지만, 다른 Claude plugin/gstack skill과 충돌할 수 있습니다. 운영에서는 **항상 `/forgeflow:<stage>` 네임스페이스 형식**을 권장합니다. 특히 `/review`와 `/ship`은 충돌 가능성이 높습니다.

요구사항을 먼저 더 단단히 뽑아야 하는 작업이면 `/forgeflow:clarify` 다음에 `/forgeflow:specify`를 끼웁니다.

```text
/forgeflow:clarify <하고 싶은 작업>
/forgeflow:specify
/forgeflow:plan
```

`/forgeflow`는 전체 workflow 설명/입구입니다. 실제 작업 진행은 보통 `/forgeflow:clarify`부터 시작하지만, 그 다음 `/forgeflow:plan`/`run`을 쓰는 이유를 agent가 정리해 줘야지 사용자에게 계획 작성을 떠넘기면 안 됩니다. 사용자가 매번 workflow 운영자가 될 필요는 없습니다. 다만 stage 경계를 넘을 때는 agent가 멈추고 닫힌 질문으로 확인합니다: `다음 스텝으로 `/forgeflow:run`을 진행하시겠습니까? (y/n)`.

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

프로젝트 단위로 Codex에 ForgeFlow 규칙을 넣으려면 generated adapter를 복사합니다.

```bash
git clone https://github.com/gimso2x/forgeflow.git /tmp/forgeflow
cp /tmp/forgeflow/adapters/generated/codex/CODEX.md ./CODEX.md
```

검증:

```bash
codex exec "Read CODEX.md first, then summarize the ForgeFlow route model."
```

## Cursor 설치

```bash
git clone https://github.com/gimso2x/forgeflow.git /tmp/forgeflow
cp /tmp/forgeflow/adapters/generated/cursor/HARNESS_CURSOR.md ./HARNESS_CURSOR.md
```

Cursor 프로젝트 규칙/문서 표면에서 `HARNESS_CURSOR.md`를 참조하게 두세요.

## 로컬 runtime 설치

ForgeFlow 자체 runtime까지 쓰려면 저장소를 clone합니다.

```bash
git clone https://github.com/gimso2x/forgeflow.git
cd forgeflow
make setup
make check-env
make validate
```

샘플 실행:

```bash
make setup
make check-env
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

기본 `execute`는 안전한 stub입니다.

```bash
python3 scripts/run_orchestrator.py execute \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --route small \
  --adapter codex
```

실제 Claude/Codex CLI를 호출하려면 `--real`을 붙입니다.

```bash
python3 scripts/run_orchestrator.py execute \
  --task-dir examples/runtime-fixtures/small-doc-task \
  --route small \
  --adapter claude \
  --real
```

결과 JSON에서 반드시 확인하세요.

```json
{
  "execution_mode": "real"
}
```

`execution_mode` 확인 안 하고 “실제 모델이 돈다”고 믿는 건 삽질 예약입니다.

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
```
