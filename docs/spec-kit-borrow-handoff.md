# Spec Kit → ForgeFlow 선택적 차용 핸드오프

> 출처: [github/spec-kit](https://github.com/github/spec-kit) (v0.7.2) 소스 전체 분석
> 작성: 02. Hermes 탐색 (탐색 에이전트)
> 대상: 01. Hermes 개발 (개발 에이전트)

---

## 배경

GitHub Spec Kit은 **스펙 저작 + 선형 파이프라인(spec → plan → tasks → implement)** 중심 도구.
ForgeFlow는 **실행 통제 + 게이트 + 증거 추적** 중심 하네스.

철학이 달라 통째 흡수는 비추천. 아래 3가지만 선택적 차용.

---

## 차용 1: YAML 워크플로우 엔진

### 현재 ForgeFlow 상태

- `stage_transition.py` — 하드코딩된 `route: list[str]`에서 다음 stage 인덱스 반환
- `operator_routing.py` — `STAGE_ROLE_MAP` 딕셔너리에 stage→role 매핑 하드코딩
- `engine.py` — `execute_stage()`가 prompt 생성 → dispatch 직접 연결
- `orchestrator.py` — `_resolve_route(load_runtime_policy(REPO_ROOT), recovery_route)`로 정적 route 로드

### Spec Kit에서 차용할 아이디어

Spec Kit의 `WorkflowEngine`은 **YAML로 파이프라인을 선언적으로 정의**하고 런타임이 해석 실행:

```yaml
# Spec Kit 예시 (workflows/speckit/workflow.yml)
steps:
  - id: specify
    command: speckit.specify
    integration: "{{ inputs.integration }}"
  - id: review-spec
    type: gate
    message: "Review the generated spec before planning."
    on_reject: abort
  - id: plan
    command: speckit.plan
  - id: implement
    command: speckit.implement
```

10가지 스텝 타입: `command`, `shell`, `prompt`, `gate`, `if`, `switch`, `while`, `do-while`, `fan-out`, `fan-in`

### ForgeFlow에 구현할 것

**파일**: `forgeflow_runtime/workflow_engine.py` (신규)

**YAML 워크플로우 스키마** (ForgeFlow 맞춤):

```yaml
# .forgeflow/workflows/default.yml
schema_version: "0.1"
name: "default-pipeline"
routes:
  small:
    - clarify
    - execute
    - finalize
  medium:
    - clarify
    - plan
    - execute
    - quality-review
    - finalize
  high:
    - clarify
    - plan
    - execute
    - spec-review
    - quality-review
    - finalize
steps:
  clarify:
    type: stage
    role: coordinator
    artifact_out: [brief.json]
  plan:
    type: stage
    role: planner
    artifact_out: [plan-ledger.json]
    required_for_entry: [brief.json]
  execute:
    type: stage
    role: worker
    artifact_out: [implementation-evidence.json]
    required_for_entry: [plan-ledger.json]
  spec-review:
    type: gate
    role: spec-reviewer
    artifact_out: [review-report.json]
    required_for_entry: [implementation-evidence.json]
  quality-review:
    type: gate
    role: quality-reviewer
    artifact_out: [review-report.json]
    required_for_entry: [implementation-evidence.json]
  finalize:
    type: stage
    role: coordinator
    artifact_out: [session-state.json]
```

**런타임 동작**:
1. `workflow_engine.py`가 YAML을 로드 → route별 stage 리스트 + 각 stage 메타데이터 구성
2. `stage_transition.py`의 `next_stage_for_transition()`을 YAML 파서 기반으로 대체
3. `operator_routing.py`의 `STAGE_ROLE_MAP` 하드코딩을 YAML의 `steps.*.role`로 대체
4. `generator.py`의 `_load_role_prompt()`는 그대로 유지 (role→프롬프트 파일 매핑은 동적)

**표현식 평가** (Spec Kit에서 차용):
- `{{ task.risk_level }}` → route 자동 선택
- `{{ steps.plan.status }}` → 조건부 분기
- stdlib만 사용: `string.Template` 또는 간단한 `str.replace` 기반 구현

**핵심 클래스**:

```python
@dataclass
class StepDefinition:
    id: str
    type: str          # "stage" | "gate"
    role: str
    artifact_out: list[str]
    required_for_entry: list[str]
    gate: str | None = None
    non_negotiables: list[str] | None = None

@dataclass
class WorkflowDefinition:
    schema_version: str
    name: str
    routes: dict[str, list[str]]   # route_name -> [step_ids]
    steps: dict[str, StepDefinition]

def load_workflow(yaml_path: Path) -> WorkflowDefinition: ...
def resolve_route(workflow: WorkflowDefinition, route_name: str) -> list[StepDefinition]: ...
def next_step(workflow: WorkflowDefinition, route_name: str, current_step: str) -> StepDefinition: ...
```

**기존 코드와의 연동**:
- `stages.schema.json` (policy)은 YAML의 steps 섹션과 1:1 매핑. YAML을 소스로 두고 JSON 스키마는 검증용으로 유지
- `stage_transition.py` → `next_step()`으로 교체
- `operator_routing.py` → `STAGE_ROLE_MAP` 제거, `WorkflowDefinition.steps[id].role` 참조
- `engine.py` → `execute_stage()` 시그니처 변경 없음. 내부적으로 워크플로우 정의에서 role/required artifacts 조회

**테스트**: `tests/runtime/test_workflow_engine.py`
- YAML 로드/파싱
- route 해석 (small/medium/high)
- next_step 전환 로직
- 존재하지 않는 step → `RuntimeViolation`
- 표현식 평가 (`{{ }}` 치환)

---

## 차용 2: 프리셋 템플릿 오버라이드 시스템

### 현재 ForgeFlow 상태

- `templates/starter-docs/` — ADR.md, ARCHITECTURE.md, PRD.md, UI_GUIDE.md (4개 고정)
- `generator.py` — `CANONICAL_PROMPT_DIR = REPO_ROOT / "prompts" / "canonical"` 고정 경로
- `ROLE_TO_FILENAME` — 딕셔너리 하드코딩

### Spec Kit에서 차용할 아이디어

Spec Kit의 `PresetResolver` — 4단계 우선순위 스택 + 컴포지션 전략:

```
Override (프로젝트별) > Preset (프리셋) > Extension (확장) > Core (기본)
```

컴포지션 전략 4가지:
- `replace`: 전체 교체
- `prepend`: 앞에 추가
- `append`: 뒤에 추가
- `wrap`: `{CORE_TEMPLATE}` 플레이스홀더에 코어 삽입

### ForgeFlow에 구현할 것

**파일**: `forgeflow_runtime/preset_resolver.py` (신규)

**디렉토리 구조**:

```
forgeflow/
  prompts/canonical/       # Core (기존, 그대로)
    coordinator.md
    planner.md
    worker.md
    spec-reviewer.md
    quality-reviewer.md
  templates/starter-docs/  # Core (기존, 그대로)
  .forgeflow/              # 프로젝트별 오버라이드 (신규)
    presets/
      coordinator.md       # replace: 전체 교체
      planner.append.md    # append: planner.md 뒤에 추가
      worker.prepend.md    # prepend: worker.md 앞에 추가
      coordinator.wrap.md  # wrap: {CORE_TEMPLATE} 치환
```

**핵심 클래스**:

```python
@dataclass
class PresetLayer:
    name: str            # "override" | "preset" | "core"
    path: Path
    priority: int        # 높을수록 우선 (override=3, preset=2, core=1)

COMPOSITION_SUFFIXES = {
    ".append.md": "append",
    ".prepend.md": "prepend",
    ".wrap.md": "wrap",
}

class PresetResolver:
    def __init__(self, core_dir: Path, override_dir: Path | None = None):
        ...

    def resolve(self, role: str) -> str:
        """Core + 오버라이드를 합성해 최종 프롬프트 반환."""
        core = self._load_core(role)
        override = self._find_override(role)
        if override is None:
            return core
        strategy = self._detect_strategy(override)
        return self._compose(core, override, strategy)

    def _compose(self, core: str, override: str, strategy: str) -> str:
        match strategy:
            case "replace": return override
            case "append": return core + "\n\n" + override
            case "prepend": return override + "\n\n" + core
            case "wrap": return override.replace("{CORE_TEMPLATE}", core)
```

**기존 코드와의 연동**:
- `generator.py`의 `_load_role_prompt()` → `PresetResolver.resolve(role)` 호출로 교체
- `ROLE_TO_FILENAME` 매핑은 `PresetResolver` 내부로 이동
- `CANONICAL_PROMPT_DIR`은 core 레이어 경로로 사용
- 프로젝트별 `.forgeflow/presets/`가 없으면 기존 동작과 100% 동일

**starter-docs 템플릿에도 동일 로직 적용**:
- `PresetResolver.resolve_template(template_name)` — ADR, ARCHITECTURE 등도 오버라이드 가능

**테스트**: `tests/runtime/test_preset_resolver.py`
- core만 있을 때 → core 그대로 반환
- replace 오버라이드 → 전체 교체
- append 오버라이드 → core + override
- prepend 오버라이드 → override + core
- wrap 오버라이드 → {CORE_TEMPLATE} 치환
- override_dir이 None이면 core와 동일

---

## 차용 3: 어댑터 레지스트리

### 현재 ForgeFlow 상태

- `adapters/targets/claude/manifest.yaml` — Claude 어댑터 메타데이터
- `adapters/targets/codex/manifest.yaml` — Codex 어댑터 메타데이터
- `adapters/targets/generic/manifest.yaml` — Generic 어댑터 메타데이터
- `adapters/targets/antigravity/` — ??? (확인 필요)
- 어댑터 발견은 디렉토리 스캔 기반, 등록 메커니즘 없음

### Spec Kit에서 차용할 아이디어

Spec Kit의 `INTEGRATION_REGISTRY` — 에이전트별 메타데이터 싱글소스 + `IntegrationBase` 서브클래싱.

### ForgeFlow에 구현할 것

**파일**: `forgeflow_runtime/adapter_registry.py` (신규)

**기존 manifest.yaml을 그대로 활용** — 새 포맷 도입 없이 기존 YAML을 레지스트리로 로드:

```python
@dataclass
class AdapterInfo:
    name: str                        # "claude", "codex", "generic"
    manifest_path: Path
    runtime_type: str                # "cli-agent"
    generated_filename: str          # "CLAUDE.md", "CODEX.md"
    supports_roles: list[str]        # ["coordinator", "planner", ...]
    agents_dir: Path | None          # agents/ 하위 디렉토리
    hooks_dir: Path | None           # hooks/ 하위 디렉토리

class AdapterRegistry:
    def __init__(self, targets_dir: Path):
        self._adapters: dict[str, AdapterInfo] = {}
        self._scan(targets_dir)

    def _scan(self, targets_dir: Path) -> None:
        """adapters/targets/ 하위 manifest.yaml 자동 발견."""
        for subdir in sorted(targets_dir.iterdir()):
            manifest = subdir / "manifest.yaml"
            if manifest.exists():
                info = self._parse_manifest(subdir.name, manifest)
                self._adapters[info.name] = info

    def get(self, name: str) -> AdapterInfo: ...
    def list_adapters(self) -> list[str]: ...
    def agent_prompt_path(self, adapter_name: str, role: str) -> Path | None: ...
```

**기존 코드와의 연동**:
- `engine.py`의 `adapter_target="claude"` 하드코딩 → `registry.get(adapter_target)` 로 lookup
- `executor.py`의 `dispatch()` — 어댑터별 분기 로직을 레지스트리 기반으로 정리
- 새 어댑터 추가 시: `adapters/targets/<name>/manifest.yaml` + 에이전트 프롬프트 파일만 추가하면 됨

**antigravity 어댑터 처리**:
- `adapters/targets/antigravity/`에 manifest.yaml이 있는지 확인하고 있으면 자동 등록, 없으면 무시

**테스트**: `tests/runtime/test_adapter_registry.py`
- manifest.yaml 스캔/파싱
- get() — 존재/미존재
- list_adapters()
- agent_prompt_path() — role별 에이전트 파일 경로 해석

---

## 구현 순서 (권장)

```
Phase 1: AdapterRegistry (가장 독립적, 부작용 최소)
  ├── adapter_registry.py
  └── test_adapter_registry.py

Phase 2: PresetResolver (generator.py 수정 필요)
  ├── preset_resolver.py
  ├── generator.py 수정 (_load_role_prompt → PresetResolver)
  └── test_preset_resolver.py

Phase 3: WorkflowEngine (가장 영향 범위 큼)
  ├── workflow_engine.py
  ├── stage_transition.py 수정 (YAML 기반으로 교체)
  ├── operator_routing.py 수정 (STAGE_ROLE_MAP → WorkflowDefinition)
  └── test_workflow_engine.py
```

## 제약사항 (반드시 준수)

- **stdlib only** — PyYAML 없이 YAML 파싱 필요. 옵션:
  - JSON으로 대체 (`.forgeflow/workflows/default.json`)
  - 또는 간단한 YAML 파서 직구현 (Spec Kit도 독자 파서 사용)
- 기존 테스트 117개 모두 통과해야 함
- 기존 artifact 스키마(`schema_version: "0.2"`) 변경 없음
- `forgeflow_runtime/` 내부만 수정, `adapters/` 구조는 그대로

## 참고 소스 (Spec Kit)

임시 클론 위치: `/tmp/spec-kit/` (shallow clone)

| 파일 | 차용 포인트 |
|---|---|
| `src/specify_cli/workflows/base.py` | StepBase, StepContext, StepResult 패턴 |
| `src/specify_cli/workflows/steps/gate.py` | gate 스텝 구현 |
| `src/specify_cli/workflows/steps/fan_out.py` | 병렬 팬아웃 |
| `presets/ARCHITECTURE.md` | PresetResolver 설계, composition 전략 |
| `extensions/RFC-EXTENSION-SYSTEM.md` | 확장 발견/카탈로그/훅 |
| `workflows/speckit/workflow.yml` | 실제 워크플로우 YAML 예시 |
