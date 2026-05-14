# ForgeFlow

AI coding agent가 채팅 기억에 의존하지 않고, **명시적인 artifact, gate, evidence, 독립 review**로 작업하게 만드는 artifact-first delivery harness. Claude Code와 Codex에서 같은 workflow를 사용합니다.

현재 릴리즈: **v0.8.1**

## 누가 왜 쓰나

Claude Code, Codex 같은 AI coding agent를 쓰는 개발자를 위한 도구입니다. Agent가 대화를 잊거나, 검증 없이 코드를 고치거나, 리스크 큰 작업을 계획 없이 실행하는 문제를 막습니다.

**핵심 가치:**
- **Session 간 context 유실 방지** — 모든 단계가 로컬 artifact로 남습니다
- **독립 review** — 작성자와 검토자가 분리된 evidence 기반 review
- **Risk-based routing** — 작업 크기와 위험도에 따라 small/medium/high 경로 자동 선택

## 30초 퀵스타트

**Claude Code:**
```text
/plugin marketplace add https://github.com/gimso2x/forgeflow
/plugin install forgeflow
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

자세한 가이드는 [INSTALL.md](INSTALL.md), [Claude Code 가이드](docs/guides/claude-code.md), [Codex 가이드](docs/guides/codex.md), [Windows 가이드](docs/guides/windows.md)을 참고하세요.

## 기본 워크플로우

```text
요청 → clarify → plan → execute → review → ship
```

- **clarify** — 요청을 목표, 제약, 성공 조건, route로 정리합니다
- **plan** — medium 이상이거나 모호한 작업을 실행 가능한 계획으로 쪼갭니다
- **execute** — 승인된 brief와 plan 범위 안에서 작업합니다
- **review** — 결과를 evidence와 artifact 기준으로 독립 검토합니다
- **ship** — handoff를 정리하고 PR/merge/keep/discard 결정을 다룹니다

각 stage는 slash skill로 실행합니다: `/forgeflow:clarify`, `/forgeflow:plan`, `/forgeflow:execute`, `/forgeflow:review`, `/forgeflow:ship`. 사용자가 매번 stage를 운영해야 한다는 뜻은 아닙니다 — agent가 다음 stage를 자연스럽게 이어받고, stage 경계에서 다음 단계로 넘어갈지 확인합니다.

자세한 stage 규칙은 [docs/workflow.md](docs/workflow.md)을 보세요.

## Installation

자세한 설치 가이드는 [INSTALL.md](INSTALL.md)를 참고하세요.

### Claude Code plugin

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

- **Artifact model** — brief, plan, run-state, review-report 등 모든 단계가 검증 가능한 JSON artifact를 생성합니다 → [docs/artifact-model.md](docs/artifact-model.md)
- **Review model** — evidence 기반 독립 review contract. 작성자와 검토자 분리 → [docs/review-model.md](docs/review-model.md)
- **Route model (small/medium/high)** — 작업 위험도와 복잡도에 따라 실행 경로를 자동 선택합니다 → [docs/operator-shell.md](docs/operator-shell.md)
- **2-axis specialist selection** — route 축(작업 크기)과 spec 축(전문 에이전트)이 독립 작동합니다. security/backend/frontend/infra/ux/perf 6개 도메인 → [docs/workflow.md](docs/workflow.md)
- **Adapter boundary** — Claude Code와 Codex에서 동일한 workflow를 보장하는 adapter 계층 → [docs/adapter-model.md](docs/adapter-model.md)

## 문제 해결

자주 묻는 질문과 해결 방법:

- **Plugin 설치 후 인식 안 됨** — Claude Code나 Codex Desktop을 재시작하세요. `scripts/smoke.sh`로 post-install smoke를 확인합니다
- **Plugin smoke matrix** — local disposable Next.js 프로젝트(`npx create-next-app@latest`)로 non-mutating plugin integration 검증: `scripts/ci_plugin_smoke_matrix.py --surface codex --route-label medium`, `scripts/ci_plugin_smoke_matrix.py --surface claude --route-label small`
- **Real plugin E2E** — live agent가 disposable project에 실제 파일을 쓰는 검증: `scripts/real_plugin_e2e.py --surface claude --route high`, `scripts/real_plugin_e2e.py --surface codex --route high`. 일부 Linux host에서 Codex `workspace-write` sandbox는 bubblewrap `RTM_NEWADDR: Operation not permitted`로 실패할 수 있어, 이 disposable-only script는 Codex 실행에 `--dangerously-bypass-approvals-and-sandbox`를 사용합니다. 실제 사용자 repo에 이 플래그를 무지성 복붙하지 마세요.
- **Codex plugin doctor** — `python3 scripts/codex_plugin_doctor.py --project .` 로 CLI, marketplace, preset 상태를 점검합니다
- **Artifact schema 오류** — `python3 scripts/validate_structure.py` 로 project 구조를 검증합니다
- **Windows local runtime** — [Windows 가이드](docs/guides/windows.md)의 PowerShell wrapper 흐름을 사용하세요
- **Debug 가이드** — [docs/debugging/](docs/debugging/)에 root-cause tracing, defense-in-depth 문서가 있습니다

## 더 보기

- [INSTALL.md](INSTALL.md) — 상세 설치, 업데이트, Windows 절차
- [CHANGELOG.md](CHANGELOG.md) — 버전별 변경 사항
- [memory/README.md](memory/README.md) — project memory 보존 기준 (`memory/`는 cache or hidden agent state가 아닙니다)
- [evals/README.md](evals/README.md) — eval suite 실행 가이드
- [scripts/README.md](scripts/README.md) — local scripts, visual tooling, validation helper
- [docs/architecture.md](docs/architecture.md) — 전체 아키텍처 개요

## 철학

- Artifact over chat memory
- Evidence over claims
- Stage gates over vibes
- Independent review over self-approval
- One workflow across Claude Code and Codex

## License

MIT.
