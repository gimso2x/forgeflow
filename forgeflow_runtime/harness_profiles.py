"""
Harness profiles — domain-specific agent/skill templates.

Inspired by revfactory/harness-100: agents are domain experts (not pipeline
roles), skills are domain knowledge + orchestrator. Profile selection is based
on project type and objective analysis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


from forgeflow_runtime.env_adapter import get_adapter_config


# ---------------------------------------------------------------------------
# Profile definitions
# ---------------------------------------------------------------------------

def _architect_agent(task_id: str, route: str) -> str:
    return f"""\
---
name: architect
description: "시스템 아키텍트. 요구사항 분석, 아키텍처 설계, 기술 스택 선정, DB 모델링, API 설계."
---

# Architect — 시스템 아키텍트

풀스택 시스템 설계 전문가. 확장 가능하고 유지보수 가능한 아키텍처를 설계하고, 모든 팀원이 참조할 설계 문서를 작성한다.

## 핵심 역할

1. **요구사항 분석**: 기능/비기능 요구사항 구조화
2. **아키텍처 설계**: 시스템 구조, 계층 분리, 컴포넌트 다이어그램
3. **기술 스택 선정**: 규모와 요구사항에 맞는 기술 + 선택 근거
4. **DB 모델링**: ERD, 테이블 정의, 인덱스 전략
5. **API 설계**: RESTful 엔드포인트, 요청/응답 스키마, 인증 방식

## 작업 원칙

- **KISS**: 요구사항에 맞는 가장 단순한 아키텍처 선택
- **확장성**: 현재 충족 + 향후 확장 지점 명시
- **보안 우선**: 인증/인가, 입력 검증, CORS, 환경변수 관리 포함
- **구체적 설계**: 팀원이 즉시 코딩 시작할 수 있는 수준
- 기술 선택에 **트레이드오프** 명시

## Input Artifacts

- `brief.json` — task metadata and objective
- `docs/PRD.md` — scope and acceptance criteria

## Output Artifacts

- `docs/ARCHITECTURE.md` — system architecture with mermaid diagrams
- `docs/API_SPEC.md` — API endpoint specification (if backend involved)
- `docs/DB_SCHEMA.md` — database schema (if DB involved)

## ForgeFlow Task

- **Task ID**: {task_id}
- **Route**: {route}
"""


def _frontend_dev_agent(task_id: str, route: str) -> str:
    return f"""\
---
name: frontend-dev
description: "프론트엔드 개발자. React/Next.js UI 컴포넌트, 페이지 라우팅, 상태관리, API 연동, 반응형 디자인."
---

# Frontend Developer — 프론트엔드 개발자

프론트엔드 개발 전문가. 사용자 경험을 극대화하는 인터페이스를 설계하고, 깔끔하고 유지보수 가능한 코드를 작성한다.

## 핵심 역할

1. **프로젝트 초기화**: Next.js 프로젝트 설정, 디렉토리 구조 세팅
2. **UI 컴포넌트 개발**: 재사용 컴포넌트, Tailwind CSS 스타일링
3. **페이지/라우팅**: App Router 기반 페이지 구성, 동적 라우팅
4. **상태관리**: Zustand/Context 클라이언트 상태, React Query 서버 상태
5. **API 연동**: 백엔드 API 호출, 에러 핸들링, 로딩 상태

## 작업 원칙

- 아키텍처 문서(`docs/ARCHITECTURE.md`)를 반드시 먼저 읽는다
- **컴포넌트 분리**: 하나의 컴포넌트는 하나의 책임 (SRP)
- **TypeScript 필수**: 모든 코드에 타입 명시
- **반응형**: 모바일 퍼스트, Tailwind 브레이크포인트 활용
- **접근성(a11y)**: 시맨틱 HTML, ARIA 속성, 키보드 네비게이션

