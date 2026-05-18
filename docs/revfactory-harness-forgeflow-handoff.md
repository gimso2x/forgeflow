# revfactory/harness → ForgeFlow 흡수 실황

대상: `revfactory/harness`의 핵심 개념을 ForgeFlow에 흡수한 결과 기록. 계획이 아니라 구현된 상태 기준.

## 한 줄 결론

`revfactory/harness`를 별도 기능으로 복제하지 않고, ForgeFlow `init`이 **도메인 키워드 기반 팀 아키텍처 선택 → 에이전트/스킬/문서 초안 생성 → CLAUDE.md 포인터 등록**까지 한 번에 수행하는 구조로 흡수했다.

## 구현 상태 (2026-05-08 기준)

### 완료

- **init 초안 생성**: `orchestrator.py`의 `_init_markdown_drafts()`가 task 아래에 16개 파일을 한 번에 생성
- **팀 아키텍처 선택**: `_select_team_architecture()`가 objective 키워드 + risk level로 3가지 패턴 자동 선택
- **에이전트/스킬 분리**: `.claude/agents/` (4개) + `.claude/skills/` (4개) 생성
- **문서 초안**: PRD, ARCHITECTURE, QA, DECISIONS, init-summary, feature task, qa task
- **CLAUDE.md 포인터**: task 디렉토리에 트리거 규칙 포함된 포인터 생성
- **덮어쓰기 방지**: `_write_new_text()`가 기존 파일 있으면 `RuntimeViolation`
- **harness absorption boundary 결정**: ADR 0002로 채택 — 샘플 선행 검증, 템플릿 추출, adapter-neutral 원칙 문서화
- **Antigravity adapter**: instruction adapter 추가
- **테스트**: 1220개, init scaffold 관련 contract test 포함

### 완료 (2026-05-08 업데이트 #2)

- **에이전트 템플릿 보강**: 1~2줄 요약 → Role/Responsibilities/Input Artifacts/Output Artifacts/Collaboration Rules/Error Handling 구조화 (4개 에이전트 전체)
- **스킬 템플릿 보강**: Trigger/Procedure(단계별)/Exit Criteria/References 구조화 (4개 스킬 전체)
- **테스트 업데이트**: agent role 검증, skill procedure/exit criteria 검증 강화

### 완료 (2026-05-08 업데이트 #3 — 초안 품질 향상)

- **도메인 분석**: `_analyze_objective_domain()` 추가 — objective에서 8개 도메인(api, frontend, backend, data, auth, infra, testing, security) + 5개 기술 스택 + 5개 변경 유형(feature, bugfix, refactor, migration, security, testing) 자동 감지
- **PRD 도메인 보강**: Domain Analysis 섹션(domains, tech stack, change type) + Domain-Specific Considerations 섹션 추가
- **ARCHITECTURE 도메인 보강**: Domain Context 섹션 + Architecture Considerations 섹션 추가
- **QA 도메인 보강**: Domain Context + Domain-Specific QA Checklist 섹션 추가. 도메인별 체크리스트 항목 + 변경 유형별 체크리스트
- **3개 헬퍼 추가**: `_domain_considerations()`, `_architecture_considerations()`, `_qa_checklist()` — 도메인/변경유형별 고려사항 생성
- **테스트**: `test_domain_analysis.py` 추가 (21개 테스트). 유닛 테스트(도메인 감지, 고려사항 생성, QA 체크리스트) + 통합 테스트(init → 도메인 보강 초안 검증)
- **프로젝트 타입 감지**: `_detect_project_type()` 추가 — task_dir 조상에서 파일시스템 마커로 프로젝트 타입 감지 (Next.js, React, FastAPI, Django, Flask, Express, Go, Rust, Python CLI). `package.json` 의존성 분석으로 Next.js/React/TypeScript 정밀 감지. `pyproject.toml` 내용 분석으로 FastAPI/Django/Flask 감지
- **프로젝트별 가이드라인**: `_project_type_considerations()` — 감지된 프로젝트 타입에 맞는 프레임워크 가이드라인 자동 생성 (Next.js App Router, FastAPI DI, Django ORM, etc.)
- **초안에 프로젝트 컨텍스트 주입**: PRD/ARCHITECTURE/QA에 Project Context(project_type, framework, language) + Project-Specific Guidelines 섹션 추가
- **테스트**: `test_project_type_detection.py` 추가 (17개 테스트). 감지 유닛 테스트(9개) + 고려사항 테스트(4개) + 통합 테스트(3개: Next.js, unknown, FastAPI)

