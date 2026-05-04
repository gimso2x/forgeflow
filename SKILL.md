---
name: forgeflow
description: Artifact-first delivery harness for AI coding agents — staged workflow, gates, evidence, and independent review.
version: "0.2.1"
category: engineering
tags: [ai-agents, workflow, harness, review, artifacts, claude-code, codex]
---

# ForgeFlow

ForgeFlow는 AI coding agent 작업을 채팅 기억이 아니라 **명시적인 stage, 로컬 artifact, gate, evidence, 독립 review**로 진행하게 만드는 artifact-first delivery harness입니다.

## Core Workflow

```text
user request
  → clarify    # 요구사항 정리 → brief.json
  → plan       # 작업 계획 → plan-ledger.json (medium/high)
  → run        # 구현 → run-state.json
  → review     # 독립 검증 → review-report.json
  → ship       # 배포/마무리
```

## Routes (자동 선택)

- **small** (risk: low) — clarify → run → ship (plan 생략)
- **medium** (risk: medium) — clarify → plan → run → review → ship
- **large_high_risk** (risk: high) — 전체 stage + verify pipeline

## Artifacts

`.forgeflow/tasks/<task-id>/` 에 JSON artifact로 상태를 기록:

- `brief.json` — 사용자 요구사항
- `plan-ledger.json` — 작업 계획 (task 분해, 우선순위)
- `decision-log.json` — 설계 결정 이력
- `run-state.json` — 실행 진행 상태
- `review-report.json` — review 결과 (spec + quality)
- `eval-record.json` — 평가 기록
- `checkpoint.json` — 세션 체크포인트

## Key Commands

```bash
# 테스트
source .venv/bin/activate && python3 -m pytest -q

# 구조 검증
python3 scripts/validate_structure.py

# Policy 스캔
python3 scripts/policy_scan.py
```

## Runtime Modules

`forgeflow_runtime/` — 55개 모듈, 67개 importable:

**Core**: engine, executor, orchestrator, generator, operator_routing
**Gates**: gate_evaluation, gate_ralf, ci_gate, constraint_checker
**Artifacts**: artifact_validation, plan_ledger, task_identity, schema_versions
**Review**: adversarial_review, anti_rationalization, evidence_qa, verify_pipeline
**Evolution**: evolution, evolution_audit, evolution_doctor, evolution_proposals, evolution_promotions, crystallization
**Intelligence**: execute_context, progress_tracker, stuck_detector, complexity, cost, telemetry
**Experiment**: experiment/loop, experiment/circuit, experiment/metric, experiment/stopping
**Orchestration**: orchestra/consensus, orchestra/debate, orchestra/pipeline, orchestra/fastest
**Resilience**: stale_recovery, resume_validation, worktree, lightweight_mode
**Parsing**: ears_parser, feedback_router, signal_pipeline, stage_transition
**Utilities**: output_compression, progressive_output, versioning, enforcement_config, policy_loader, profile_detector, coordination

## Adapter Targets

- **Claude Code** — `.claude-plugin/` marketplace plugin + hooks (edit recovery, large file recovery, tool tracker, output truncator, safety guard)
- **Codex** — `CODEX.md` adapter + agent presets + rules
- Both: coordinator, planner, worker, spec-reviewer, quality-reviewer roles

## Slash Skills (Claude Code Plugin)

```text
/forgeflow:init     — task 생성 (task-id, objective, risk)
/forgeflow:clarify  — 요구사항 정리
/forgeflow:plan     — 계획 수립
/forgeflow:run      — 구현 실행
/forgeflow:review   — 독립 검증
/forgeflow:ship     — 배포/마무리
/forgeflow:finish   — 정리 및 종료
```

## Conventions

- Artifact는 항상 JSON. schema_version `0.1`.
- Review는 읽기 전용. 코드 수정 금지 — findings에 기록 후 worker에게 돌려보냄.
- `progress.percentage`는 매 write 시 재계산. timestamp는 실제 ISO 8601.
- Verification은 실제 명령 기반. hallucinated command 금지.