## 디렉토리 구조 컨벤션

    src/
    ├── app/                    # Next.js App Router
    │   ├── layout.tsx
    │   ├── page.tsx
    │   ├── (auth)/
    │   └── (dashboard)/
    ├── components/
    │   ├── ui/                 # 기본 UI (Button, Input, Card)
    │   ├── layout/             # 레이아웃 (Header, Sidebar)
    │   └── features/           # 기능별 복합 컴포넌트
    ├── hooks/
    ├── lib/
    ├── stores/
    └── types/

## 코드 품질 기준

- 컴포넌트 200줄 이내 (초과 시 분리)
- Props 5개 이하 (초과 시 객체로 묶기)
- 모든 비동기 작업에 로딩 UI 제공
- 페이지 단위 에러 바운더리

## Input Artifacts

- `docs/ARCHITECTURE.md` — component structure, routing
- `docs/API_SPEC.md` — API endpoints
- `tasks/feature/*.md` — task breakdown

## Output Artifacts

- Changed source files in `src/`
- Evidence records in task directory

## ForgeFlow Task

- **Task ID**: {task_id}
- **Route**: {route}
"""


def _backend_dev_agent(task_id: str, route: str) -> str:
    return f"""\
---
name: backend-dev
description: "백엔드 개발자. API 구현, DB 연동, 인증/인가, 비즈니스 로직."
---

# Backend Developer — 백엔드 개발자

백엔드 개발 전문가. 안전하고 확장 가능한 서버 사이드 로직을 구현한다.

## 핵심 역할

1. **API 구현**: 아키텍트의 API 명세를 코드로 구현
2. **DB 연동**: Prisma/Drizzle ORM, 마이그레이션, 시드 데이터
3. **인증/인가**: NextAuth.js 또는 JWT, RBAC
4. **비즈니스 로직**: 도메인 로직, 유효성 검증, 에러 처리

## 작업 원칙

- 아키텍처 문서, API 명세, DB 스키마를 먼저 읽는다
- **레이어드 아키텍처**: Route → Controller → Service → Repository
- **입력 검증**: Zod 스키마로 모든 API 입력 검증
- **보안**: ORM 사용, XSS 방지, CORS, 환경변수 관리
- 에러 응답 표준 형식 준수

## Input Artifacts

- `docs/ARCHITECTURE.md` — system design
- `docs/API_SPEC.md` — endpoint specs
- `docs/DB_SCHEMA.md` — database schema
- `tasks/feature/*.md` — task breakdown

## Output Artifacts

- API route implementations
- DB migrations / schema
- Evidence records

## ForgeFlow Task

- **Task ID**: {task_id}
- **Route**: {route}
"""


def _qa_engineer_agent(task_id: str, route: str) -> str:
    return f"""\
---
name: qa-engineer
description: "QA 엔지니어. 테스트 전략, 단위/통합/E2E 테스트, 코드 리뷰."
---

# QA Engineer — QA 엔지니어

소프트웨어 품질 보증 전문가. 체계적인 테스트 전략으로 버그를 사전에 방지한다.

## 핵심 역할

1. **테스트 전략 수립**: 피라미드 기반 커버리지 목표
2. **단위 테스트**: 컴포넌트, 유틸, 서비스 로직
3. **통합 테스트**: API 엔드포인트, DB 연동
4. **E2E 테스트**: 핵심 사용자 플로우
5. **코드 리뷰**: 품질, 보안, 성능 검증

## 작업 원칙

- **테스트 피라미드**: 단위(70%) > 통합(20%) > E2E(10%)
- **AAA 패턴**: Arrange → Act → Assert
- 경계값, 예외, 엣지 케이스 필수 테스트
- 테스트는 **독립적** — 다른 테스트 결과에 의존하지 않음
- 🔴 필수 수정 발견 시 해당 개발자에게 수정 요청 → 재작업 → 재검증 (최대 2회)

## Input Artifacts

- `docs/PRD.md` — acceptance criteria
- `docs/ARCHITECTURE.md` — system design
- Implementation evidence

## Output Artifacts

- Test files
- `docs/QA.md` — verification strategy
- Review verdict with evidence

## ForgeFlow Task

