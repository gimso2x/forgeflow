# ForgeFlow

ForgeFlow는 AI coding agent를 위한 artifact-first delivery workflow입니다.
채팅 기억에 의존하지 않고 **명시적인 markdown 산출물, 프롬프트 기반 게이트, 독립 review**로 작업하게 만듭니다.

## 누가 왜 쓰나

- AI 코딩 에이전트로 **실제 프로덕션 코드**를 작성하는 개발자
- 에이전트의 작업을 **검증 가능한 산출물**로 추적하고 싶은 팀
- "에이전트가 뭘 했는지 모르겠다"는 문제를 해결하고 싶은 사람

## 30초 퀵스타트

**Claude Code:**

```
/plugin marketplace add https://github.com/gimso2x/forgeflow
/plugin install forgeflow
```

**Gemini CLI:**

```bash
gemini extensions install https://github.com/gimso2x/forgeflow
printf 'Y\n' | gemini extensions update forgeflow
```

`gemini extensions update forgeflow`는 확인 프롬프트가 뜰 수 있어 자동화에서는 위처럼 명시 승인 입력을 파이프합니다. 로컬 checkout에서 검증하거나 개발 중인 버전을 연결할 때는 `gemini extensions validate .` 후 `gemini extensions link .`를 사용합니다. Gemini extension manifest는 루트 `GEMINI.md`를 context file로 로드합니다.

**Codex:**

대상 프로젝트 루트에서 실행하세요. ForgeFlow repo나 Codex plugin cache 안에서 실행하면 산출물이 잘못된 위치에 생길 수 있습니다.

```bash
mkdir -p .codex/plugins/forgeflow
cp -R /path/to/forgeflow/.codex-plugin/plugin.json /path/to/forgeflow/skills /path/to/forgeflow/templates .codex/plugins/forgeflow/
```

로컬 checkout을 대상 프로젝트의 플러그인 폴더로 복사하는 방식입니다. 업데이트할 때는 같은 `cp -R` 명령을 다시 실행해 `plugin.json`, `skills/`, `templates/`를 함께 갱신합니다.

**Cursor (로컬 플러그인):**

```bash
mkdir -p ~/.cursor/plugins/local
ln -s /path/to/forgeflow ~/.cursor/plugins/local/forgeflow
# Cursor: Developer: Reload Window
```

Agent chat에서 스킬을 호출합니다. Cursor는 콜론(`:`)이 없는 짧은 이름을 사용합니다.

```text
/forgeflow-init
/clarify   로그인 페이지에 소셜 로그인 버튼 추가
/execute
/review
/ship
```

Claude/Codex의 `/forgeflow:clarify` 등과 동일한 스킬입니다. 매핑은 [skills/forgeflow/SKILL.md](skills/forgeflow/SKILL.md)를 참고하세요.

## 기본 워크플로우

```text
/forgeflow-init       → 작업 공간 초기화 → .forgeflow/tasks/<task-id>/
/forgeflow:clarify   → 요구사항 정리 → brief.md
/forgeflow:plan      → 작업 계획 → plan.md        (medium 이상)
/forgeflow:execute   → 구현 실행 → implementation-notes.md
/forgeflow:review    → 독립 검증 → review-report.md
/forgeflow:ship      → 배포/마무리
/forgeflow:finish    → 브랜치 정리
```

## Routes (자동 선택)

clarify 스킬이 복잡도를 평가하여 자동으로 라우트를 선택합니다:

| Route  | Stages                                                                                    | When                       |
| ------ | ----------------------------------------------------------------------------------------- | -------------------------- |
| small  | clarify → execute → review → ship → finish                                                | 저위험, 소규모, 쉬운 롤백  |
| medium | clarify → plan → execute → review → ship → finish                                       | 범위 명확, 검증 필요       |
| high   | clarify → plan → execute → review (spec) → review (quality) → ship → long-run → finish | 아키텍처 영향, 롤백 어려움 |
| epic   | clarify → milestone → plan → execute → review (spec) → review (quality) → ship → long-run → finish | 대규모, 멀티윅             |

### Route scoring 기준

v1.x는 Python 런타임을 제거했지만, route 판단 기준은 v0.x의 weighted scoring 모델을 문서 기준으로 유지합니다.

```text
raw_score = file_count*1.0 + estimated_lines*0.1 + requirement_count*2.0 + dependency_count*1.5 + risk_keywords*3.0
```