### 미완료 / 간극

- **evolve 루프**: 런타임 진화 모듈은 있으나 init 초안 품질 피드백 미연결

## init이 실제로 생성하는 파일

```
.forgeflow/tasks/<task-id>/
├── brief.json              # task metadata (schema_version, objective, risk, route)
├── run-state.json          # stage progression state
├── checkpoint.json         # gate checkpoint
├── session-state.json      # session tracking
├── CLAUDE.md               # 포인터 (brief, init-summary, PRD, ARCHITECTURE, QA 링크 + 트리거)
├── docs/
│   ├── PRD.md              # 도메인 분석 + 프로젝트 컨텍스트 + 고려사항 포함 초안
│   ├── ARCHITECTURE.md     # 선택된 team pattern + 도메인/프로젝트 컨텍스트 + 아키텍처 고려사항
│   ├── QA.md               # 도메인 특화 + 프로젝트별 QA 체크리스트 포함 초안
│   └── DECISIONS.md        # ADR-001: init creates usable drafts
├── tasks/
│   ├── init-summary.md     # route, architecture, generated drafts 목록
│   ├── feature/<slug>.md   # feature breakdown 초안
│   └── qa/<slug>.md        # QA reproduction/fix/regression 초안
└── .claude/
    ├── agents/
    │   ├── planner.md      # Role/Responsibilities/Input/Output/Collaboration/Error Handling
    │   ├── implementer.md  # (동일 구조)
    │   ├── qa.md           # (동일 구조)
    └── reviewer.md         # (동일 구조)
    └── skills/
        ├── plan/SKILL.md   # Trigger/Procedure(6단계)/Exit Criteria/References
        ├── build/SKILL.md  # Trigger/Procedure(6단계)/Exit Criteria/References
        ├── qa-fix/SKILL.md # Trigger/Procedure(7단계)/Exit Criteria/References
        └── review/SKILL.md # Trigger/Procedure(7단계)/Exit Criteria/References
```

## 팀 아키텍처 선택 로직

```python
# _select_team_architecture()
if risk == "high" or 키워드("migration", "refactor", "architecture", "security"):
    → "fan-out/fan-in + producer-reviewer"
elif 키워드("bug", "fix", "qa", "test", "regression"):
    → "pipeline + producer-reviewer"
else:
    → "producer-reviewer + pipeline"  # 기본
```

3가지 패턴, objective 키워드 + risk level 기반. harness-100의 6가지 패턴(pipeline, fan-out/fan-in, expert pool, producer-reviewer, supervisor, hierarchical delegation)에서 실제 사용 빈도 높은 것만 살림.

## harness-100과의 비교

| | harness-100 | ForgeFlow init |
|---|---|---|
| **포지션** | 프로젝트 템플릿 | 워크플로우 오케스트레이터 |
| **에이전트** | 도메인 특화 (architect, frontend, backend, devops, qa) | 파이프라인 역할 (planner, implementer, qa, reviewer) |
| **스킬** | 프로젝트 특화 (api-security-checklist, component-patterns) | 파이프라인 단계 (plan, build, qa-fix, review) |
| **초안 품질** | 도메인 지식 포함된 실질적 초안 | 도메인 분석 기반 구조화 초안 (8개 도메인, 5개 기술스택, 6개 변경유형 자동 감지) |
| **CLAUDE.md** | ✅ | ✅ (task-local 포인터) |
| **적용 범위** | 특정 프로젝트 타입별 템플릿 | 범용 파이프라인 + 프로젝트 타입 자동 감지 (9개 타입, framework/language 추론) |

