# ForgeFlow

[![validate](https://github.com/gimso2x/forgeflow/actions/workflows/validate.yml/badge.svg)](https://github.com/gimso2x/forgeflow/actions/workflows/validate.yml) [![evals](https://github.com/gimso2x/forgeflow/actions/workflows/evals.yml/badge.svg)](https://github.com/gimso2x/forgeflow/actions/workflows/evals.yml)

ForgeFlow는 AI coding agent를 위한 artifact-first delivery workflow입니다. 채팅 기억 대신 **명시적인 markdown 산출물, 프롬프트 기반 게이트, 독립 review**로 작업을 남깁니다.

English quickstart: [README_en.md](README_en.md)

Release version source of truth: [`VERSION`](VERSION).

## 누가 왜 쓰나

- AI 코딩 에이전트로 실제 코드를 작성하는 개발자
- 작업 과정을 `brief.md`, `plan.md`, `review-report.md` 같은 산출물로 추적하려는 팀
- “에이전트가 뭘 했는지 모르겠다”를 줄이고 싶은 사람

ForgeFlow에는 coding agent behavior guardrails도 포함됩니다: assumption surfacing, simplicity-first implementation, surgical diffs, goal-driven verification. 로컬 focused 검증은 `make validate-behavior-guardrails`입니다.

## 30초 퀵스타트

**Claude Code:**

```text
/plugin marketplace add https://github.com/gimso2x/forgeflow
/plugin install forgeflow
```

**Gemini CLI:**

```bash
gemini extensions install https://github.com/gimso2x/forgeflow
printf 'Y\n' | gemini extensions update forgeflow
gemini extensions list
```

개발 중인 checkout은 `gemini extensions validate .` 후 `gemini extensions link .`로 연결합니다.

**Cursor (로컬 플러그인):**

```bash
mkdir -p ~/.cursor/plugins/local
ln -s /path/to/forgeflow ~/.cursor/plugins/local/forgeflow
```

Cursor 명령은 콜론 없음: `/clarify`, `/ff-plan`, `/execute`, `/ff-review`, `/ship`.

**Codex (CLI + Codex App):**

Marketplace 권장:

```bash
codex plugin marketplace add gimso2x/forgeflow
codex plugin add forgeflow@forgeflow
codex plugin list
```

로컬 설치 타겟은 **대상 프로젝트 루트**에서 실행합니다. ForgeFlow repo나 Codex plugin cache 안에서 실행하면 산출물이 잘못된 위치에 생길 수 있습니다.

```bash
make -C /path/to/forgeflow install-codex-local CODEX_LOCAL_PLUGIN_DIR="$PWD/.codex/plugins/forgeflow"
```

이 로컬 설치는 `.codex/plugins/forgeflow` 아래에 `plugin.json`, `skills/`, `templates/`를 복사합니다.

**중요:** plugin/extension 설치 위치와 작업 위치를 분리하세요. `/forgeflow:clarify` 같은 workflow 명령은 변경하려는 프로젝트 루트에서 실행합니다. 기본 task 산출물은 `~/.forgeflow/projects/<project-slug>/tasks/<task-id>/`에 기록됩니다. plugin cache에서 열렸다면 `--task-dir ~/.forgeflow/projects/<project-slug>/tasks/<task-id>`를 명시하세요.

## 기본 워크플로우

Core만 익히면 됩니다.

```text
/forgeflow:ff-config  → 설정 메뉴
/forgeflow:clarify    → 작업 공간 생성 + 요구사항 정리 → brief.md
/forgeflow:ff-plan    → 작업 계획 → plan.md
/forgeflow:execute    → 구현 실행 → implementation-notes.md
/forgeflow:ff-review  → 독립 검증 → review-report.md
/forgeflow:ship       → ship-summary.md + branch disposition
```

`/forgeflow:long-run`은 high/epic ship 후 학습 기록(`eval-record.md`)에 사용합니다. 흐름은 `ship → long-run`입니다.

## Routes (자동 선택)

clarify가 복잡도를 평가해 route를 고릅니다.

| Route | Stages | When |
| --- | --- | --- |
| small | clarify → execute → ship | 저위험, 소규모, 쉬운 롤백 |
| medium | clarify → plan → execute → review → ship | 범위 명확, 검증 필요 |
| high | clarify → plan → execute → review(spec) → review(quality) → ship → long-run | 아키텍처 영향, 롤백 어려움 |
| epic | clarify → plan(epic decomposition) → execute → review(spec) → review(quality) → ship → long-run | 대규모, 멀티윅 |

high/epic의 spec/quality review는 별도 slash command가 아니라 같은 `/forgeflow:ff-review` 안의 pass 깊이 차이입니다.

### Route scoring

```text
raw_score = file_count*1.0 + estimated_lines*0.1 + requirement_count*2.0 + dependency_count*1.5 + risk_keywords*3.0
```

| Score | Route 판단 |
| ---: | --- |
| `< 10` | small |
| `10-16.9` | medium-light |
| `17-24.9` | medium-full |
| `25-49.9` | high |
| `>= 50` | epic |

`17.0`은 medium을 light/full로 가르는 `mid_threshold`입니다.

## Artifacts

기본 저장 위치:

```text
~/.forgeflow/projects/<project-slug>/tasks/<task-id>/
```

`project-slug`는 기본적으로 repo basename입니다. 같은 이름의 checkout이 충돌하면 절대 경로 해시를 붙입니다. 모든 task는 `run-state.json`에 `repo_root`, `project_name`, `project_slug`, `storage_root`, `task_id`를 남겨 원본 프로젝트를 복원합니다.

Installed plugin smoke 기준은 `<task-dir>/brief.md`, `plan.md`, `implementation-notes.md`, `review-report.md`, `ledger.md`, `checkpoint.md`, `run-state.json` 존재 여부입니다.

필수 산출물:

| 산출물 | 생성 route/stage |
| --- | --- |
| `brief.md` | 전체 |
| `run-state.json` | clarify |
| `plan.md` | medium+ |
| `ledger.md` | execute |
| `checkpoint.md` | execute |
| `implementation-notes.md` | 전체 |
| `review-report.md` | 전체 |
| `ship-summary.md` | 전체 |
| `project-draft.md` | full init |
| `roadmap.md` | epic |
| `eval-record.md` | high+ |
| `input-source.md`, `normalized-input.md` | standalone review |
| `evidence-manifest.md`, `metrics-dashboard.md`, `telemetry-event.md` | evidence/telemetry |
| `fact-extraction.md`, `evolution-rule.md`, `re-execution-conditions.md` | learning/replay |

Telemetry는 `~/.forgeflow/projects/<project-slug>/telemetry/` 아래에 기록합니다.

Evolution lifecycle은 단순화되어 별도 `proposed`/`review` 중간 디렉터리를 두지 않습니다. ship 단계가 observe → extract 흐름으로 증거를 관찰하고 재사용 가능한 규칙을 추출한 뒤 evolution rule 생성은 ship 단계에서 직접 처리합니다. long-run은 candidate notes와 재실행 조건만 넘깁니다.

## 독립 리뷰 (Standalone Review)

`/forgeflow:ff-review`는 파이프라인 없이도 PR, diff, 디렉터리, 기존 artifact를 검토할 수 있는 1급 진입점입니다. 전체 `clarify → plan → execute`를 돌리지 않아도 리뷰 산출물(`input-source.md`, `normalized-input.md`, `review-report.md`)을 바로 남깁니다.

```text
/forgeflow:ff-review https://github.com/org/repo/pull/42
/forgeflow:ff-review --type security ./src/auth/
/forgeflow:ff-review ./changes.diff
/forgeflow:ff-review HEAD~3..HEAD
```

지원 입력은 URL, GitHub PR/commit/compare, repo path, git range, `.diff`/`.patch` 파일, file bundle, existing artifact, ambiguous 입력입니다. standalone review는 먼저 입력을 `brief / evidence / scope / constraints`로 정규화한 뒤 판단합니다.

Standalone report 품질 기준:
- 모든 non-nit finding은 `Evidence Source`, `Evidence Level`, **Evidence Quote**를 가져야 합니다. 느낌표 리뷰 금지. 증거 없으면 finding이 아니라 evidence gap입니다.
- `Severity`는 `blocker | major | minor | nit` 중 하나입니다.
- `blocker`가 하나라도 있으면 `Finding Counts`의 `blockers=N`과 `Open Blockers`에 동시에 보여야 하며, verdict는 `approved`가 될 수 없습니다. approved-with-blockers는 없다 — 그건 승인 흉내 낸 보류입니다.
- Human Review Gate는 AI 리뷰를 자동 승인으로 바꾸지 않습니다.

Review runtime contract는 [docs/review-runtime-contract.md](docs/review-runtime-contract.md)에 고정됩니다. 핵심은 adapter-neutral input normalization(`brief / evidence / scope / constraints`), `input-source.md`, `normalized-input.md`, source classification rationale, role trigger matrix, role별 evidence requirement, role evidence map, role input packet, packet freshness, constraints.roles, role capability hints, review ownership plan, conflict policy, ignored flags, Evidence Escalation Log, fetch ledger complete(`fetch_ledger_complete`), fetch posture constrained, Fetch Method Ledger, Evidence Source Map, Adapter Handoff Checklist, access posture, mutation check, `fetched_at`, `freshness_status`, read-only/verification-only posture, standalone input source summary입니다. external-system access to read-only evidence fetching만 허용되며 Evidence Source Map과 type/fetch status/`fetched_at`/`freshness_status`/evidence level은 일치해야 합니다.

Local loop runtime contract는 [docs/local-loop-runtime-contract.md](docs/local-loop-runtime-contract.md)에 고정됩니다. 핵심은 route별 상태 전이, failure type, retry budget, route promotion/demotion, evidence requirement, human gate입니다. 로드맵은 [docs/local-loop-runtime-roadmap.md](docs/local-loop-runtime-roadmap.md)에 둡니다.

Maintainer backlog는 [docs/maintainer-backlog.md](docs/maintainer-backlog.md)에 둡니다. [docs/roadmap-improvements.md](docs/roadmap-improvements.md)는 historical/archive design notes이며 live queue가 아닙니다.

Multi-harness 원칙: route, artifact schema, review verdict, human gate는 adapter-neutral core contract입니다. hidden provider state나 chat transcript가 아니라 `<task-dir>` 산출물로 handoff합니다. adapter별 별도 report나 자동 승인 경로 없음.

역할 경계 원칙: planner/worker/reviewer/lead/member 같은 역할명은 stage-owned pass의 책임 경계를 설명할 뿐, 별도 팀 런타임이나 hidden approval path가 아닙니다. lead reviewer만 normalization과 aggregation을 소유하고, member reviewer는 하나의 pass/section만 맡습니다. unmanaged child work 금지. claim marker는 `role=<reviewer> scope=<artifact section/evidence IDs> at=<ISO8601>` 형식입니다.

## Auto 모드 (`--auto`)

```text
/forgeflow:clarify --auto 로그인 페이지에 소셜 로그인 버튼 추가
```

라우트별로 clarify 이후 단계를 자동 체이닝합니다. 검증 실패, `changes_requested`, 파괴적 작업, scope creep, 필수 산출물 누락, context 한계에서는 멈춥니다.

## Context refresh / resume

Stage 경계나 checkpoint 갱신 직후 context refresh가 안전합니다. 재개 시 `checkpoint.md` → `ledger.md` → `implementation-notes.md` 요약 → 필요한 섹션만 읽습니다. 상세 규칙은 [skills/_shared/context-resume.md](skills/_shared/context-resume.md)를 따릅니다. `checkpoint.md`의 `Handoff Boundary`는 forbidden-action delegation 기록이며 현재 stage owner, 다음 owner, handoff reason, requested/forbidden action, evidence/artifact trigger, blocker/limitation impact, explicit stop condition, exact artifact update location을 기록합니다.

## 로컬 검증

기본은 하나입니다.

```bash
make validate
```

`make validate`는 문서/JSON/skill/template/link/route/release/adapter/eval 계약을 검사합니다. live provider/plugin E2E를 실행하지 않습니다. Markdown link 검증은 HTML href/src 링크도 포함합니다. 큰 workflow skill은 `docs/skill-modularization.md` 정책에 따라 shared/reference로 쪼개졌는지도 검사합니다.

자주 쓰는 focused target:

```bash
make validate-slim-surface        # tracked legacy runtime/schema/test directories are absent
make validate-english-readme
make validate-route-scoring-parity
make validate-versions validate-changelog-links
make validate-json
make validate-skills                # root SKILL.md marketplace summary 포함
make validate-skill-modularity      # docs/skill-modularization.md 기반 대형 skill reference 분리 검증
make validate-agent-docs            # shared discipline/automation linkage 포함
make validate-templates validate-template-refs
make validate-template-fields
make validate-adapter-config
make validate-stage-tool-boundaries
make validate-markdown-links
make validate-demo
make validate-forgeflow-loop       # scripts/forgeflow_loop.py markdown loop CLI smoke
make smoke-local-plugins            # opt-in, local-only plugin/provider boundary smoke
make validate-evals
```

CI도 같은 계약을 씁니다: `.github/workflows/validate.yml`은 `make validate`, `.github/workflows/evals.yml`은 `make validate-evals`를 실행하며 둘 다 read-only `contents: read` permissions를 사용합니다.

### 첫 성공 데모

```bash
make demo
```

provider/plugin 없이 임시 workspace에 `.forgeflow/tasks/demo-small/` 산출물을 만들어 위치와 템플릿 구성을 보여주는 안전한 smoke입니다. 실제 provider/plugin E2E가 아니라 template copy 검증이며, 임시 디렉터리만 쓰고 추적 파일을 수정하지 않으므로 repo-local artifacts는 남지 않습니다. focused 검증은 `make validate-demo`입니다.

### Opt-in plugin/provider boundary smoke

```bash
make smoke-local-plugins
```

이 target은 live Claude/Codex/Cursor/Gemini CLI를 호출하지 않습니다. 대신 plugin manifest, slash command namespace, Gemini context import, Codex local install copy surface를 임시 디렉터리에서 검증합니다. 기본 `make validate`에는 포함하지 않습니다. credential이나 provider CLI 유무에 따라 기본 검증이 흔들리면 그건 검증이 아니라 지뢰입니다.

## Release version policy

루트 `VERSION` 파일이 단일 버전 기준입니다. README 본문에는 현재 릴리즈 버전을 고정하지 않습니다. `SKILL.md`는 루트 marketplace summary입니다. `skills/*/SKILL.md` 같은 public skill의 Per-skill frontmatter `version`은 skill schema version이며 릴리즈 `VERSION`과 별개입니다.

CI는 `VERSION`, `CHANGELOG.md`, `SKILL.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `gemini-extension.json` 정합성을 봅니다.

## 실제 외부 실행 안전 기준

v1.x는 Python `exec-stage --real` 런타임을 포함하지 않습니다. 향후 실제 Claude/Codex/Gemini CLI 호출 adapter나 `--real` 경로를 다시 추가한다면 기본값은 stub/dry-run이어야 하고, 실제 외부 호출 전 stderr 경고와 `[y/N]` 확인 프롬프트가 필수입니다.

## 첫 실행 예시

먼저 실제 프로젝트 루트에서 실행 중인지 확인하세요. 에이전트가 plugin cache/설치 디렉토리에서 열렸다면 `/forgeflow:clarify --task-dir ~/.forgeflow/projects/<project-slug>/tasks/<task-id>`처럼 명시 경로를 넘깁니다.

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

## 더 깊게 보기

- Adapter config: [docs/adapter-config.md](docs/adapter-config.md)
- Review contract: [docs/review-runtime-contract.md](docs/review-runtime-contract.md)
- Local loop runtime contract: [docs/local-loop-runtime-contract.md](docs/local-loop-runtime-contract.md)
- Local loop runtime roadmap: [docs/local-loop-runtime-roadmap.md](docs/local-loop-runtime-roadmap.md)
- Dogfooding: [docs/dogfooding.md](docs/dogfooding.md)
- Benchmark: [skills/benchmark/SKILL.md](skills/benchmark/SKILL.md)

## 라이선스

MIT
