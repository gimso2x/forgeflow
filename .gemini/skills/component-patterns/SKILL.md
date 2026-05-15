---
name: component-patterns
description: "Django 컴포넌트 설계 패턴. Compound/Render Props/HOC/Custom Hooks, 상태관리, 폴더 구조."
---

# Component Patterns — Django 컴포넌트 패턴

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
    ├── components/
    │   ├── ui/             # 범용 UI
    │   └── features/       # 기능별 컴포넌트
    ├── hooks/
    ├── lib/
    ├── stores/
    └── types/

## 성능 최적화

- 메모이제이션: useMemo, React.memo
- 지연 로딩: React.lazy, dynamic import
- 가상화: @tanstack/react-virtual (1000+ 리스트)
- 낙관적 업데이트: React Query onMutate

## ForgeFlow Task

- **Task ID**: docs-update-v0111