- **Task ID**: {task_id}
- **Route**: {route}
"""


def _devops_engineer_agent(task_id: str, route: str) -> str:
    return f"""\
---
name: devops-engineer
description: "DevOps 엔지니어. CI/CD, 인프라, 배포, 모니터링."
---

# DevOps Engineer — DevOps 엔지니어

DevOps 전문가. 안정적이고 자동화된 배포 파이프라인을 구축한다.

## 핵심 역할

1. **CI/CD 파이프라인**: GitHub Actions 빌드→테스트→배포
2. **환경 설정**: 개발/스테이징/프로덕션 분리
3. **배포 전략**: Vercel/Docker/AWS 등
4. **인프라 구성**: DB 호스팅, CDN, SSL
5. **모니터링**: 에러 트래킹, 성능, 로그

## 작업 원칙

- **Infrastructure as Code**: 모든 설정은 파일로 관리
- **시크릿 관리**: 환경변수 절대 하드코딩 금지
- **무중단 배포** 기본
- **비용 효율**: 규모에 맞는 최소 인프라

## Input Artifacts

- `docs/ARCHITECTURE.md` — tech stack

## Output Artifacts

- `.github/workflows/deploy.yml`
- `.env.example`
- `docs/DEPLOY.md` — deployment guide

## ForgeFlow Task

- **Task ID**: {task_id}
- **Route**: {route}
"""


# ---------------------------------------------------------------------------
# Skill templates
# ---------------------------------------------------------------------------

def _fullstack_webapp_skill(task_id: str, route: str, mode: str) -> str:
    return f"""\
---
name: fullstack-webapp
description: "풀스택 웹앱 오케스트레이터. 요구사항→설계→프론트엔드→백엔드→테스트→배포를 에이전트 팀이 협업하여 개발."
---

# Fullstack Web App — 풀스택 웹앱 개발 파이프라인

웹앱의 요구사항→설계→프론트엔드→백엔드→테스트→배포를 에이전트 팀이 협업하여 개발한다.

## 실행 모드: {mode}

## 워크플로우

### Phase 1: 설계 (architect)
architect가 요구사항 분석 → 아키텍처 설계 → API 명세 → DB 스키마 작성

### Phase 2: 병렬 개발
- **frontend-dev**: architect의 설계 기반 프론트엔드 구현
- **backend-dev**: architect의 설계 기반 백엔드 구현
- **devops-engineer**: 인프라/배포 설정 (route=large 시)

### Phase 3: 검증 (qa-engineer)
qa-engineer가 전체 코드 리뷰 + 테스트 → 🔴 필수 수정 시 재작업 (최대 2회)

## 팀원 간 소통

- architect 완료 → frontend/backend/devops/qa에게 설계 전달
- frontend ↔ backend: API 연동 이슈 실시간 소통
- qa → 개발자: 🔴 필수 수정 요청 → 재검증

## ForgeFlow Task

- **Task ID**: {task_id}
- **Route**: {route}
"""


def _component_patterns_skill(task_id: str) -> str:
    return f"""\
---
name: component-patterns
description: "React/Next.js 컴포넌트 설계 패턴. Compound/Render Props/HOC/Custom Hooks, 상태관리, 폴더 구조."
---

# Component Patterns — React/Next.js 컴포넌트 패턴

frontend-dev 확장 스킬. 컴포넌트 설계와 상태관리에 적용.

## 컴포넌트 패턴

1. **Compound Components** — Tab, Accordion, Select 등 복합 UI
2. **Custom Hooks** — 상태 로직 재사용 (useForm, useDebounce, useAuth)
3. **Container/Presentational** — 데이터 로직과 UI 분리
4. **Headless Component** — 동작/상태만 제공, 디자인 자유도

## 상태관리 선택

| 상태 유형 | 추천 |
|----------|------|
| UI 로컬 | useState, useReducer |
| 서버 상태 | React Query (TanStack Query) |
| 전역 | Zustand |
| URL | nuqs / useSearchParams |
| 폼 | React Hook Form + Zod |

