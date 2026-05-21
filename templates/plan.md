# 실행 계획 (Execution Plan)

<!-- ForgeFlow plan template. Created during plan stage. -->
<!-- Write prose in the user's primary language. Preserve canonical labels, enum values, commands, paths, and artifact filenames in English. -->

## 사용자용 요약 (Reader Summary)
<!-- For high/epic routes especially: summarize what will change, touched areas, verification, and key risks in the user's language. -->

## 라우트 (Route)
<!-- small | medium | high | epic -->
<!-- medium sub-band: medium-light | medium-full (from brief.md) -->

## 라우트 하위 밴드 (Route Sub-band)
<!-- medium-light | medium-full | n/a -->

## 요구사항 (Requirements)
<!-- Derived from brief.md acceptance criteria -->

## 비목표 (Non-goals)
<!-- Explicitly out-of-scope items from clarify -->

## 의존성 (Dependencies)
<!-- What must exist before execution starts -->

## 아키텍처 메모 (Architecture Notes)
<!-- Key design decisions affecting execution order -->
<!-- high/epic: record Execution Pattern (pipeline | fan-out/fan-in) here -->
<!-- medium-full: contract-first traceability required; medium-light: contracts optional unless brownfield -->

## 실행 패턴 (Execution Pattern)
<!-- Route strategy: small = direct single-worker; medium = pipeline; high = fan-out/fan-in when independent + separate spec/quality review; epic = milestone fan-out/fan-in -->

## 적용된 진화 규칙 (Applied Evolution Rules)
<!-- Carry forward rules from brief.md and state how this plan applies them. -->
- **Project active rules**:
- **Global advisory rules**:
- **Plan impact**:

## 작업 의존성 그래프 (Task Dependency Graph)
<!-- Optional: include only when tasks have non-trivial dependencies (high/epic routes). -->
<!-- Validate Mermaid syntax before committing; omit this section entirely for small/medium routes. -->

```mermaid
graph TD
    T1[Task 1] --> T2[Task 2]
    T1 --> T3[Task 3]
    T2 --> T4[Task 4]
    T3 --> T4
```

## 작업 목록 (Tasks)

### Task 1: <!-- name -->
- **Objective**:
- **Files**:
- **Depends on**: (none | Task N)
- **Expected output**:
- **Verification**:
- **Fulfills**: <!-- which acceptance criteria -->
- **Rollback note**: <!-- if applicable, how to revert -->

### Task 2: <!-- name -->
<!-- Copy pattern above -->

## 검증 계획 (Verification Plan)
<!-- How to verify the entire plan succeeded -->

### Check 1: <!-- target -->
- **Type**: <!-- sub_req | journey | artifact | contract -->
- **Gates**:

## 계약 (Contracts, if applicable)
- **Artifact**:
- **Interfaces**:
- **Invariants**:

## 여정 (Journeys, if applicable)
<!-- End-to-end flow verification -->
### Journey 1: <!-- name -->
- **Composes**: <!-- which tasks -->
- **Description**:

## 병렬성 (Parallelism)
<!-- Which tasks can run concurrently and any conflicts -->
