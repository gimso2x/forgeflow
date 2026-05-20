# ForgeFlow Agent Benchmark Report

**날짜**: 2026-05-20
**환경**: WSL2, Node v24.15.0, pnpm 11.1.1, Vite + React + TypeScript

---

## 1. 테스트 개요

| 항목 | Small | Medium |
|------|-------|--------|
| **난이도** | 정적 랜딩 페이지 | API 연동 + 폼 |
| **요구 컴포넌트** | Hero, FeatureCard, Footer | UserList, UserForm, UserCard, useUsers |
| **ForgeFlow 요구사항** | 계획 → 파일목록 → 컴포넌트 책임 | 계획 → 파일목록 → 역할 → 에지 케이스 |

## 2. 실행 시간 비교

| 에이전트 | Small | Medium | 합계 |
|---------|-------|--------|------|
| **Gemini CLI** | **56.1s** 🥇 | **101.5s** 🥇 | **157.6s** |
| **Claude Code** | 63.7s 🥈 | 243.3s 🥉 | 307.0s |
| **Codex CLI** | 118.7s 🥉 | 147.9s 🥈 | 266.6s |

## 3. 코드량(LOC) 비교

| 에이전트 | Small | Medium | 합계 |
|---------|-------|--------|------|
| **Claude Code** | **236** | 276 | 512 |
| **Gemini CLI** | 228 | 232 | 460 |
| **Codex CLI** | 218 | **347** | 565 |

## 4. 빌드 검증

| 에이전트 | Small | Medium |
|---------|-------|--------|
| Claude Code | ✅ pass | ✅ pass |
| Codex CLI | ✅ pass | ✅ pass |
| Gemini CLI | ✅ pass | ✅ pass |

## 5. ForgeFlow 워크플로우 호환성 평가

### 5.1 Small 테스트

| 평가 항목 | Claude | Codex | Gemini |
|----------|--------|-------|--------|
| 구현 계획 서술 | ✅ | ❌ (생략) | ✅ |
| 변경 파일 목록 | ✅ | ✅ | ✅ |
| 컴포넌트 책임 설명 | ✅ | ✅ | ✅ |
| 검증(build/lint) | ✅ build | ✅ build+lint | ✅ build |
| **점수** | **4/4** | **3/4** | **4/4** |

### 5.2 Medium 테스트

| 평가 항목 | Claude | Codex | Gemini |
|----------|--------|-------|--------|
| 구현 계획 + 데이터 흐름 | ✅ 표 형식 | ✅ 간단히 | ✅ 상세히 |
| 변경 파일 목록 | ✅ | ✅ (링크 포함) | ✅ |
| 함수/컴포넌트 역할 | ✅ 표 형식 | ✅ | ✅ |
| 에지 케이스 나열 | ✅ (5개) | ✅ (7개) | ✅ (4개) |
| 검증(build/lint) | ✅ build | ✅ build+lint | ✅ build |
| **점수** | **5/5** | **5/5** | **5/5** |

### 5.3 ForgeFlow 워크플로우 총점

| 에이전트 | Small | Medium | 총점 |
|---------|-------|--------|------|
| **Claude Code** | 4/4 | 5/5 | **9/9** 🥇 |
| **Codex CLI** | 3/4 | 5/5 | **8/9** 🥈 |
| **Gemini CLI** | 4/4 | 5/5 | **9/9** 🥇 |

## 6. 코드 품질 비교

### useUsers 훅
- **Claude**: 직관적, useState 3개, fetch + POST + delete. 중복 제출 방지(submitting 상태) 포함
- **Codex**: 가장 방대함(105행). AbortController로 언마운트 시 fetch 취소. 폼 상태를 error별로 세분화
- **Gemini**: 간결함. import type 사용(verbatimModuleSyntax 준수). Date.now()로 ID 충돌 방지

### UserForm 유효성 검사
- **Claude**: 이름 필수 + 이메일 regex + 제출 중 disabled
- **Codex**: 이름 필수 + 이메일 regex + 전화번호 검사 + 필드별 실시간 에러
- **Gemini**: 이름 필수 + 이메일 regex + 폼 에러 상태 관리

### 타입 정의
- **Claude/Gemini**: `User` + `NewUser = Omit<User, 'id'>` 패턴
- **Codex**: `User` + `NewUser = Omit<User, 'id'>` 동일 패턴 (9행, 간결)

## 7. 종합 평가

### 속도 중심 → **Gemini CLI**
- 두 테스트 모두 가장 빠름 (Small 56s, Medium 101s)
- ForgeFlow 호환성도 만점
- 코드가 간결하고 실용적

### 코드 품질/안정성 중심 → **Codex CLI**
- LOC가 가장 많고 에지 케이스 7개 명시
- AbortController 등 실무적 디테일 포함
- lint까지 검증하는 습관
- 다만 속도가 느리고 Small에서 계획 서술 누락

### 보고서/문서화 중심 → **Claude Code**
- 표 형식의 정돈된 보고
- ForgeFlow 총점 만점 (9/9)
- 가장 완벽한 "완료 보고" 형식
- 다만 Medium에서 속도가 현저히 느림 (243s)

### ForgeFlow 워크플로우 권장 순위

1. **Gemini CLI** — 속도 + 호환성 최고의 밸런스
2. **Claude Code** — 가장 정교한 산출물, 시간은 길어도 품질 보장
3. **Codex CLI** — 실무적 코드 품질, 속도는 중간, Small에서 계획 누락 주의

---

*생성된 모든 프로젝트는 `/tmp/agent-bench/`에서 확인 가능합니다.*
