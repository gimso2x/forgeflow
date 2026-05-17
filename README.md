# ForgeFlow

ForgeFlow is an artifact-first workflow contract plus a lightweight enforcement runtime for Claude Code, Codex, and Gemini CLI. AI coding agent가 채팅 기억에 의존하지 않고 **명시적인 artifact, gate, evidence, 독립 review**로 작업하게 만듭니다.

현재 릴리즈: **v0.11.2**

## 누가 왜 쓰나

Claude Code, Codex, Gemini CLI 같은 AI coding agent를 쓰는 개발자를 위한 도구입니다. Agent가 대화를 잊거나, 검증 없이 코드를 고치거나, 리스크 큰 작업을 계획 없이 실행하는 문제를 막습니다.

**핵심 가치:**
- **Session 간 context 유실 방지** — 모든 단계가 로컬 artifact로 남습니다
- **독립 review** — 작성자와 검토자가 분리된 evidence 기반 review
- **Risk-based routing** — 작업 크기와 위험도에 따라 small/medium/high/epic 경로 자동 선택

## 30초 퀵스타트

**Claude Code:**

> 주의: /plugin marketplace add 및 claude plugin ... 명령어는 현재 Claude Code에서 지원되지 않습니다.
> 현재 작동하는 설치 경로는 아래 수동 설치 섹션을 사용하세요.

```text
/plugin marketplace add https://github.com/gimso2x/forgeflow
/plugin install forgeflow
```

**Gemini CLI:**
```bash
# 이 명령은 즉시 설치됩니다. (consent 플래그로 확인 생략)
gemini extensions install https://github.com/gimso2x/forgeflow --ref main --consent
```

**Codex:**
```bash
curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - -- --dry-run
curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - --
```

**Local CLI:**
```bash
python3 -m pip install "forgeflow-runtime @ git+https://github.com/gimso2x/forgeflow.git"
forgeflow-runtime --help
```

자세한 가이드는 [INSTALL.md](INSTALL.md), [Claude Code 가이드](docs/guides/claude-code.md), [Codex 가이드](docs/guides/codex.md), [Gemini 가이드](docs/guides/gemini.md), [Windows 가이드](docs/guides/windows.md)을 참고하세요.

## 기본 워크플로우

```text
요청 → clarify → milestone → plan → execute → review → ship
```

- **clarify** — 요청을 목표, 제약, 성공 조건, route로 정리합니다
- **milestone** — epic route일 때 전체 작업을 큰 단위의 마일스톤으로 분할합니다
- **plan** — medium 이상이거나 모호한 작업을 실행 가능한 계획으로 쪼갭니다
- **execute** — 승인된 brief와 plan 범위 안에서 작업합니다
- **review** — 결과를 evidence와 artifact 기준으로 독립 검토합니다
- **ship** — handoff를 정리하고 PR/merge/keep/discard 결정을 다룹니다

각 stage는 slash skill로 실행합니다: `/forgeflow:clarify`, `/forgeflow:milestone`, `/forgeflow:plan`, `/forgeflow:execute`, `/forgeflow:review`, `/forgeflow:ship`. 사용자가 매번 stage를 운영해야 한다는 뜻은 아닙니다 — agent가 다음 stage를 자연스럽게 이어받고, stage 경계에서 다음 단계로 넘어갈지 확인합니다.

자세한 stage 규칙은 [docs/workflow.md](docs/workflow.md)을 보세요.

## 첫 실행 예시

설치 후 바로 작은 작업 하나를 ForgeFlow 흐름으로 실행해볼 수 있습니다.

```text
/forgeflow:clarify Fix the failing dashboard test
/forgeflow:execute
/forgeflow:review
/forgeflow:ship
```

### 5분 로컬 smoke path

Plugin 설치 전에도 repo clone만 있으면 runtime artifact 흐름을 확인할 수 있습니다. 아래 명령은 현재 프로젝트 아래 `.forgeflow/tasks/demo-readme/`에만 파일을 만듭니다.

```bash
make setup
make check-env
make demo

# 또는 수동으로 runtime artifact를 확인하려면:
python3 scripts/run_orchestrator.py init --task-id demo-readme --objective "Update README quickstart" --risk small
python3 scripts/run_orchestrator.py status --task-dir .forgeflow/tasks/demo-readme
```

예상 흐름:
- `init`은 `brief.json`, `run-state.json`, `checkpoint.json`, `session-state.json`을 생성합니다.
- 첫 `status`의 `current_stage`는 `clarify`이고, `next_action`은 `clarify` 실행을 안내해야 합니다.
- 이후 실제 agent 흐름은 `/forgeflow:clarify → /forgeflow:execute → /forgeflow:review → /forgeflow:ship` 또는 `scripts/run_orchestrator.py clarify/execute/status`로 이어갑니다.