**핵심 차이**: harness-100은 "이런 종류의 프로젝트에는 이런 팀과 스킬이 필요하다"를 템플릿화한 것이고, ForgeFlow init은 "어떤 task든 파이프라인으로 돌리기 위한 최소 구조"를 만든다.

## 가져온 것 (흡수 완료)

### 1) 에이전트 / 스킬 분리

- 에이전트 = 누가 수행하는가 → `.claude/agents/`
- 스킬 = 어떻게 수행하는가 → `.claude/skills/`
- ✅ 구조 구현 + 내용 구조화 완료 (Role/Responsibilities/Input/Output/Collaboration/Error Handling)

### 2) 팀 아키텍처 선행 선택

- ✅ `_select_team_architecture()`로 구현
- harness-100의 6패턴 → 3패턴으로 실용적 축소
- objective 키워드 매칭으로 자동 선택

### 3) init은 빈 껍데기가 아니다

- ✅ objective, risk, pattern이 초안에 치환되어 들어감
- ✅ 도메인 분석 결과(domains, tech stack, change type)가 PRD/ARCHITECTURE/QA에 자동 반영
- ✅ 도메인별 고려사항 + QA 체크리스트 자동 생성
- 덮어쓰기 방지로 안전성 확보

### 4) CLAUDE.md 포인터 규칙

- ✅ 전체 규칙 복붙 없이 포인터만 생성
- brief, init-summary, PRD, ARCHITECTURE, QA 링크 + 트리거 명령

## 버린 것 (의도적)

- Claude Code 전용 강결합 → adapter-neutral 원칙 (ADR 0002)
- 6가지 팀 아키텍처 전체 → 실사용 3패턴으로 축소
- init에서 모든 걸 완결하는 과도한 오케스트레이터화
- DB 기반 워크플로우 엔진
- 도메인 특화 에이전트 템플릿 (harness-100의 frontend-dev, backend-dev 등)

## 다음 개선 후보

이미 구조는 잡혀 있으니, 깊이를 올리는 방향:

1. ~~**초안 품질 향상**~~: ✅ 완료 (2026-05-08 #3). `_analyze_objective_domain()`으로 도메인/기술스택/변경유형 감지 → PRD/ARCHITECTURE/QA에 도메인 특화 고려사항 + 체크리스트 자동 생성
2. ~~**스킬 내용 보강**~~: ✅ 완료 (2026-05-08). Trigger/Procedure/Exit Criteria/References 구조화
3. ~~**프로젝트 타입 인식**~~: ✅ 완료 (2026-05-08 #4). `_detect_project_type()`으로 파일시스템 마커 감지 → 프로젝트별 가이드라인 자동 주입. 9개 프로젝트 타입 + framework/language 자동 추론
4. **evolve → init 피드백 루프**: 완료 태스크에서 패턴 학습 → 다음 init 초안 품질 향상

## 검증

```bash
# 전체 테스트
source .venv/bin/activate && python3 -m pytest -q

# 구조 검증
python3 scripts/validate_structure.py

# init scaffold 관련 테스트
python3 -m pytest tests/test_plugin_skill_contracts.py -q
```

## 관련 문서

- `docs/decisions/0002-harness-absorption-boundary.md` — 흡수 경계 결정
- `forgeflow_runtime/orchestrator.py` L581-741 — 실제 구현 (`_select_team_architecture`, `_init_markdown_drafts`)
- `skills/forgeflow-init/SKILL.md` — init 스킬 정의
- `.claude-plugin/skills/forgeflow-init.md` — 플러그인 init 명령
