# ForgeFlow

[![validate](https://github.com/gimso2x/forgeflow/actions/workflows/validate.yml/badge.svg)](https://github.com/gimso2x/forgeflow/actions/workflows/validate.yml) [![evals](https://github.com/gimso2x/forgeflow/actions/workflows/evals.yml/badge.svg)](https://github.com/gimso2x/forgeflow/actions/workflows/evals.yml)

ForgeFlow는 AI coding agent용 **artifact-first** delivery workflow입니다. 채팅 기억 대신 markdown 산출물, 프롬프트 게이트, 독립 review로 작업을 남깁니다. 릴리즈 기준은 [`VERSION`](VERSION)이고, public skill의 Per-skill frontmatter `version`은 **skill schema** 버전이며 릴리즈 `VERSION`과 별개입니다.

## 30초 퀵스타트

**중요:** plugin/extension **설치 위치와 작업 위치를 분리하세요.** workflow 명령은 변경 대상 **프로젝트 루트**에서 실행하고, 산출물은 `~/.forgeflow/projects/<project-slug>/tasks/<task-id>/`에 기록합니다. plugin cache에서 열렸다면 `--task-dir`를 명시하세요.

| Adapter | 설치 |
| --- | --- |
| Claude Code | `/plugin marketplace add https://github.com/gimso2x/forgeflow` → `/plugin install forgeflow` |
| Codex | `codex plugin marketplace add gimso2x/forgeflow` → `codex plugin add forgeflow@forgeflow` |
| Cursor | `ln -s /path/to/forgeflow ~/.cursor/plugins/local/forgeflow` — `/clarify`, `/ff-plan`, `/execute`, `/ff-review`, `/ship` |

## 기본 워크플로우

```text
/forgeflow:ff-config → /forgeflow:clarify → brief.md
medium+: /forgeflow:ff-plan → plan.md
/forgeflow:execute → implementation-notes.md
/forgeflow:ff-review → review-report.md
/forgeflow:ship → ship-summary.md
high/epic: ship → long-run → eval-record.md
```

high/epic의 spec/quality review는 별도 command가 아니라 **같은 `/forgeflow:ff-review`** pass 깊이 차이입니다.

## Routes

| Route | When |
| --- | --- |
| small | 저위험·소규모·쉬운 롤백 |
| medium | clarify → plan → execute → review → ship |
| high | 아키텍처 영향·롤백 어려움 |
| epic | 대규모·멀티윅 decomposition |

### Route scoring

`raw_score = file_count*1.0 + estimated_lines*0.1 + requirement_count*2.0 + dependency_count*1.5 + risk_keywords*3.0`

| Score | Route |
| ---: | --- |
| `< 10` | small |
| `10-16.9` | medium-light |
| `17-24.9` | medium-full |
| `25-49.9` | high |
| `>= 50` | epic |

## Artifacts

경로: `~/.forgeflow/projects/<project-slug>/tasks/<task-id>/` (`run-state.json`에 `repo_root`, `project_slug` 등 기록).

Installed plugin smoke: `<task-dir>/brief.md`, `plan.md`, `implementation-notes.md`, `review-report.md`, `ledger.md`, `checkpoint.md`, `run-state.json`.

템플릿(`templates/`): brief.md, project-draft.md, plan.md, review-report.md, implementation-notes.md, input-source.md, normalized-input.md, eval-record.md, roadmap.md, checkpoint.md, run-state.json, ledger.md, evolution-rule.md, ship-summary.md, fact-extraction.md, telemetry-event.md, metrics-dashboard.md, evidence-manifest.md, re-execution-conditions.md

Evolution: ship이 observe → extract로 증거를 관찰·추출하고, **evolution rule 생성은 ship 단계에서 직접** 처리합니다. 별도 `proposed`/`review` 중간 단계는 제거되었습니다(별도 `proposed` 디렉터리 없음).

**Multi-harness 원칙:** route·artifact schema·review verdict·human gate는 **adapter-neutral core contract**입니다. **역할 경계 원칙:** planner/worker/reviewer는 stage-owned pass 설명이며 hidden approval path가 아닙니다.

## 독립 리뷰 · Loop · Resume

`/forgeflow:ff-review`는 PR/diff/경로/artifact를 **adapter-neutral input normalization**(`brief / evidence / scope / constraints`)으로 정규화한 뒤 판단합니다. 계약: [docs/review-runtime-contract.md](docs/review-runtime-contract.md) — `input-source.md`, `normalized-input.md`, source classification rationale, role trigger matrix, role별 evidence requirement, review ownership plan, conflict policy, ignored flags, Evidence Escalation Log, role input packet, role capability hints, constraints.roles, packet freshness, fetch ledger complete(`fetch_ledger_complete`), fetch posture constrained, `fetch_ledger_complete`, `fetched_at`, `freshness_status`, access posture, mutation check, read-only/verification-only posture, Fetch Method Ledger, Evidence Source Map과 type/fetch status/`fetched_at`/`freshness_status`/evidence level, Adapter Handoff Checklist, standalone input source summary. 입력 예: URL, `.diff`/`.patch` 파일, git range. **external-system access to read-only evidence fetching**만 허용. lead reviewer / member reviewer 경계 — unmanaged child work 금지; claim marker `role=<reviewer> scope=<artifact section/evidence IDs> at=<ISO8601>`. adapter별 별도 report나 자동 승인 경로 없음. Multi-harness 원칙: adapter-neutral core contract, hidden provider state.

Loop CLI: `scripts/forgeflow_loop.py` — [docs/local-loop-runtime-contract.md](docs/local-loop-runtime-contract.md)

Context refresh: [skills/_shared/context-resume.md](skills/_shared/context-resume.md). `checkpoint.md`의 `Handoff Boundary`는 forbidden-action delegation 기록이며 현재 stage owner, 다음 owner, requested/forbidden action, evidence/artifact trigger, blocker/limitation impact, explicit stop condition, exact artifact update location을 기록합니다.

## 로컬 검증

```bash
make validate   # live provider/plugin E2E를 실행하지 않습니다
```

Windows는 Git Bash/WSL에 `make` 필요. Markdown link 검증은 **HTML href/src** 링크도 포함합니다. 큰 skill은 [docs/skill-modularization.md](docs/skill-modularization.md) 정책으로 reference 분리 검사합니다. [docs/advisory-guidelines.md](docs/advisory-guidelines.md)의 **coding agent behavior guardrails**는 `make validate-behavior-guardrails`로 검증합니다.

**Focused targets:**

```bash
make validate-slim-surface          # tracked legacy runtime/schema/test directories are absent
make validate-route-scoring-parity
make validate-versions validate-changelog-links
make validate-skills                # root SKILL.md marketplace summary 포함
make validate-agent-docs            # shared discipline/automation linkage 포함
make validate-skill-modularity
make validate-templates validate-template-refs
make validate-template-fields          # required_fields warning mode; --strict for error mode
make validate-stage-handoff            # alias: cross-artifact handoff checks (same script as template-fields)
make validate-adapter-config
make validate-stage-tool-boundaries
make validate-markdown-links
make validate-demo
make validate-forgeflow-loop
make validate-full-loop-e2e         # credential-free disposable full-loop E2E
make validate-evals
make validate-behavior-guardrails
make smoke-local-plugins            # opt-in
```

CI: `.github/workflows/validate.yml` → `make validate`, `.github/workflows/evals.yml` → `make validate-evals`, read-only `contents: read` permissions. eval fixture 검사는 `.github/workflows/evals.yml`을 참조합니다.

### 첫 실행 데모

```bash
make demo
```

`.forgeflow/tasks/demo-small/`에 brief.md, plan.md, ledger.md, checkpoint.md, run-state.json, implementation-notes.md, review-report.md, ship-summary.md를 복사하는 smoke입니다. **실제 provider/plugin E2E가 아니라** template copy 검증이며, 임시 디렉터리만 쓰고 **추적 파일을 수정하지 않으므로** repo-local artifacts는 남지 않습니다. `make validate-demo`로 확인합니다.

## 첫 실행 예시

plugin cache에서 열렸다면 `--task-dir ~/.forgeflow/projects/<project-slug>/tasks/<task-id>`를 명시하세요.

```text
> /forgeflow:clarify 로그인 페이지에 소셜 로그인 버튼 추가
# → brief.md, route: medium

> /forgeflow:ff-plan → plan.md
> /forgeflow:execute → implementation-notes.md
> /forgeflow:ff-review → review-report.md
> /forgeflow:ship → ship-summary.md
```

## 더 깊게 보기

- [docs/adapter-config.md](docs/adapter-config.md) · [docs/stage-tool-boundaries.md](docs/stage-tool-boundaries.md)
- [docs/review-runtime-contract.md](docs/review-runtime-contract.md) · [docs/local-loop-runtime-roadmap.md](docs/local-loop-runtime-roadmap.md)
- [docs/dogfooding.md](docs/dogfooding.md) · [docs/maintainer-backlog.md](docs/maintainer-backlog.md)
- [skills/benchmark/SKILL.md](skills/benchmark/SKILL.md) · [AGENTS.md](AGENTS.md)

## 라이선스

MIT
