# ForgeFlow

[![validate](https://github.com/gimso2x/forgeflow/actions/workflows/validate.yml/badge.svg)](https://github.com/gimso2x/forgeflow/actions/workflows/validate.yml) [![evals](https://github.com/gimso2x/forgeflow/actions/workflows/evals.yml/badge.svg)](https://github.com/gimso2x/forgeflow/actions/workflows/evals.yml)

ForgeFlow는 AI coding agent를 위한 artifact-first delivery workflow입니다.
채팅 기억에 의존하지 않고 **명시적인 markdown 산출물, 프롬프트 기반 게이트, 독립 review**로 작업하게 만듭니다.

ForgeFlow에는 coding agent behavior guardrails도 포함됩니다: 숨은 가정 드러내기(assumption surfacing), 단순한 구현 우선(simplicity-first implementation), 필요한 범위만 고치는 국소 diff(surgical diffs), 목표 기준 검증(goal-driven verification). 이 규칙은 clarify/plan/execute 단계에서는 advisory로 작동하고, review 단계에서는 `assumption-risk`, `overengineering`, `scope-creep`, `unverified-success`, `drive-by-refactor` finding으로 검출할 수 있습니다. 로컬 focused 검증은 `make validate-behavior-guardrails`입니다.

## 누가 왜 쓰나

- AI 코딩 에이전트로 **실제 프로덕션 코드**를 작성하는 개발자
- 에이전트의 작업을 **검증 가능한 산출물**로 추적하고 싶은 팀
- "에이전트가 뭘 했는지 모르겠다"는 문제를 해결하고 싶은 사람

English quickstart: [README_en.md](README_en.md)

Release version source of truth: [`VERSION`](VERSION).

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
gemini extensions list
```

`gemini extensions update forgeflow`는 확인 프롬프트가 뜰 수 있어 자동화에서는 위처럼 명시 승인 입력을 파이프합니다. 업데이트 후 `gemini extensions list`에서 `forgeflow`가 보이는지 확인합니다. 로컬 checkout에서 검증하거나 개발 중인 버전을 연결할 때는 `gemini extensions validate .` 후 `gemini extensions link .`를 사용합니다. Gemini extension manifest는 루트 `GEMINI.md`를 context file로 로드합니다.

**Cursor (로컬 플러그인):**

ForgeFlow repo checkout을 Cursor 로컬 플러그인으로 연결한 뒤 Cursor에서 `Developer: Reload Window`를 실행합니다. Cursor는 콜론(`:`)이 없는 짧은 slash command를 씁니다.

```bash
mkdir -p ~/.cursor/plugins/local
ln -s /path/to/forgeflow ~/.cursor/plugins/local/forgeflow
```

```text
/clarify   로그인 페이지에 소셜 로그인 버튼 추가
/ff-plan
/execute
/ff-review
/ship
```

**Codex (CLI + Codex App):**

Codex App은 WSL backend에서도 Codex CLI와 같은 plugin marketplace 설정을 읽습니다. 따라서 Codex App에서 쓰려면 WSL 안에서 아래 명령을 실행한 뒤 앱을 새로 시작하세요.

*방법 1 — Marketplace (권장):*

```bash
# ForgeFlow checkout의 repo root를 marketplace로 등록
codex plugin marketplace add /path/to/forgeflow

# 플러그인 설치
codex plugin add forgeflow@forgeflow

# 확인
codex plugin list
```

`/path/to/forgeflow`에는 `.agents/plugins/marketplace.json`, `plugins/forgeflow` symlink, `.codex-plugin/plugin.json`, `skills/`, `templates/`가 함께 있어야 합니다. 이 repo는 그 구조를 그대로 제공하므로 checkout root를 marketplace source로 쓰면 됩니다.

원격 Git marketplace로도 등록 가능합니다:

```bash
codex plugin marketplace add gimso2x/forgeflow
codex plugin add forgeflow@forgeflow
```

이미 예전 로컬 marketplace(`forgeflow@local-codex-plugins`)로 설치했다면 중복 skill 노출을 피하려고 새 `forgeflow@forgeflow`만 enabled 상태로 남기는 것을 권장합니다. Codex App 재시작 후 새 대화에서 `/forgeflow:clarify <작업>`처럼 호출하면 됩니다.

*방법 2 — 로컬 설치 타겟:*

대상 프로젝트 루트에서 실행하세요. ForgeFlow repo나 Codex plugin cache 안에서 실행하면 산출물이 잘못된 위치에 생길 수 있습니다. 수동 `cp -R` 대신 Make target이 `plugin.json`, `skills/`, `templates/`를 한 번에 복사하므로 숨김 파일/심볼릭 링크 처리 실수를 줄일 수 있습니다.

```bash
# 대상 프로젝트 루트에서
make -C /path/to/forgeflow install-codex-local CODEX_LOCAL_PLUGIN_DIR="$PWD/.codex/plugins/forgeflow"
```

업데이트할 때도 같은 명령을 다시 실행합니다. 기본 설치 위치는 `.codex/plugins/forgeflow`입니다.

*방법 3 — 개발용 심볼릭 링크:*

ForgeFlow repo를 직접 수정하며 테스트할 때 사용합니다. symlink 대상은 `.codex-plugin` 하위 디렉토리가 아니라 `skills/`, `templates/`, `.codex-plugin/plugin.json`을 모두 포함하는 repo root여야 합니다.

```bash
# 대상 프로젝트에서
ln -s /path/to/forgeflow .codex/plugins/forgeflow
```

**Codex App + WSL:** WSL 안의 `codex plugin marketplace add /path/to/forgeflow`와 `codex plugin add forgeflow@forgeflow`가 기준입니다. Windows 쪽 앱 UI는 재시작 후 해당 WSL Codex 설정에서 enabled plugin을 읽습니다.

Cursor의 `/clarify` 등은 Claude/Codex의 `/forgeflow:clarify` 등과 동일한 스킬입니다. 매핑은 [skills/forgeflow/SKILL.md](skills/forgeflow/SKILL.md)를 참고하세요.

**설치 위치와 작업 위치를 분리하세요.** Claude/Codex/Gemini/Cursor의 plugin 또는 extension은 각 도구의 설치/cache 위치에 둘 수 있지만, `/forgeflow:clarify` 같은 실제 workflow 명령은 변경하려는 프로젝트 루트에서 실행해야 합니다. 기본 task 산출물은 repo 안이 아니라 `~/.forgeflow/projects/<project-slug>/tasks/<task-id>/`에 기록됩니다. plugin/cache 디렉토리에서 실행 중이면 `--task-dir ~/.forgeflow/projects/<project-slug>/tasks/<task-id>`처럼 명시 경로를 지정해 산출물이 대상 프로젝트 저장소에 기록되게 하세요.

**Multi-harness 원칙:** ForgeFlow의 route, artifact schema, review verdict, human gate는 adapter-neutral core contract에 속합니다. Claude Code/Codex/Gemini/Cursor 차이는 slash command 이름, CLI flag, trust/permission mode, timeout, output normalization 같은 얇은 wrapper 표면에만 둡니다. 새 어댑터나 예외를 추가할 때는 [docs/adapter-config.md](docs/adapter-config.md)의 `Multi-harness routing invariants`, [docs/review-runtime-contract.md](docs/review-runtime-contract.md), 그리고 [docs/stage-tool-boundaries.md](docs/stage-tool-boundaries.md)를 먼저 맞추고, hidden provider state나 chat transcript가 아니라 `<task-dir>` 산출물로 handoff합니다.

**역할 경계 원칙:** planner/worker/reviewer/lead/member 같은 역할명은 stage-owned pass의 관점과 책임을 설명할 뿐, 별도 팀 런타임이나 hidden approval path가 아닙니다. Worker는 scoped 구현과 evidence 수집까지만, reviewer는 read-only 검증과 `review-report.md`까지만, lead/member split은 markdown claim marker로 선언된 한 pass/section까지만 허용됩니다. 충돌이나 약한 증거는 자동 승인으로 덮지 말고 Human Review Packet으로 넘깁니다.

### Context efficiency / refresh resume

ForgeFlow는 artifact-first를 유지하면서 adapter-selected context refresh 후 재개 비용을 줄입니다. stage 경계 또는 checkpoint 갱신 직후에 context refresh가 안전합니다. 재개 시 `checkpoint.md` → `ledger.md` → `implementation-notes.md` 요약 → 필요한 섹션만 읽습니다. `checkpoint.md`의 `Handoff Boundary`는 현재 stage owner, 다음 owner, handoff reason, requested/forbidden action(= forbidden-action delegation), evidence/artifact trigger, blocker/limitation impact, explicit stop condition, exact artifact update location을 기록해 역할/도구 경계가 refresh나 adapter 전환 중 흐려지지 않게 합니다. 어댑터별 명령 힌트는 [skills/_shared/context-resume.md](skills/_shared/context-resume.md)에만 둡니다.

### 공통 프로젝트 컨텍스트

대상 프로젝트 루트에서 한 번 분석한 기획, 아키텍처, WBS, 검증 관례를 이후 태스크에서 재사용하려면 `/forgeflow:ff-config` 메뉴에서 **full init (프로젝트 컨텍스트 draft)** 를 선택해 `<storage-root>/project-draft.md`를 생성합니다.

```text
/forgeflow:ff-config
→ 4. full init (프로젝트 컨텍스트 draft)
```

이 명령은 현재 작업 중인 프로젝트의 `<storage-root>/project-draft.md`를 생성합니다. ForgeFlow plugin/cache 설치 디렉터리 안이 아니라 실제로 변경하려는 repository root에서 실행해야 하며, `config` skill이 이 artifact의 생성 책임을 가집니다.

`<storage-root>/project-draft.md`는 source of truth가 아니라 repo-relative 포인터와 안정적인 결정 요약입니다. `clarify`는 새 태스크를 시작할 때 이 파일이 있으면 planning/WBS, architecture/contract, verification hints를 `brief.md`의 `Common Project Context`, WHERE, Constraints, Verification Gates에 반영합니다. `plan`은 task-relevant section만 읽어 작업 계획에 반영하고, `execute`는 plan/brief가 참조한 section과 원본 문서·코드를 재확인한 뒤 변경합니다. checkpoint에는 관련 섹션명이나 원본 문서 경로만 남겨 compact resume 비용을 늘리지 않습니다.

갱신이 필요한 경우 같은 명령으로 draft를 다시 생성하거나 `<storage-root>/project-draft.md`를 직접 보정하세요. 토큰, API key, credential, private key 같은 비밀값은 이 파일에 복사하지 말고 정책 또는 환경 변수 이름만 포인터로 남깁니다.

### Init intelligence

`clarify`와 full init은 repo marker와 요청 문장을 함께 읽어 generic brief가 아니라 프로젝트 맞춤 초안을 만듭니다.

- **Project type detection**: `package.json`, framework config, `pyproject.toml`, `requirements.txt`, `go.mod`, `Cargo.toml` 등으로 user-facing app / API-service / dev tool-library / infrastructure 성격을 추정합니다. Next.js, React, FastAPI, Django, Flask, Express, Go, Rust, Python CLI 같은 흔한 형태는 검증/설계 힌트가 달라집니다.
- **Domain/change detection**: frontend, backend, data, auth, infra, testing, security 도메인과 feature, bugfix, refactor, migration, security, testing 변경 유형을 objective에서 추출합니다.
- **Artifact impact**: 감지 결과는 `brief.md`의 WHERE, Constraints, Acceptance Criteria, Verification Gates에 반영합니다. 예를 들어 Next.js UI 작업은 build/typecheck와 route/component 경계를 우선하고, FastAPI 결제 변경은 API contract, data safety, rollback 검증을 우선합니다.

감지는 힌트입니다. 실제 파일/프레임워크는 repo에서 확인한 증거만 쓰고, 없으면 bounded assumption으로 기록합니다.

## 기본 워크플로우

### Active surface tiers

ForgeFlow의 public entrypoint는 아래 등급으로 읽습니다. 새 사용자는 **Core**만 익히면 되고, Support/Utility는 필요할 때만 호출합니다.

- **Core workflow**: `/forgeflow:clarify`, `/forgeflow:ff-plan`, `/forgeflow:execute`, `/forgeflow:ff-review`, `/forgeflow:ship`
- **Support**: `/forgeflow:ff-config`, `/forgeflow:long-run`
- **Utility / optional**: `/forgeflow:benchmark` — delivery 파이프라인 밖의 cross-adapter 비교 도구

```text
/forgeflow:ff-config         → 설정 메뉴 (auto 토글, basic/full init 선택)
/forgeflow:clarify   → 작업 공간 생성 + 요구사항 정리 → brief.md
/forgeflow:ff-plan   → 작업 계획 → plan.md        (medium 이상; epic 시 마일스톤 분해 포함)
/forgeflow:execute   → 구현 실행 → implementation-notes.md
/forgeflow:ff-review → 독립 검증 → review-report.md
/forgeflow:ship      → 배포/마무리 + 브랜치 정리
/forgeflow:long-run  → 학습 기록 → eval-record.md (high/epic ship 후 자동 또는 수동)
/forgeflow:benchmark → cross-adapter 벤치마크 (독립 실행, 파이프라인 외부)
```

`long-run`은 high/epic 라우트 ship 완료 후 자동으로 실행되며, 수동으로 `/forgeflow:long-run`을 호출할 수도 있습니다. 재사용 가능한 패턴과 실패 규칙만 `eval-record.md`에 기록합니다. small/medium 라우트에서는 실행하지 않습니다.

### Review model

ForgeFlow review는 두 층입니다.

- **Automated review**: 기본 `/forgeflow:ff-review` 단계입니다. spec/quality/architecture/security/ux/perf 관점에서 observed evidence와 reported evidence를 구분해 `review-report.md`에 기록합니다.
- **Human review**: 자동 reviewer role이 아니라 `/forgeflow:ff-review` 이후, `/forgeflow:ship` 이전의 decision-partner gate입니다. API/CLI/schema 변경, state/data 변경, 보안 영향, 넓은 영향 범위, reviewer 간 충돌, 자동 증거 부족처럼 사람 판단이 필요한 경우 `Human Review Packet`을 작성합니다.

리뷰 입력은 `plan.md`의 **Design Intent**와 **Review Criteria**를 기준으로 합니다. plan 단계는 설계 의도, 선택한 접근, 대안, 의도적 제외사항, 적용 convention/ADR/risk check를 짧게 기록하고, review 단계는 각 finding에 `Priority`, `Criteria Basis`, `Side Effect`, `Why This Remediation`, `Disposition`, `Disposition Rationale`을 남깁니다. p1/p2 finding을 고치지 않고 거부하거나 risk-accept하면 보통 Human Review Gate가 필요합니다.

작고 국소적이며 established pattern을 반복하는 변경은 human review를 `skipped`로 기록할 수 있습니다. 그 외에는 사람이 `ship`, `execute`, `keep/defer` 중 handoff target을 결정해야 `/forgeflow:ship`이 진행됩니다. 자세한 기준은 [docs/review-model.md](docs/review-model.md)를 참고하세요.

`benchmark`는 Claude/Codex/Gemini에 동일 프롬프트를 실행해 정량 비교 리포트를 생성합니다. ForgeFlow 파이프라인과 독립적으로 실행되며, 결과는 `/tmp/forgeflow-bench/` 아래에 기록됩니다. 자세한 절차는 [`skills/benchmark/SKILL.md`](skills/benchmark/SKILL.md)를 참고하세요.

## Routes (자동 선택)

clarify 스킬이 복잡도를 평가하여 자동으로 라우트를 선택합니다:

| Route  | Stages                                                                                    | When                       |
| ------ | ----------------------------------------------------------------------------------------- | -------------------------- |
| small  | clarify → execute → review → ship                                                | 저위험, 소규모, 쉬운 롤백  |
| medium | clarify → plan → execute → review → ship                                       | 범위 명확, 검증 필요       |
| high   | clarify → plan → execute → review (spec) → review (quality) → ship → long-run | 아키텍처 영향, 롤백 어려움 |
| epic   | clarify → plan (epic decomposition) → execute → review (spec) → review (quality) → ship → long-run | 대규모, 멀티윅             |

high/epic의 spec/quality review는 별도 제거된 slash command가 아니라 같은 `/forgeflow:ff-review`가 `review-report.md` 안에서 순차 pass로 수행하는 깊이 차이입니다.

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

모든 task 산출물은 기본적으로 글로벌 프로젝트별 저장소 아래에 기록됩니다:

```text
~/.forgeflow/projects/<project-slug>/tasks/<task-id>/
```

`project-slug`는 기본적으로 `basename(repo_root)`이고, 같은 이름의 체크아웃이 충돌하면 절대 경로 해시를 붙입니다(예: `forgeflow-a13f9c`). `tasks/` 앞에 프로젝트 폴더가 있어야 여러 레포 작업이 섞이지 않습니다. 레포 안의 `<repo>/.forgeflow/tasks/<task-id>/`는 `storage.mode: local` 또는 명시 `--task-dir`일 때만 쓰는 호환/팀 공유 옵션입니다.

각 task state에는 `run-state.json`을 생성하고 최소한 `repo_root`, `project_name`, `project_slug`, `storage_root`, `task_id`를 기록해 글로벌 저장소에서도 원본 프로젝트를 항상 복원할 수 있어야 합니다. 스크립트 부트스트랩은 `python3 scripts/forgeflow_storage.py --project-dir <repo-root> --task-id <task-id> --write-run-state`를 사용합니다.

기록되는 markdown 파일:

| 산출물                    | 설명                         | 라우트  |
| ------------------------- | ---------------------------- | ------- |
| `brief.md`                | 요구사항, 라우트, 제약사항   | 전체    |
| `project-draft.md`        | 프로젝트 컨텍스트 draft (planning/WBS, architecture/contract, verification hints) | ff-config |
| `plan.md`                 | 작업 계획, 태스크 분해, 검증 | medium+ |
| `ledger.md`               | 실행 상태 truth (pending/done) | execute |
| `checkpoint.md`           | 재개용 전술 포인터           | execute |
| `run-state.json`          | 프로젝트/스토리지 식별 상태  | clarify |
| `implementation-notes.md` | 실행 진행, 결정 기록, 편차   | 전체    |
| `input-source.md`         | standalone review 입력 출처/fetch 상태 | standalone review |
| `normalized-input.md`     | standalone review 4-field 정규화 입력 | standalone review |
| `review-report.md`        | 독립 검증 (high/epic: spec+quality) | 전체    |
| `ship-summary.md`         | ship handoff 요약            | 전체    |
| `roadmap.md`              | 마일스톤 분해                | epic    |
| `eval-record.md`          | 학습 기록                    | high+   |
| `evolution-rule.md`       | evolution rule 템플릿 (ship에서 `active/`에 작성) | ship    |
| `fact-extraction.md`      | Memory Bank fact 추출 기준/명령 가이드 | ship/long-run |
| `telemetry-event.md`     | per-task 이벤트 로그 (stage 전환, token 사용, boundary alert) | long-run |
| `metrics-dashboard.md`   | 기간별 집계 리포트 (stage 소요, 실패 분포, token 비용) | long-run |
| `evidence-manifest.md`    | deprecated compatibility stub; 새 태스크에서는 `ship-summary.md` Evidence Manifest 사용 | legacy read-only |
| `re-execution-conditions.md` | deprecated compatibility stub; 새 태스크에서는 `checkpoint.md` Re-Execution Conditions 사용 | legacy read-only |

telemetry 산출물은 같은 프로젝트 저장소의 `telemetry/` 아래에 기록됩니다: `<task-id>.md` (이벤트 로그), `summary.md` (집계 리포트). 기본 경로는 `~/.forgeflow/projects/<project-slug>/telemetry/`입니다.

### 실사용 surface 정기 점검

ForgeFlow maintainer는 2~4주마다 문서상 존재하는 기능이 아니라 실제로 자주 쓰인 entrypoint와 산출물을 확인합니다.

```bash
make usage-audit
```

이 명령은 최근 28일 git history의 `/forgeflow:*` 언급과 현재 resolved `tasks/` directory, resolved telemetry directory (`~/.forgeflow/projects/<project-slug>/telemetry/` by default) 산출물을 집계해 `<telemetry-dir>/surface-usage-audit.md`를 생성합니다. 결과는 제거 명령이 아니라 유지보수 신호입니다.

- Core 5개가 `clarify → plan/execute → review → ship`으로 수렴하는지 확인합니다.
- Support/Utility surface가 낮은 사용 빈도에도 README/skill 인지 비용을 만들고 있지 않은지 확인합니다.
- 2회 연속 low-use인 항목은 유지 사유를 문서화하거나 병합/삭제 후보로 올립니다.
- 반복 review finding은 `review-report.md`의 Harness Follow-up으로 eval/skill/template/docs 개선에 연결합니다.

`review-report.md`의 **Execute Micro-Gates** 테이블(high/epic)은 execute 단계의 `micro_spec` / `micro_quality` 증거를 stage review가 reported로 받아 재검증할 때 씁니다.

이 repo 안의 일부 `.forgeflow/tasks/*` 폴더는 검증 fixture로 의도적으로 tracked 상태입니다. 일반 consumer 프로젝트에서는 `.forgeflow/`를 gitignore에 두는 것이 기본이며, 자세한 기준은 [docs/dogfooding.md](docs/dogfooding.md)를 참고하세요.

## Subagent execute (opt-in, high/epic)

기본 `/forgeflow:execute`는 컨트롤러가 구현하고 필요 시 일부 step만 subagent에 위임합니다.

**plan step마다** implementer → spec micro-review → quality micro-review 루프를 강제하려면 `--subagent-per-task` 플래그를 사용합니다.

```text
/forgeflow:execute --subagent-per-task
```

- **When:** high/epic, 승인된 `plan.md`, 독립 파일 스코프의 step
- **Prompts:** `skills/execute/references/*.md`
- **Not a substitute for** `/forgeflow:ff-review` — stage review는 여전히 필수
- **Claim marker:** subagent/parallel pass를 시작하기 전에 `ledger.md`의 해당 task에 `Claim Marker: role=<...> scope=<...> at=<ISO8601>`를 기록합니다. Marker 기록 후 같은 task row를 다시 읽어 role/scope/timestamp가 그대로인지 확인한 뒤 진행합니다. 다른 claim이 보이면 덮어쓰지 말고 controller handoff로 중단합니다. Direct sequential controller work는 `Claim Marker: none`을 사용합니다.

자세한 절차는 [`skills/execute/SKILL.md`](skills/execute/SKILL.md)의 Subagent Per-Task Loop와 [`skills/forgeflow/SKILL.md`](skills/forgeflow/SKILL.md)의 Review depth by route를 참고하세요.

## 독립 리뷰 (Standalone Review)

v1.1.4부터 `/forgeflow:ff-review`를 파이프라인(execute 후속) 없이도 독립적으로 실행할 수 있습니다.

```text
# PR 리뷰
/forgeflow:ff-review https://github.com/org/repo/pull/42

# 특정 디렉토리 보안 리뷰
/forgeflow:ff-review --type security ./src/auth/

# diff 파일 리뷰
/forgeflow:ff-review ./changes.patch

# 전체 역할 리뷰
/forgeflow:ff-review --type all ./src/
```

지원 입력: URL(GitHub PR/commit/compare, 일반 웹페이지), 로컬 repo 경로, diff/patch 텍스트 또는 `.diff`/`.patch` 파일, 파일 묶음, 기존 artifact

지원 역할: `spec`, `quality`(기본), `architecture`, `security`, `ux`, `perf`, `all`(전체)

각 reviewer role은 같은 입력을 공유하더라도 독립적으로 근거를 남깁니다. Finding에는 role, checklist version, evidence source, evidence level(`observed | reported | missing`)을 포함하고, role별 evidence requirement는 [`skills/ff-review/references/role-checklists.md`](skills/ff-review/references/role-checklists.md)에 둡니다. 역할 시작 전 lead reviewer는 `normalized-input.md`만 근거로 role input packet(트리거 결정, 허용 evidence IDs, scoped files/ranges/exclusions, constraints/focus, visible limitations, Evidence Gap Register entries, packet freshness)을 넘기고 `role input packet readiness`를 `READY`/`BLOCKED`/`SKIPPED`로 고정해야 하며, packet이 없거나 `BLOCKED`이거나 chat-only/hidden provider state에 의존하면 해당 role은 blocked로 기록합니다. Finding이 0건인 role도 `review-report.md`의 role-pass record에 inspected scope/evidence, 관찰한 verification 또는 no-command rationale, limitations, Independence Check, verdict를 남겨야 하며 chat-only 완료 주장이나 implementer self-report는 독립 검증 증거가 아닙니다.

Harness가 role별 model/profile을 고를 수 있으면 `normalized-input.md`의 `role capability hints`에 provider-neutral capability(`strongest reasoning available`, `standard reasoning/coding model`, `not_applicable`)로만 남깁니다. 이 값은 audit metadata이며 role routing, evidence IDs, evidence level, verdict, approval rule, human gate를 바꾸면 안 됩니다.

여러 reviewer pass를 병렬/위임으로 실행하더라도 team runtime을 만들지 않습니다. 하나의 lead reviewer만 input normalization, role routing, `review-report.md` aggregation, cross-role conflict visibility, human gate recommendation을 소유합니다. standalone normalization은 reviewer judgment 전에 `normalized-input.md`의 review ownership plan에 lead reviewer, member assignments, aggregation owner, no-child-work policy, conflict policy, product-mutation policy를 기록합니다. 각 member reviewer는 정확히 하나의 assigned pass/section만 맡고, 시작 전에 markdown claim marker(`role=<reviewer> scope=<artifact section/evidence IDs> at=<ISO8601>`)를 남깁니다. member는 새 role 생성, scope 확장, product file 수정, unmanaged child work 생성, conflict의 비공개 해결이 금지됩니다. unresolved cross-role conflict는 `review-report.md`에 남기고 Human Review Gate로 올립니다.

Reviewer role이 role evidence map 밖의 자료가 필요하다고 판단하면 바로 판단하지 않고 Evidence Escalation Log에 요청을 남깁니다. lead reviewer는 새 evidence ID를 `normalized-input.md`에 추가하고 `input-source.md` Evidence Source Map에 provenance를 연결하거나, 자료를 unavailable로 표시해 해당 role을 blocked/limited로 기록합니다. 이후 role evidence map, role input packet readiness, role input packet을 최신 evidence/scope/constraint/routing 상태로 refresh하기 전에는 해당 role 판단을 재개하지 않습니다.

Review tool posture는 inspection-only입니다. external-system access to read-only evidence fetching 원칙에 따라 PR/issue/CI/deploy 같은 외부 시스템은 read-only fetch evidence로만 다룹니다. issue comment, PR review/approval, label 변경, CI dispatch, deploy, state-changing API call은 review 단계에서 금지됩니다. 이런 조치가 필요하면 finding으로 기록하고 execute 또는 ship으로 handoff합니다.

독립 모드에서는 synthetic task directory(`~/.forgeflow/projects/<project-slug>/tasks/standalone-<timestamp>/`)가 생성되며, AI 리뷰 결과는 참고 자료(advisory)이고 최종 판단은 사람이 내립니다.

Review runtime contract는 [docs/review-runtime-contract.md](docs/review-runtime-contract.md)에 고정되어 있습니다. 핵심은 adapter-neutral input normalization(`brief / evidence / scope / constraints`), thin adapter, role-separated findings, evidence levels(`observed | reported | missing`), read-only review tool surface입니다.

독립 리뷰의 산출물 계약:

- `input-source.md`: 입력 타입, 원본 입력, fetch command/source, fetch status, `fetched_at` timestamp/run label, `freshness_status`, access posture, mutation check, 복수 fetch 사용 시 evidence ID별 Fetch Method Ledger, 누락/잘림 evidence, evidence ID별 source map 기록
- `input-source.md`는 source classification rationale도 기록해 어떤 신호로 입력 타입을 골랐고, 가능한 ambiguity를 어떻게 처리했는지 남깁니다.
- `normalized-input.md`: `brief / evidence / scope / constraints` 4-field 구조로 정규화하고, constraints에는 `--type` 때문에 무시된 `--focus` 같은 ignored flags를 남기며, stable evidence IDs, per-item fetch status/limitations/freshness, role trigger matrix, role evidence map, role input packet readiness, review ownership plan으로 각 리뷰어 역할의 실행/스킵 근거, 인용 가능한 증거, 판단 전 READY/BLOCKED/SKIPPED 상태, lead/member 소유권을 고정
- `normalized-input.md`: adapter handoff checklist는 `fetch_ledger_complete`를 포함해 복수 fetch evidence의 모든 Evidence Source Map `fetch_id`가 `input-source.md` Fetch Method Ledger row로 해소되는지 확인합니다.
- `normalized-input.md`: evidence integrity check는 모든 인용 evidence ID가 `input-source.md` Evidence Source Map과 type/fetch status/`fetched_at`/`freshness_status`/evidence level이 일치하는지 확인하며, stale/unknown evidence는 limitation 또는 Evidence Gap Register에 드러나기 전까지 reviewer judgment를 막습니다.
- `review-report.md`: standalone input source summary는 Fetch Method Ledger row, Evidence Source Map references, Adapter Handoff Checklist(`fetch_ledger_complete` 포함)를 echo해, 독자가 report만 보고도 finding/role summary evidence가 어떤 multi-fetch provenance에 묶였고 handoff가 PASS/FAIL인지 확인할 수 있어야 합니다.
- `normalized-input.md`: role capability hints는 역할별 model/profile 선택을 capability 수준으로 기록하는 선택적 audit metadata이며, review semantics를 바꾸지 않습니다.
- `normalized-input.md`: `constraints.roles`, role trigger matrix, role evidence map이 서로 일치해야 합니다. constraints에 있는 role은 matrix에서 `run` 또는 `blocked`이고 evidence map에 evidence IDs 또는 blocked rationale이 있어야 하며, matrix에서 `run`인 role은 constraints에도 있어야 합니다.
- `normalized-input.md`: adapter handoff checklist도 포함해 source classified, fetch reproduced, fetch ledger complete(`fetch_ledger_complete`), fetch posture constrained, normalization complete, limitations visible, canonical review ownership을 reviewer judgment 전에 PASS/FAIL로 고정
- `review-report.md`: 단일 최종 리뷰 산출물. Standalone Input Source 요약은 fetch status/`fetched_at`/`freshness_status`/access posture/mutation check를 echo해 독자가 정규화 산출물을 다시 열지 않아도 evidence freshness와 read-only/verification-only posture를 확인할 수 있어야 합니다. adapter별 별도 report나 자동 승인 경로 없음

리뷰 단계는 코드 수정/브랜치 정리/ship을 하지 않습니다. 문제가 발견되면 `review-report.md`에 finding으로 남기고 execute 단계로 돌려보냅니다.

## Auto 모드 (`--auto`)

`--auto` 플래그로 clarify 진입 시 한 번의 승인으로 전체 라우트를 자동 체이닝합니다.

```text
/forgeflow:clarify --auto 로그인 페이지에 소셜 로그인 버튼 추가
# → clarify → plan → execute → review → ship 자동 진행
```

**체인 순서 (라우트별):**

- **small:** clarify → execute → review → ship
- **medium:** clarify → plan → execute → review → ship
- **high/epic:** clarify → plan → execute → review(spec) → review(quality) → ship

**자동으로 멈추는 조건 (auto-break):**

- 검증 실패 (빌드/린트/테스트) 후 자동 수정 불가
- 리뷰 결과 `changes_requested`
- 파괴적 작업 (브랜치 삭제, force-push)
- brief 범위를 벗어나는 스코프 변경
- 필수 산출물 누락, 외부 의존성 장애
- context 한계 — 다음 턴에서 체인 자동 재개

**`--auto`가 우회하지 않는 것:**

- `--real` 외부 실행 안전 확인
- ship 브랜치 처리 선택 (merge/PR/keep/discard)
- discard 최종 확인
- ship 품질 루프백

관련 플래그: `--yes` / `--auto-approve` (현재 스테이지만 승인), `--non-interactive` (대화형 프롬프트 억제)

상세 규칙: [skills/_shared/automation.md](skills/_shared/automation.md)

### 기본 활성화

```text
/forgeflow:ff-config
```

실행하면 설정 메뉴가 나오고, 번호만 누르면 토글됩니다:

```
ForgeFlow 설정

1. auto (자동 체이닝)  — 현재: 꺼짐
2. 종료

번호를 선택하세요: 1
→ auto 활성화됨. <storage-root>/defaults.md에 저장되었습니다.
```

**우선순위:** `--auto` 플래그 > `brief.md` auto 필드 > `<storage-root>/defaults.md` > 기본값(`false`)

자연어로 `"auto로 진행해"`, `"모든 단계 자동으로 해"`라고 해도 동일하게 동작합니다.

상세 설정: [docs/adapter-config.md](docs/adapter-config.md) → Project Defaults

## 특징

- **의존성 제로** — Python, Node.js 등 외부 런타임 불필요
- **순수 Markdown** — 모든 산출물이 사람이 읽을 수 있는 markdown
- **프롬프트 기반** — 스크립트가 아닌 프롬프트 지시로 강제
- **멀티 플랫폼** — Claude Code, Codex, Gemini CLI, Cursor(로컬 플러그인) 지원

어댑터별 CLI 플래그, 타임아웃, 감지 방법: [docs/adapter-config.md](docs/adapter-config.md)

루트에는 현재 marketplace/extension 호환성을 위해 `.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `.gemini`, `.agents`, `plugins/`, `gemini-extension.json`가 남아 있습니다. 새 어댑터 surface를 추가하거나 정리할 때는 [docs/adapter-layout.md](docs/adapter-layout.md)의 `adapters/` 수렴 원칙을 따릅니다.

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

v1.1.0부터 evolution rule 생성은 ship 단계에서 직접 처리합니다. 별도 `proposed` → `review` 중간 단계가 없으며, review가 이미 작업을 검증했으므로 ship이 evidence 기반 규칙을 `active/`에 바로 기록합니다.

- `observe` (ship)
  - 트리거: ship이 task artifacts(`implementation-notes.md`, `review-report.md`, `eval-record.md`)에서 재사용 가능한 패턴을 식별
  - 산출물/위치: 기존 task artifacts (별도 산출물 없음)
- `extract` (ship)
  - 트리거: evidence가 확인된 재사용 가능한 패턴이 기존 active rule으로 이미 커버되지 않음
  - 산출물/위치: compact 6-line format으로 `active/`에 직접 작성
    - global-advisory (기본): `~/.forgeflow/evolution/active/<rule-name>`
    - project: `.forgeflow/evolution/active/<rule-name>`
  - small 라우트는 추출 건너뜀, medium은 최대 1-2개, high/epic은 full extraction
- `active`
  - 트리거: rule 파일이 `active/` 디렉토리에 존재
  - 산출물/위치: `~/.forgeflow/evolution/active/*` (global) 또는 `.forgeflow/evolution/active/*` (project)
  - 다음 단계: 향후 clarify/plan/execute에서 trigger/stage 일치 시 자동 로드
- `retired`
  - 트리거: 규칙이 해롭거나 더 이상 맞지 않음
  - 산출물/위치: `.forgeflow/evolution/retired/` (project) 또는 `~/.forgeflow/evolution/retired/` (global), retirement reason 포함
  - 다음 단계: retirement reason 기록 후 로드하지 않음

Project active rule은 해당 repository의 필수 제약입니다.
Global rule(`~/.forgeflow/evolution/active/*`)은 advisory only이며 hard block으로 쓰지 않습니다.

## 로컬 검증

이 저장소는 v1.x 기준으로 runtime/build 의존성이 없는 Markdown/JSON 패키지입니다. 변경 전후에는 GitHub Actions의 구조 검증 계약(`.github/workflows/validate.yml`)과 같은 핵심 범위를 로컬에서 먼저 확인합니다.

```bash
make validate
```

`make validate`는 Python runtime 파일 재유입, tracked legacy runtime/schema/test directories are absent, 활성 문서의 제거된 runtime/schema/test tree 참조 재유입, GitHub Actions workflow가 문서화된 로컬 검증 bundle을 호출하는지와 read-only `contents: read` permissions를 쓰는지, 플러그인/extension JSON 파싱, release version/CHANGELOG 링크, public skill `SKILL.md` 존재 및 frontmatter `name`/`description`/`validate_prompt` 정합성, 필수 템플릿 존재 여부, 첫 성공 데모 산출물 생성, skill→template cross-reference, Gemini skill imports, plugin defaultPrompt 매핑, adapter config 계약, stage tool boundary artifact ownership/read-only review posture, workflow vocabulary(활성 문서의 제거된 slash command 재유입 포함), ship branch-disposition safety, advisory contract, eval fixture 계약, `evals/evals.json` 계약(정수형 순차 `id`, 고유 `name`, assertion shape, repo-relative·git-tracked `files` 참조 포함), Markdown inline/reference/collapsed-reference 상대 링크, 중복 reference definition, HTML href/src, 이미지, anchor를 code span 밖에서 확인합니다. `make validate`는 live provider/plugin E2E를 실행하지 않습니다. 개별 명령으로 확인할 때는 아래와 같습니다.

```bash
# Python runtime 파일이 다시 들어오지 않았는지 확인
make validate-no-python

# 활성 문서가 제거된 runtime/schema/test tree를 다시 참조하지 않는지 확인
make validate-slim-surface

# route scoring 공식이 README/SKILL/clarify 계약 사이에서 드리프트되지 않는지 확인
make validate-route-scoring-parity

# release VERSION/manifest와 CHANGELOG compare 링크 정합성 확인
make validate-versions validate-changelog-links

# 플러그인/extension JSON 파싱 확인
make validate-json

# public skill inventory/frontmatter 계약과 root SKILL.md marketplace summary linkage 확인
make validate-skills

# 템플릿 존재 여부와 skill→template 참조 확인
make validate-templates validate-template-refs

# adapter CLI/config 문서와 README quickstart 계약만 빠르게 확인
make validate-adapter-config

# stage별 artifact ownership과 review read-only tool posture 확인
make validate-stage-tool-boundaries

# 문서/스킬 링크가 repo-relative로 깨지지 않고 reference definition이 중복되지 않는지 확인
make validate-markdown-links

# 첫 성공 데모 산출물/README 계약만 빠르게 확인
make validate-demo

# GitHub Actions workflow가 로컬 검증 bundle과 드리프트되지 않는지 확인
make validate-ci-workflows

# English README가 핵심 설치/산출물/검증 표면과 드리프트되지 않는지 확인
make validate-english-readme

# AGENTS.md, maintainer preflight, shared discipline/automation linkage 계약만 빠르게 확인
make validate-agent-docs

# Gemini import와 plugin prompt 매핑만 빠르게 확인
make validate-gemini-imports validate-plugin-prompts

# workflow vocabulary, ship safety, dogfooding/context-resume/advisory 계약만 빠르게 확인
make validate-workflow-vocab validate-ship-safety validate-dogfooding-docs validate-context-resume validate-advisory-contract

# eval fixture 계약만 빠르게 확인
make validate-evals
# 또는 특정 lane 디버깅 시:
make validate-evals-json validate-eval-files validate-evals-fixtures
```

각 focused target은 exit code 0이면 통과이며, 실패 시 어떤 계약이 깨졌는지 출력합니다. 특히 [첫 성공 데모](#첫-성공-데모)는 provider/plugin 없이 산출물 위치를 확인하는 안전한 smoke입니다. push/PR에서는 상단 badge와 연결된 `.github/workflows/validate.yml`의 `validate` workflow가 전체 `make validate`를, `.github/workflows/evals.yml`의 `evals` workflow가 eval fixture 계약(`make validate-evals`; 내부적으로 `validate-evals-json`, `validate-eval-files`, `validate-evals-fixtures`)을 검사합니다. 두 workflow 모두 read-only `contents: read` permissions를 사용합니다. eval fixture를 추가하거나 수정할 때는 [evals/README.md](evals/README.md)의 로컬 체크리스트를 따릅니다.

### 첫 성공 데모

로컬 checkout만으로 산출물 위치와 템플릿 구성을 빠르게 확인하려면 다음을 실행합니다. 실제 provider/plugin E2E가 아니라, 임시 workspace에 핵심 task 산출물 템플릿을 복사해 첫 실행 결과의 파일 구조를 보여주는 안전한 데모입니다.

```bash
make demo
```

이 명령은 `mktemp -d` 아래에 `.forgeflow/tasks/demo-small/`을 만들고 `brief.md`, `plan.md`, `ledger.md`, `checkpoint.md`, `run-state.json`, `implementation-notes.md`, `review-report.md`, `ship-summary.md` 경로를 출력합니다. repo 안에 `.forgeflow/`를 만들거나 추적 파일을 수정하지 않으므로, 첫 clone 직후나 자동화 preflight에서 안전하게 실행할 수 있습니다. 생성된 임시 workspace를 열어 실제 작업에서는 `/forgeflow:clarify`부터 시작하세요.

### Claude 설치 플러그인 E2E smoke

`make demo`는 provider/plugin을 호출하지 않는 안전한 local smoke입니다. 실제 Claude Code에 설치된 ForgeFlow plugin이 현재 release와 맞는지 보려면, 대상 프로젝트와 분리된 disposable sample workspace에서 설치 버전 smoke를 별도로 실행합니다.

1. 설치된 plugin 버전 확인 및 업데이트:

```bash
claude plugin list
claude plugin update forgeflow@forgeflow
claude plugin list
```

`forgeflow@forgeflow` 버전이 repo `VERSION`과 다른 경우 먼저 update/reinstall하고, Claude Code 안내처럼 새 프로세스에서 다시 실행합니다. checkout 자체를 검증할 때만 `--plugin-dir /path/to/forgeflow`를 사용하고, 설치 plugin smoke에서는 `--plugin-dir`를 빼야 실제 user-scope 설치본을 검증합니다.

2. disposable sample project에서 실제 설치 plugin 실행:

```bash
mkdir -p /tmp/forgeflow-installed-smoke/src /tmp/forgeflow-installed-smoke/tests
cd /tmp/forgeflow-installed-smoke

claude -p --permission-mode bypassPermissions \
  "Use the installed ForgeFlow plugin. Run /forgeflow:clarify --auto, /forgeflow:execute --auto, and /forgeflow:ff-review for a tiny local code change. Run the project test command and report artifact paths."
```

3. 확인 기준:

- `python3 -m pytest -q` 또는 해당 프로젝트 test command가 observed evidence로 기록됨
- `<task-dir>/brief.md`, `plan.md`, `implementation-notes.md`, `review-report.md`, `ledger.md`, `checkpoint.md`, `run-state.json`가 대상 프로젝트 아래 생성됨
- `review-report.md` verdict가 `approved`이거나, `changes_requested`의 finding이 재현 가능한 증거를 포함함
- 산출물이 ForgeFlow checkout/plugin cache가 아니라 sample project 아래에 생성됨

## 실제 외부 실행 안전 기준

v1.x는 Python `exec-stage --real` 런타임을 포함하지 않습니다.
향후 실제 Claude/Codex/Gemini CLI를 호출하는 adapter나 `--real` 경로를 다시 추가한다면 기본값은 stub/dry-run이어야 합니다.
실제 외부 호출 전에는 stderr 경고와 `[y/N]` 확인 프롬프트가 필수입니다.

## 첫 실행 예시

먼저 실제 프로젝트 루트에서 실행 중인지 확인하세요. 에이전트가 plugin cache/설치 디렉토리에서 열렸다면 `/forgeflow:clarify --task-dir ~/.forgeflow/projects/<project-slug>/tasks/<task-id>`처럼 명시 경로를 넘겨 프로젝트 안에 산출물을 만듭니다.

```text
> /forgeflow:clarify 로그인 페이지에 소셜 로그인 버튼 추가
# → 작업 공간 생성, brief.md 작성, route: medium

> /forgeflow:ff-plan
# → plan.md 생성, 실행 단계/검증 목표 확정

> /forgeflow:execute
# → 구현 진행, implementation-notes.md 업데이트

> /forgeflow:ff-review
# → 독립 review, review-report.md 생성

> /forgeflow:ship
# → ship-summary.md, handoff 요약, 브랜치 merge/PR/keep/discard 선택
```

## 라이선스

MIT