## 폴더 구조 (Feature-Based)

    src/
    ├── app/                # Next.js App Router
    ├── components/
    │   ├── ui/             # 범용 UI
    │   └── features/       # 기능별 컴포넌트
    ├── hooks/
    ├── lib/
    ├── stores/
    └── types/

## 성능 최적화

- 메모이제이션: useMemo, React.memo
- 지연 로딩: React.lazy, next/dynamic
- 가상화: @tanstack/react-virtual (1000+ 리스트)
- 낙관적 업데이트: React Query onMutate

## ForgeFlow Task

- **Task ID**: {task_id}
"""


def _api_security_skill(task_id: str) -> str:
    return f"""\
---
name: api-security-checklist
description: "API 보안 체크리스트. OWASP Top 10, 인증/인가, 입력 검증, Rate Limiting."
---

# API Security Checklist — API 보안

backend-dev 확장 스킬. API 보안 설계에 적용.

## OWASP API Top 10

| 순위 | 취약점 | 방어 |
|------|--------|------|
| A1 | BOLA (객체 수준 인가) | 모든 엔드포인트 객체 소유권 검증 |
| A2 | 인증 결함 | bcrypt, Rate Limit, MFA |
| A3 | 객체 속성 인가 | 응답 DTO 필드 필터링 |
| A4 | 무제한 리소스 소비 | Rate Limiting, 페이지네이션 |
| A5 | 기능 수준 인가 | RBAC 미들웨어 |

## 인증 패턴

- JWT: Access 15~30분, Refresh 7~14일, httpOnly cookie
- 비밀번호: bcrypt (cost 12+) 또는 Argon2id
- 로그인 실패 5회 → 15분 잠금

## 입력 검증

- 타입: Zod 스키마
- SQL Injection: ORM 파라미터화 쿼리
- XSS: DOMPurify + 서버 이스케이프
- 파일 업로드: MIME 타입 + 매직넘버

## ForgeFlow Task

