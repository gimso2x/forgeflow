---
name: forgeflow
description: Artifact-first workflow contract plus lightweight enforcement runtime for AI coding agents — staged workflow, gates, evidence, and independent review.
version: "0.11.3"
category: engineering
tags: [ai-agents, workflow, harness, review, artifacts, claude-code, codex, gemini-cli]
---

# ForgeFlow

ForgeFlow는 Claude Code, Codex, Gemini CLI를 위한 artifact-first workflow contract plus lightweight enforcement runtime입니다. AI coding agent 작업을 채팅 기억이 아니라 **명시적인 stage, 로컬 artifact, gate, evidence, 독립 review**로 진행하게 만듭니다.

## Core Workflow

```text
user request
  → clarify    # 요구사항 정리 → brief.json
  → milestone  # (Epic 전용) 마일스톤 분해 → roadmap.json
  → plan       # 작업 계획 → plan-ledger.json (medium/high/epic)
  → execute    # 구현, updates run-state.json
  → review     # 독립 검증 → review-report.json
  → ship       # 배포/마무리
```

## Routes (자동 선택)

- **small** (risk: low) — clarify → execute → ship (plan 생략)
- **medium** (risk: medium) — clarify → plan → execute → review → ship
- **high** (risk: high) — 전체 stage + verify pipeline
- **epic** (risk: critical) — milestone 기반 계층적 분해 및 점진적 실행

## Artifacts

`.forgeflow/tasks/<task-id>/` 에 JSON artifact로 상태를 기록:

- `brief.json` — 요구사항, 전문가 선택(specialists), 제약사항
- `roadmap.json` — Epic 전용 마일스톤 및 진행 상태
- `plan-ledger.json` — 작업 계획 (task 분해, 우선순위)
- `decision-log.json` — 설계 결정 및 가설 디버깅 이력
- `run-state.json` — 실행 진행 상태 (TDD 사이클 포함)
- `review-report.json` — review 결과 (spec + quality)
- `eval-record.json` — 평가 기록
- `checkpoint.json` — 세션 체크포인트

## Key Commands

```bash
# 테스트
source .venv/bin/activate && python3 -m pytest -q

# Evals
make evals                         # all executable eval suites
make adherence-evals               # workflow/stage/gate adherence only

# 구조 검증
python3 scripts/validate_structure.py

# Policy 스캔
python3 scripts/policy_scan.py
```

## Runtime Modules

`forgeflow_runtime/` — 92개 Python import surface. Domain packages are preferred once a domain has multiple cohesive modules; flat `evolution_*` imports remain compatibility shims only.

**Core**: engine, executor, orchestrator, generator, operator_routing
**Gates**: gate_evaluation, gate_ralf, ci_gate, constraint_checker
**Artifacts**: artifact_validation, artifact_migrations, plan_ledger, task_identity, schema_versions
**Review**: adversarial_review, anti_rationalization, evidence_qa, verify_pipeline
**Evolution**: evolution package (`audit`, `cases`, `doctor`, `execution`, `lifecycle`, `observations`, `promotion_*`, `promotions`, `proposals`, `rules`) plus legacy shim modules
**Intelligence**: execute_context, progress_tracker, stuck_detector, complexity, cost, telemetry
**Environment**: env_adapter, profile_detector, preset_resolver, harness_profiles
**Experiment**: experiment/loop, experiment/circuit, experiment/git_ops, experiment/metric, experiment/simplicity, experiment/stopping
**Orchestration**: orchestra/consensus, orchestra/debate, orchestra/pipeline, orchestra/fastest, orchestra/strategy
**Resilience**: stale_recovery, resume_validation, worktree, lightweight_mode
**Parsing**: ears_parser, feedback_router, signal_pipeline, stage_transition
**Utilities**: output_compression, progressive_output, versioning, enforcement_config, policy_loader, coordination

## Adapter Targets

- **Claude Code** — `.claude-plugin/` marketplace plugin + hooks (edit recovery, large file recovery, tool tracker, output truncator, safety guard)
- **Codex** — `CODEX.md` adapter + agent presets + rules
- **Gemini CLI** — `GEMINI.md` adapter + extension context + instructions
- All: coordinator, planner, worker, spec-reviewer, quality-reviewer roles

## Slash Skills (Claude Code Plugin)

```text
/forgeflow:init     — task 생성 (task-id, objective, risk)
/forgeflow:clarify  — 요구사항 정리
/forgeflow:milestone — Epic 전용 마일스톤 관리
/forgeflow:plan     — 계획 수립
/forgeflow:execute      — 구현 실행
/forgeflow:review   — 독립 검증
/forgeflow:ship     — 배포/마무리
/forgeflow:finish   — 정리 및 종료
```

## Conventions

- Artifact는 항상 JSON. 새 artifact schema_version은 현재 `0.2`이며 `schema_versions.py`/`schemas/*.schema.json`가 canonical입니다 (`0.1`은 migration 입력).
- Review는 읽기 전용. 코드 수정 금지 — findings에 기록 후 worker에게 돌려보냄.
- `progress.percentage`는 매 write 시 재계산. timestamp는 실제 ISO 8601.
- Verification은 실제 명령 기반. hallucinated command 금지.