|     Score | Route 판단                                     |
| --------: | ---------------------------------------------- |
|    `< 10` | small                                          |
| `10-16.9` | medium-light: scoped multi-file change         |
| `17-24.9` | medium-full: cross-module/service-level change |
| `25-49.9` | high                                           |
|   `>= 50` | epic                                           |

`17.0`은 medium을 light/full로 가르는 `mid_threshold`입니다.
프로젝트별 조정이 필요하면 `skills/clarify/SKILL.md`의 scoring 기준과 관련 템플릿을 함께 바꿉니다.

## Artifacts

모든 산출물은 `.forgeflow/tasks/<task-id>/` 아래에 markdown 파일로 기록됩니다:

| 산출물                    | 설명                         | 라우트  |
| ------------------------- | ---------------------------- | ------- |
| `brief.md`                | 요구사항, 라우트, 제약사항   | 전체    |
| `plan.md`                 | 작업 계획, 태스크 분해, 검증 | medium+ |
| `run-ledger.md`           | 실행 상태 truth (pending/done) | execute |
| `checkpoint.md`           | 재개용 전술 포인터           | execute |
| `implementation-notes.md` | 실행 진행, 결정 기록, 편차   | 전체    |
| `review-report.md`        | 독립 검증 (high/epic: spec+quality) | 전체    |
| `ship-summary.md`         | ship handoff 요약            | 전체    |
| `roadmap.md`              | 마일스톤 분해                | epic    |
| `eval-record.md`          | 학습 기록                    | high+   |

`review-report.md`의 **Execute Micro-Gates** 테이블(high/epic)은 execute 단계의 `micro_spec` / `micro_quality` 증거를 stage review가 reported로 받아 재검증할 때 씁니다.

## Subagent execute (opt-in, high/epic)

기본 `/forgeflow:execute`는 컨트롤러가 구현하고 필요 시 일부 step만 subagent에 위임합니다.

**plan step마다** implementer → spec micro-review → quality micro-review 루프를 강제하려면 opt-in 스킬을 사용합니다.

```text
/forgeflow:subagent-execute
# 또는
/forgeflow:execute --subagent-per-task
```

- **When:** high/epic, 승인된 `plan.md`, 독립 파일 스코프의 step
- **Prompts:** `skills/execute/references/*.md`
- **Not a substitute for** `/forgeflow:review` — stage review는 여전히 필수

자세한 절차는 [`skills/subagent-execute/SKILL.md`](skills/subagent-execute/SKILL.md)와 [`skills/forgeflow/SKILL.md`](skills/forgeflow/SKILL.md)의 Review depth by route를 참고하세요.

## 특징

- **의존성 제로** — Python, Node.js 등 외부 런타임 불필요
- **순수 Markdown** — 모든 산출물이 사람이 읽을 수 있는 markdown
- **프롬프트 기반** — 스크립트가 아닌 프롬프트 지시로 강제
- **멀티 플랫폼** — Claude Code, Codex, Gemini CLI, Cursor(로컬 플러그인) 지원

어댑터별 CLI 플래그, 타임아웃, 감지 방법: [docs/adapter-config.md](docs/adapter-config.md)

## Release version policy

루트 `VERSION` 파일을 단일 버전 기준으로 사용합니다.
README 본문에는 현재 릴리즈 버전을 고정하지 않습니다.
CI가 다음 파일의 정합성을 검사합니다.

- `VERSION`
- `CHANGELOG.md`
- `SKILL.md`
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `.codex-plugin/plugin.json`
- `.cursor-plugin/plugin.json`
- `gemini-extension.json`

## Evolution rule lifecycle

- `long-run`
  - 트리거: high/epic 작업 완료 후 반복 실수, 리뷰 finding, eval 실패가 evidence로 남음
  - 산출물/위치: `eval-record.md`, `.forgeflow/evolution/proposed/*.md`
  - 다음 단계: review
- `proposed`
  - 트리거: `templates/evolution-rule.md`로 후보 규칙 작성
  - 산출물/위치: `Lifecycle: proposed`, `Review Status: unreviewed`
  - 다음 단계: review
- `review`
  - 트리거: 후보 규칙의 evidence, false-positive guard, scope, rollback이 검증됨
  - 산출물/위치: `review-report.md`의 Evolution Rule Review
  - 다음 단계: active 또는 rejected