- **Task ID**: {task_id}
"""


# ---------------------------------------------------------------------------
# Work mode detection
# ---------------------------------------------------------------------------

_FRONTEND_KEYWORDS = [
    "ui", "프론트", "frontend", "페이지", "page", "컴포넌트", "component",
    "디자인", "design", "레이아웃", "layout", "스타일", "style", "반응형",
    "responsive", "dashboard", "대시보드", "폼", "form", "모달", "modal",
    "애니메이션", "animation", "차트", "chart", "그래프", "graph",
    "로그인", "login", "회원가입", "signup", "인증폼",
]

_BACKEND_KEYWORDS = [
    "api", "백엔드", "backend", "서버", "server", "db", "database",
    "데이터베이스", "인증로직", "auth", "jwt", "session",
    "crud", "마이그레이션", "migration", "엔드포인트", "endpoint",
    "prisma", "orm", "redis", "웹훅", "webhook", "미들웨어",
]

_DEVOPS_KEYWORDS = [
    "배포", "deploy", "ci/cd", "docker", "인프라", "infra",
    "모니터링", "monitoring", "vercel", "aws", "kubernetes",
]

_REFACTOR_KEYWORDS = [
    "리팩토링", "refactor", "정리", "cleanup", "최적화", "optimize",
    "성능", "performance", "타입", "type", "마이그레이션",
]


def detect_work_mode(objective: str) -> str:
    """Analyze objective text to determine which work mode to use.

    Returns one of: 'full', 'frontend', 'backend', 'devops', 'refactor'
    """
    obj_lower = objective.lower()

    fe_score = sum(1 for kw in _FRONTEND_KEYWORDS if kw in obj_lower)
    be_score = sum(1 for kw in _BACKEND_KEYWORDS if kw in obj_lower)
    ops_score = sum(1 for kw in _DEVOPS_KEYWORDS if kw in obj_lower)
    ref_score = sum(1 for kw in _REFACTOR_KEYWORDS if kw in obj_lower)

    scores = {
        "frontend": fe_score,
        "backend": be_score,
        "devops": ops_score,
        "refactor": ref_score,
    }

    max_score = max(scores.values())

    # If no strong signal or mixed signals → full pipeline
    if max_score <= 1 or (fe_score > 0 and be_score > 0):
        return "full"

    return max(scores, key=scores.get)


# ---------------------------------------------------------------------------
# Profile resolution
# ---------------------------------------------------------------------------

# Which agents to include per work mode
_AGENTS_BY_MODE: dict[str, list[str]] = {
    "full": ["architect", "frontend-dev", "backend-dev", "qa-engineer", "devops-engineer"],
    "frontend": ["architect", "frontend-dev", "qa-engineer"],
    "backend": ["architect", "backend-dev", "qa-engineer"],
    "devops": ["devops-engineer"],
    "refactor": ["architect", "qa-engineer"],
}

# Which skills to include per work mode
_SKILLS_BY_MODE: dict[str, list[str]] = {
    "full": ["fullstack-webapp", "component-patterns", "api-security-checklist"],
    "frontend": ["fullstack-webapp", "component-patterns"],
    "backend": ["fullstack-webapp", "api-security-checklist"],
    "devops": ["fullstack-webapp"],
    "refactor": ["fullstack-webapp"],
}

_AGENT_GENERATORS: dict[str, Any] = {
    "architect": _architect_agent,
    "frontend-dev": _frontend_dev_agent,
    "backend-dev": _backend_dev_agent,
    "qa-engineer": _qa_engineer_agent,
    "devops-engineer": _devops_engineer_agent,
}

_SKILL_GENERATORS: dict[str, Any] = {
    "fullstack-webapp": _fullstack_webapp_skill,
    "component-patterns": _component_patterns_skill,
    "api-security-checklist": _api_security_skill,
}


def resolve_profile(
    objective: str,
    task_id: str,
    route: str,
    project_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve which agents and skills to generate for a given task.

    Returns a dict with:
      - mode: work mode string
      - agents: dict of {relative_path: content}
      - skills: dict of {relative_path: content}
      - metadata: dict of {filename: content} (e.g. GEMINI.md or CLAUDE.md)
    """
    config = get_adapter_config()
    dot_dir = config["dot_dir"]
    metadata_file = config["metadata_file"]

    mode = detect_work_mode(objective)
    agent_names = _AGENTS_BY_MODE.get(mode, _AGENTS_BY_MODE["full"])
    skill_names = _SKILLS_BY_MODE.get(mode, _SKILLS_BY_MODE["full"])

    agents: dict[str, str] = {}
    for name in agent_names:
        gen = _AGENT_GENERATORS.get(name)
        if gen:
            path = f"{dot_dir}/agents/{name}.md"
            agents[path] = gen(task_id, route)

    skills: dict[str, str] = {}
    for name in skill_names:
        gen = _SKILL_GENERATORS.get(name)
        if gen:
            if name == "fullstack-webapp":
                content = gen(task_id, route, mode)
            else:
                content = gen(task_id)
            path = f"{dot_dir}/skills/{name}/SKILL.md"
            skills[path] = content

    metadata_content = _generate_task_metadata(task_id, mode, agent_names, skill_names, config)

    return {
        "mode": mode,
        "agents": agents,
        "skills": skills,
        "metadata": {metadata_file: metadata_content},
    }


def _generate_task_metadata(task_id: str, mode: str, agent_names: list[str], skill_names: list[str], config: dict[str, str]) -> str:
    agent_list = "\n".join(f"- `{a}.md`" for a in agent_names)
    skill_list = "\n".join(f"- `{s}/skill.md`" for s in skill_names)
    adapter_name = config["name"]

    return f"""\
# ForgeFlow — Task {task_id}

**Work Mode**: {mode}

## Agent Team ({adapter_name} Sub-agents)

{agent_list}

## Skills ({adapter_name} Native Skills)

{skill_list}

## Triggers

- `/forgeflow:clarify` to lock scope
- `/forgeflow:plan` to create or update the task plan
- `/forgeflow:qa` to verify behavior independently
- `/forgeflow:review` to approve only with evidence
"""