예상 결과:
- `.forgeflow/tasks/<task-id>/brief.json` — 목표, 범위, route, acceptance criteria
- optional `.forgeflow/tasks/<task-id>/plan.json` / `plan-ledger.json` — medium 이상이거나 모호한 작업의 실행 계획
- `.forgeflow/tasks/<task-id>/run-state.json` — 현재 stage, gate, evidence 상태
- `.forgeflow/tasks/<task-id>/review-report.json` 또는 role별 review report — 독립 review 결과
- 최종 ship/handoff summary — 변경 파일, 검증, review verdict, PR/merge/keep/discard 판단

더 긴 실제 흐름은 [examples/end-to-end-nextjs-flow.md](examples/end-to-end-nextjs-flow.md)를 보세요.

## Installation

자세한 설치 가이드는 [INSTALL.md](INSTALL.md)를 참고하세요.

### 수동 Claude Code 설치

> **현재 권장 설치 방법입니다.**

플러그인 설치가 안 되는 환경이면 generated adapter를 프로젝트 루트에 복사합니다.

```bash
git clone https://github.com/gimso2x/forgeflow.git path/to/forgeflow
cp path/to/forgeflow/adapters/generated/claude/CLAUDE.md ./CLAUDE.md
```

Claude Code는 프로젝트 루트의 `CLAUDE.md`를 읽습니다.

검증:

```bash
claude -p "Read CLAUDE.md first. Reply with the ForgeFlow stage order."
```

### Claude Code plugin

> 주의: /plugin marketplace add 및 claude plugin ... 명령어는 현재 Claude Code에서 지원되지 않습니다.
> 현재 작동하는 설치 경로는 아래 수동 설치 섹션을 사용하세요.

```bash
claude plugin marketplace add https://github.com/gimso2x/forgeflow
claude plugin install forgeflow
```

[자세히 보기 →](docs/guides/claude-code.md)

### Codex plugin

```bash
curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - -- --dry-run
curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - --
```

Codex Desktop 재시작 후 local marketplace에서 enable. [자세히 보기 →](docs/guides/codex.md)

### Local CLI

```bash
python3 -m pip install -e .
forgeflow --help
```

Windows PowerShell:

```powershell
.\scripts\setup.ps1
.\scripts\validate.ps1
```

[자세히 보기 →](INSTALL.md)

## 핵심 개념

- **Artifact model** — brief, milestone, plan, run-state, review-report 등 모든 단계가 검증 가능한 JSON artifact를 생성합니다 → [docs/artifact-model.md](docs/artifact-model.md)
- **Review model** — evidence 기반 독립 review contract. 작성자와 검토자 분리 → [docs/review-model.md](docs/review-model.md)
- **Route model (small/medium/high/epic)** — 작업 위험도와 복잡도에 따라 실행 경로를 자동 선택합니다 → [docs/operator-shell.md](docs/operator-shell.md)
- **2-axis specialist selection** — route 축(작업 크기)과 spec 축(전문 에이전트)이 독립 작동합니다. security/backend/frontend/infra/ux/perf 6개 도메인 → [docs/workflow.md](docs/workflow.md)
- **Adapter boundary** — Claude Code, Codex, Gemini CLI에서 동일한 workflow를 보장하는 adapter 계층 → [docs/adapter-model.md](docs/adapter-model.md)

### Artifact 빠른 지도

처음에는 아래 파일만 보면 됩니다. 모두 `.forgeflow/tasks/<task-id>/` 아래에 생성됩니다.

- `brief.json`: 목표, 범위, 제약, acceptance criteria, route. 사용자가 가장 먼저 확인할 요구사항 파일입니다.
- `run-state.json`: 현재 stage, gate 통과 여부, retry, review 승인 플래그. “지금 어디까지 왔나”를 봅니다.
- `checkpoint.json`: 재개 지점과 `next_action`. agent/session이 끊겼을 때 이 파일 기준으로 이어갑니다.
- `session-state.json`: runtime pointer. 보통 사람이 직접 수정하지 않습니다.
- `plan.json` / `plan-ledger.json`: medium/high/epic route에서 단계별 실행 계획과 현재 task를 추적합니다.
- `review-report.json`, `review-report-spec.json`, `review-report-quality.json`: 독립 review 결과. `approved`면 blocker가 없어야 하고 다음 stage로 안전해야 합니다.

### Route와 review 의무

