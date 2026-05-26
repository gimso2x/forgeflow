# Coding Convention

> 코드 품질 기준은 Frontend Fundamentals — 좋은 코드를 위한 4가지 기준을 따릅니다.
> 원문: https://frontend-fundamentals.com/code-quality/code/

## 코드 품질 4가지 기준

가독성, 예측 가능성, 응집도, 결합도의 4가지 기준과 인라인 코드 예시는 → [`coding-convention/quality-criteria.md`](coding-convention/quality-criteria.md)

## 기본 원칙

- 패키지 매니저는 pnpm만 사용합니다.
- lint / format 표준은 ESLint + Prettier를 사용합니다.
- TanStack Router 파일 기반 라우팅 규칙을 따릅니다.
- 자동 생성 파일 (`src/routeTree.gen.ts`)은 직접 수정하지 않습니다.

## 파일 / 코드 규칙

- 파일명은 kebab-case를 사용합니다.
- 컴포넌트와 타입은 PascalCase를 사용합니다.
- 함수와 훅은 camelCase를 사용합니다.
- import는 절대경로 `@/` 사용을 우선합니다.
- 사용하지 않는 import는 허용하지 않습니다.
- `import type`을 우선 사용합니다.

### 컴포넌트 파일 크기

> **한 파일 = 한 화면 조각.** 서브 컴포넌트를 같은 파일 안에 `function`으로만 두지 말고, 기준을 넘으면 **별도 파일로 분리**합니다.

| 기준            | 값         | 조치                                            |
| --------------- | ---------- | ----------------------------------------------- |
| **권장 상한**   | 300줄      | 이하 유지                                       |
| **분리 필수**   | 300줄 초과 | 같은 PR 또는 직후 PR에서 파일 분리              |
| **entry point** | ~50줄      | 조합·레이아웃만 담당 (`PropertyFilterSheet` 등) |

**분리 우선순위**

1. **상태·순수 로직** → `*-utils.ts`, `*-state.ts` (React import 없음)
2. **복잡한 UI 조각** (~80줄 이상, 슬라이더·드래그 등) → `*-section.tsx`, `*-panel.tsx`
3. **단순 탭·칩 나열** → 같은 `filter-panels.tsx` 등 **한 파일에 묶기** (탭마다 파일 X)

**과도한 분리 금지**

- **50줄 미만**이고 재사용·독립 테스트가 없으면 별도 파일로 빼지 않습니다.
- 타입 3~4줄만을 위한 `*-props.ts`는 `types.ts`에 둡니다.
- "탭 1개 = 파일 1개" 패턴은 지양합니다. 단순 map 렌더는 인접 패널과 같은 파일에 둡니다.

**composite 컴포넌트** (시트·모달·폼 등 여러 하위 UI로 구성)는 feature `components/` 아래 **전용 서브디렉터리**를 둡니다.

```text
src/features/property-filter/components/
  property-filter-sheet.tsx          # public export (얇은 entry)
  property-filter-sheet.scss
  property-filter-sheet/               # 내부 구현 (외부 import 금지)
    filter-panel.tsx
    price-range-section.tsx
    filter-state-utils.ts
```

- **외부(feature 밖·다른 feature)** 에서 import하는 것은 entry(`property-filter-sheet.tsx`)만 허용합니다.
- 서브디렉터리 파일은 **같은 composite 안에서만** import합니다.

**새 기능 추가 시**

- 기존 entry 파일이 250줄을 넘기 시작하면, 추가 전에 패널/섹션 파일을 먼저 만듭니다.
- "나중에 분리"는 brief/plan에 **명시적으로 Out of Scope**일 때만 허용하고, review에서 잔여 항목으로 기록합니다.

ESLint `max-lines`(300, warn)가 `src/features/**/components/**`, `src/components/**`에 적용됩니다. 경고가 뜨면 분리 또는 PR 범위 조정을 검토하세요.

## 스타일 규칙

- 들여쓰기는 2칸 공백입니다.
- print width는 120입니다.
- 문자열 quote는 single quote를 사용합니다.
- semicolon을 사용합니다.
- trailing comma는 가능한 곳에 모두 사용합니다.
- bracket spacing은 사용합니다.
- 수동 포맷보다 Prettier 자동 포맷 결과를 우선합니다.

## ESLint 핵심 규칙

- `unused-imports/no-unused-imports`: error
- `@typescript-eslint/no-unused-vars`: error (`_` prefix 허용)
- `@typescript-eslint/consistent-type-imports`: error
- `prefer-const`: error
- `no-debugger`: error
- `no-console`: warn
- `react/no-danger`: warn
- `react/no-array-index-key`: warn