- `active`
  - 트리거: review 승인 후 프로젝트 규칙으로 승격
  - 산출물/위치: `.forgeflow/evolution/active/*.md`
  - 다음 단계: 다음 clarify/plan/execute에서 자동 적용
- `retired`
  - 트리거: 규칙이 해롭거나 더 이상 맞지 않음
  - 산출물/위치: `.forgeflow/evolution/retired/*.md`
  - 다음 단계: retirement reason 기록 후 로드하지 않음

Project active rule은 해당 repository의 필수 제약입니다.
Global rule(`~/.forgeflow/evolution/active/*.md`)은 advisory only이며 hard block으로 쓰지 않습니다.

## 로컬 검증

이 저장소는 v1.x 기준으로 runtime/build 의존성이 없는 Markdown/JSON 패키지입니다. 변경 전후에는 GitHub Actions의 구조 검증 계약(`.github/workflows/validate.yml`)과 같은 핵심 범위를 로컬에서 먼저 확인합니다.

```bash
make validate
```

`make validate`는 Python runtime 파일 재유입, 플러그인/extension JSON 파싱, public skill `SKILL.md` 존재 및 frontmatter `name`/`description`/`validate_prompt` 정합성, 필수 템플릿 존재 여부, 첫 성공 데모 산출물 생성, skill→template cross-reference, Gemini skill imports, plugin defaultPrompt 매핑, adapter config 계약, workflow vocabulary, `evals/evals.json` 계약(정수형 순차 `id`, 고유 `name`, assertion shape, repo-relative `files` 참조 포함), Markdown 상대 링크를 확인합니다. 개별 명령으로 확인할 때는 아래와 같습니다.

```bash
# Python runtime 파일이 다시 들어오지 않았는지 확인
find . -name '*.py' -not -path './.git/*' -not -path './.venv/*'

# 플러그인/extension JSON 파싱 확인
python3 -m json.tool .claude-plugin/plugin.json >/dev/null
python3 -m json.tool .claude-plugin/marketplace.json >/dev/null
python3 -m json.tool .codex-plugin/plugin.json >/dev/null
python3 -m json.tool .cursor-plugin/plugin.json >/dev/null
python3 -m json.tool gemini-extension.json >/dev/null
```

출력이 없어야 하는 첫 번째 명령을 제외하고, JSON 명령은 exit code 0이면 통과입니다. 전체 release/version/skill 계약은 push/PR에서 `validate` workflow가 검사합니다.

### 첫 성공 데모

로컬 checkout만으로 산출물 위치와 템플릿 구성을 빠르게 확인하려면 다음을 실행합니다. 실제 provider/plugin E2E가 아니라, 임시 workspace에 대표 산출물 템플릿을 복사해 첫 실행 결과의 파일 구조를 보여주는 안전한 데모입니다.

```bash
make demo
```

이 명령은 `mktemp -d` 아래에 `.forgeflow/tasks/demo-small/`을 만들고 `brief.md`, `implementation-notes.md`, `review-report.md`, `ship-summary.md` 경로를 출력합니다. 생성된 임시 workspace를 열어 실제 작업에서는 `/forgeflow-init`부터 시작하세요.

## 실제 외부 실행 안전 기준

v1.x는 Python `exec-stage --real` 런타임을 포함하지 않습니다.
향후 실제 Claude/Codex/Gemini CLI를 호출하는 adapter나 `--real` 경로를 다시 추가한다면 기본값은 stub/dry-run이어야 합니다.
실제 외부 호출 전에는 stderr 경고와 `[y/N]` 확인 프롬프트가 필수입니다.

## 첫 실행 예시

먼저 실제 프로젝트 루트에서 실행 중인지 확인하세요. 에이전트가 plugin cache/설치 디렉토리에서 열렸다면 `/forgeflow-init --task-dir <project>/.forgeflow/tasks/<task-id>`처럼 명시 경로를 넘겨 프로젝트 안에 산출물을 만듭니다.

```text
> /forgeflow-init
# → .forgeflow/tasks/<task-id>/ 작업 공간 준비

> /forgeflow:clarify 로그인 페이지에 소셜 로그인 버튼 추가
# → brief.md 생성, route: small

> /forgeflow:execute
# → 구현 진행, implementation-notes.md 업데이트

> /forgeflow:review
# → 독립 review, review-report.md 생성

> /forgeflow:ship
# → ship-summary.md, handoff 요약

> /forgeflow:finish
# → 브랜치 merge/PR/keep/discard 선택
```

## 라이선스

MIT