- `small`: 짧은 변경. 최소 smoke/build/lint/type check 후 review를 선택할 수 있습니다.
- `medium`: 계획 단위로 실행합니다. 실행 후 review가 필요합니다.
- `high`: spec review와 quality review가 필수입니다. 실행 완료 후 독립 review로 넘어갑니다.
- `epic`: milestone 단위로 쪼개고, 각 milestone 뒤 독립 review가 필수입니다.

## Evaluation

ForgeFlow evals는 workflow 계약이 실제 executable check로 유지되는지 검증합니다. Unit test가 코드 동작을 보는 쪽이라면, eval은 stage/gate/artifact/review 정책이 우회되지 않는지 보는 쪽입니다.

```bash
make setup
make check-env
make evals
```

- 전체 eval 실행: `make evals`
- adherence suite만 실행: `make adherence-evals`
- 결과 해석과 suite 추가 절차: [docs/evaluation-guide.md](docs/evaluation-guide.md)
- suite별 fixture 설명: [evals/README.md](evals/README.md)

## 문제 해결

자주 묻는 질문과 해결 방법:

- **Plugin 설치 후 인식 안 됨** — Claude Code나 Codex Desktop을 재시작하세요. `scripts/smoke.sh`로 post-install smoke를 확인합니다
- **Plugin smoke matrix** — local disposable Next.js 프로젝트(`npx create-next-app@latest`)로 non-mutating plugin integration 검증: `scripts/ci_plugin_smoke_matrix.py --surface codex --route-label medium`, `scripts/ci_plugin_smoke_matrix.py --surface claude --route-label small`
- **Real plugin E2E** — live agent가 disposable project에 실제 파일을 쓰는 검증: `scripts/real_plugin_e2e.py --surface claude --route high`, `scripts/real_plugin_e2e.py --surface codex --route high`. 일부 Linux host에서 Codex `workspace-write` sandbox는 bubblewrap `RTM_NEWADDR: Operation not permitted`로 실패할 수 있어, 이 disposable-only script는 Codex 실행에 `--dangerously-bypass-approvals-and-sandbox`를 사용합니다. 실제 사용자 repo에 이 플래그를 무지성 복붙하지 마세요.
- **Codex plugin doctor** — `python3 scripts/codex_plugin_doctor.py --project .` 로 CLI, marketplace, preset 상태를 점검합니다
- **Artifact schema 오류** — `python3 scripts/validate_structure.py` 로 project 구조를 검증합니다
- **Gate에서 missing artifact로 멈춤** — `checkpoint.json`의 `current_stage`와 `next_action`을 보고 해당 stage가 요구하는 `brief.json`, `plan-ledger.json`, `run-state.json`, `review-report*.json`가 task dir에 있는지 확인하세요.
- **task_id mismatch** — 한 task dir 안의 artifact는 모두 같은 `task_id`여야 합니다. 다른 task에서 복사한 JSON을 섞지 말고 새 task dir에서 다시 `init`하거나 artifact의 task id를 일관되게 맞추세요.
- **approved review가 거부됨** — `verdict: "approved"`인 review report에는 `open_blockers: []`가 필요하고, `safe_for_next_stage`가 `false`이면 안 됩니다.
- **specialist 오류** — `required_specialists`와 `skipped_specialists`에 같은 specialist를 동시에 넣을 수 없습니다. skip이 있으면 `skip_rationale`도 있어야 합니다.
- **Windows local runtime** — [Windows 가이드](docs/guides/windows.md)의 PowerShell wrapper 흐름을 사용하세요
- **Debug 가이드** — [docs/debugging/](docs/debugging/)에 root-cause tracing, defense-in-depth 문서가 있습니다

## 더 보기

- [INSTALL.md](INSTALL.md) — 상세 설치, 업데이트, Windows 절차
- [CHANGELOG.md](CHANGELOG.md) — 버전별 변경 사항
- [memory/README.md](memory/README.md) — project memory 보존 기준 (`memory/`는 cache or hidden agent state가 아닙니다)
- [evals/README.md](evals/README.md) — eval suite 실행 가이드
- [scripts/README.md](scripts/README.md) — local scripts, visual tooling, validation helper
- [docs/architecture.md](docs/architecture.md) — 전체 아키텍처 개요
- [docs/api.md](docs/api.md) — `forgeflow_runtime` 패키지의 공개 API 및 내부 모듈 경계 안내

## 철학

- Artifact over chat memory
- Evidence over claims
- Stage gates over vibes
- Independent review over self-approval
- One workflow across Claude Code, Codex, and Gemini CLI

## License

MIT.
