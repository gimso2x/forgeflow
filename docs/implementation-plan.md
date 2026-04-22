# Implementation Plan

> For Hermes: 이 문서는 설계를 구현 repo로 내릴 때 따를 P0 구현 순서다.

**Goal:** 현재 설계 문서와 정책을 실제 동작하는 harness repo로 옮길 수 있게 구현 순서를 고정한다.

**Architecture:** 문서/정책/스키마를 먼저 굳히고, 그 다음 generator와 validation을 붙인다. 코어 semantics를 안정화하기 전에는 adapter 구현을 넓히지 않는다.

**Tech Stack:** YAML, JSON Schema, Markdown, 간단한 generator/validator 스크립트

---

### Task 1: Canonical policy freeze
**Objective:** workflow, gates, review order, complexity routing을 SSOT로 고정한다.

**Files:**
- Verify: `policy/canonical/workflow.yaml`
- Verify: `policy/canonical/stages.yaml`
- Verify: `policy/canonical/gates.yaml`
- Verify: `policy/canonical/review-rubrics.yaml`
- Verify: `policy/canonical/complexity-routing.yaml`

**Verification:**
- stage names가 모든 문서와 동일한지 수동 체크
- review order가 `spec-review -> quality-review`로 일치하는지 확인

### Task 2: Artifact schema freeze
**Objective:** core artifact 6종 schema를 확정한다.

**Files:**
- Verify: `schemas/*.json`

**Verification:**
- 모든 schema에 `schema_version`, `task_id`가 필요한지 검토
- 문서의 artifact 설명과 schema required fields가 충돌 없는지 확인

### Task 3: Canonical prompt pack freeze
**Objective:** coordinator/planner/worker/reviewer 역할 정의를 확정한다.

**Files:**
- Verify: `prompts/canonical/*.md`

**Verification:**
- worker/reviewer separation이 모든 prompt에서 유지되는지 확인
- reviewer prompt가 anti-rationalization stance를 가지는지 확인

### Task 4: Adapter contract define
**Objective:** adapter manifest와 target metadata를 확정한다.

**Files:**
- Verify: `adapters/manifest.schema.json`
- Create: `adapters/targets/*/manifest.yaml`

**Verification:**
- adapter가 semantics를 바꾸지 못한다는 원칙이 manifest 설명에 반영되는지 확인

### Task 5: Validation scripts scaffold
**Objective:** schema/gate/doc drift를 검사할 최소 validator 자리를 만든다.

**Files:**
- Create: `scripts/validate-structure.*`
- Create: `scripts/validate-policy.*`
- Create: `scripts/generate-adapters.*`

**Verification:**
- 필수 파일 누락 검사 가능
- policy와 schema 존재 여부 검사 가능

### Task 6: Example scenarios and evals
**Objective:** small/medium/large 예시 흐름과 adherence eval을 연결한다.

**Files:**
- Verify: `examples/*`
- Verify: `evals/adherence/README.md`
- Verify: `evals/regression/README.md`

**Verification:**
- route 예시가 complexity-routing.yaml과 일치하는지 확인

### Task 7: First runnable generator slice
**Objective:** canonical prompt 하나를 claude/codex/cursor용 generated output으로 내리는 최소 generator를 만든다.

**Files:**
- Create: `scripts/generate-adapters.*`
- Write: `adapters/generated/*`

**Verification:**
- generated 파일이 생기고 target별 path 규칙을 지키는지 확인

---

## Done condition
- 문서, policy, schema, prompt, adapter contract가 서로 충돌하지 않는다.
- 최소 generator/validator를 붙일 다음 단계가 명확하다.
- v1에서 뭘 안 하는지까지 고정돼 있다.
