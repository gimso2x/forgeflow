# Adapter Model

## 목적
Claude, Codex, Cursor 같은 런타임 차이를 코어 workflow에서 분리한다.

핵심 원칙은 하나다.
**adapter는 표면을 바꾸지만 의미를 바꾸면 안 된다.**

---

## 1. Canonical policy
canonical layer가 정의하는 것:
- stage semantics
- gate semantics
- review order
- artifact contracts
- complexity routing

이건 단 하나의 진실원천이다.

---

## 2. Adapter target
adapter가 담당하는 것:
- prompt formatting
- tool declaration syntax
- runtime-specific config paths
- generated file layout
- capability declaration

adapter가 바꾸면 안 되는 것:
- review 순서
- artifact meaning
- gate meaning
- task risk semantics

---

## 3. Target shape
각 target은 최소한 아래를 가져야 한다.
- `name`
- `runtime_type`
- `input_mode`
- `output_mode`
- `supports_roles`
- `supports_generated_files`
- `generated_filename`
- `recommended_location`
- `surface_style`
- `handoff_format`
- `tooling_constraints`

---

## 4. Generated output
`adapters/generated/`는 빌드 결과물이다.
직접 수정하지 않는다.

P0 기준 generated 산출물:
- `generated/claude/CLAUDE.md`
- `generated/codex/CODEX.md`
- `generated/cursor/HARNESS_CURSOR.md`

주의:
- generated output은 install path / surface style / handoff format까지 target별로 드러내야 한다.
- Cursor용 `.mdc` 또는 `rules/` 레이아웃은 generated markdown 안에서 명시적으로 안내한다.
- canonical semantics를 보존하는 범위에서만 target-aware formatting을 허용한다.

---

## 5. V1 adapter scope
v1에서는 adapter를 과하게 벌리지 않는다.
추천 범위:
- claude
- codex
- cursor

gemini/copilot/opencode는 나중이다.
처음부터 다 하려는 건 욕심이다.
