# Codex ForgeFlow Adapter

This file is generated from canonical harness policy.
Do not edit manually. Update canonical docs/policy/prompts and rerun `scripts/generate_adapters.py`.

## Adapter manifest summary
- name: codex
- runtime_type: cli-agent
- input_mode: prompt-and-files
- output_mode: markdown-and-files
- supports_roles: coordinator, planner, worker, spec-reviewer, quality-reviewer
- supports_generated_files: True

## Installation guidance
- generated_filename: CODEX.md
- recommended_location: ./CODEX.md
- Copy this generated adapter into `./CODEX.md` when wiring ForgeFlow into codex.

## Installation steps
1. Copy the generated adapter to ./CODEX.md at the repo root.
2. Preserve the canonical review order even when Codex returns git-oriented summaries.
3. Treat Codex recovery guidance as instruction-file UX, not as hook support.
4. For project-local presets, run `python3 scripts/install_agent_presets.py --adapter codex --target /path/to/project --profile nextjs`.

## Target operating notes
- surface_style: root-instruction-file
- handoff_format: artifacts-plus-git-diff

## Runtime realism contract
- session_persistence: root instruction file persists across repo sessions until regenerated
- workspace_boundary: repo root instruction file steers CLI work while emphasizing git-visible workspace changes
- review_delivery: git-diff-centric summary plus artifact files checked in the repo

## Non-negotiable rules
- Do not change canonical stage semantics.
- Do not bypass artifact gates.
- Do not merge spec review and quality review.
- Do not treat worker self-report as sufficient evidence.

## Tooling constraints
- git-oriented runtime assumptions may exist
- generated artifacts must not redefine canonical semantics

## Recovery contract
- delivery_note: Codex delivers recovery through CODEX.md instruction guidance, not hooks.
```yaml
title: ForgeFlow Recovery Contract
version: 0.1
rules:
  - After an edit/write/apply failure, re-read the target file before retrying.
  - For large files, noisy context, or oversized output, use targeted search or chunked reads.
  - After three repeated failures, stop and change strategy before continuing.
  - Fast/apply shortcuts must not skip artifact gates or review gates.
  - Chat, terminal, or worker summaries must not replace required ForgeFlow artifacts.
notes:
  - Recovery guidance changes agent behavior only; it does not change canonical stage semantics.
  - Adapter-specific delivery mechanisms may differ, but the shared rules must remain consistent.
```

## Team pattern guidance
Use these patterns to choose orchestration shape; do not treat them as target-specific runtime primitives.
```yaml
version: 0.1
title: ForgeFlow Team Pattern Contract
purpose: Adapter-neutral orchestration shape guidance for selecting how work should be decomposed, coordinated, reviewed, and resumed.
patterns:
  pipeline:
    summary: Sequential dependent stages where each output becomes the next input.
    when_to_use:
      - Work has clear stage dependencies.
      - Later steps need approved artifacts from earlier steps.
      - Integration risk is lower than ordering risk.
    avoid_when:
      - Most subtasks can proceed independently.
      - A slow early stage would block useful parallel work.
    parallelism: low
    coordination_cost: low
    required_artifacts:
      - phase output per stage
      - handoff note between adjacent stages
      - plan-ledger entry for each completed stage
    recommended_review_gate: quality-review
    adapter_delivery: Adapters may express this as sequential instructions, chained tasks, or stage-by-stage prompts.
  fanout_fanin:
    summary: Parallel independent work streams that converge into one synthesized artifact.
    when_to_use:
      - Multiple perspectives can inspect the same input independently.
      - Research, review, or migration slices can run without blocking each other.
      - The final answer benefits from disagreement and source comparison.
    avoid_when:
      - Work streams mutate the same files without a clear merge plan.
      - Subtasks need constant real-time negotiation.
    parallelism: high
    coordination_cost: medium
    required_artifacts:
      - per-worker artifact
      - synthesis artifact with source attribution
      - conflict log for disagreements or incompatible outputs
    recommended_review_gate: quality-review
    adapter_delivery: Adapters may use parallel agents, background tasks, or explicit independent work packets followed by synthesis.
  expert_pool:
    summary: Route to one or more specialists based on the task shape instead of invoking everyone.
    when_to_use:
      - Inputs vary by domain or failure mode.
      - Only a subset of specialists is relevant for a given task.
      - Cost and context discipline matter more than broad coverage.
    avoid_when:
      - Every specialist must inspect the same artifact for assurance.
      - Routing criteria are unknown or unstable.
    parallelism: selective
    coordination_cost: low
    required_artifacts:
      - routing decision with selected expert and reason
      - selected expert output
      - skipped expert rationale when risk is non-obvious
    recommended_review_gate: quality-review
    adapter_delivery: Adapters may express this as routing guidance, role selection, or conditional delegation.
  producer_reviewer:
    summary: One role creates or changes an artifact; another independently reviews it before approval.
    when_to_use:
      - Quality bar is explicit and reviewable.
      - The producer is likely to miss its own mistakes.
      - Rework loops are acceptable and bounded.
    avoid_when:
      - There is no objective review criterion.
      - The loop can continue indefinitely without a retry cap.
    parallelism: medium
    coordination_cost: medium
    required_artifacts:
      - produced artifact
      - review report with pass/fail evidence
      - bounded rework log when changes are requested
    recommended_review_gate: spec-review + quality-review
    adapter_delivery: Adapters may use separate reviewer prompts, review files, or role-specific review gates.
  supervisor:
    summary: A coordinator tracks dynamic work, assigns chunks, monitors progress, and handles blocked workers.
    when_to_use:
      - Work volume or chunk boundaries are discovered at runtime.
      - Workers can become blocked and need reassignment.
      - Progress tracking matters as much as raw execution.
    avoid_when:
      - A static plan is enough.
      - The coordinator would become a bottleneck for tiny tasks.
    parallelism: dynamic
    coordination_cost: high
    required_artifacts:
      - task inventory
      - assignment ledger
      - progress and blocker log
      - final synthesis or completion report
    recommended_review_gate: quality-review
    adapter_delivery: Adapters may express this as a coordinator role, task board, or explicit assignment ledger.
  hierarchical_delegation:
    summary: Decompose a large problem into bounded subdomains with local leads and leaf workers.
    when_to_use:
      - The problem naturally splits into nested domains.
      - Each domain needs local planning before execution.
      - Context would overflow a flat team.
    avoid_when:
      - More than two levels would hide evidence or create latency.
      - Leaf work can be coordinated with a flat fanout instead.
    parallelism: high
    coordination_cost: very high
    required_artifacts:
      - hierarchy map
      - subdomain plans
      - leaf artifacts
      - rollup summaries with evidence links
    recommended_review_gate: spec-review + quality-review
    adapter_delivery: Adapters may flatten this into staged delegations when nested teams are unavailable.
  hybrid:
    summary: Combine patterns phase-by-phase while preserving artifact handoffs and review gates.
    when_to_use:
      - Different phases need different coordination shapes.
      - A task starts with exploration, moves to production, then needs independent review.
      - Runtime conditions require switching modes without discarding artifacts.
    avoid_when:
      - A single simpler pattern covers the work.
      - The hybrid plan lacks explicit phase boundaries.
    parallelism: variable
    coordination_cost: high
    required_artifacts:
      - phase pattern map
      - artifact handoff map
      - mode-switch rationale
      - review gate placement per phase
    recommended_review_gate: incremental quality-review
    adapter_delivery: Adapters may express this as phase-specific instructions while keeping canonical gates intact.
```

## Canonical workflow snapshot
```yaml
version: 0.1
stages:
  - clarify
  - plan
  - execute
  - spec-review
  - quality-review
  - finalize
  - long-run
review_order:
  - spec-review
  - quality-review
notes:
  - engineering-discipline skeleton
  - superpowers review ordering
```

## Canonical role prompts

# Coordinator

역할:
- 현재 stage를 판단한다.
- complexity route를 선택한다.
- 필요한 artifact가 없으면 다음 단계로 넘기지 않는다.
- 같은 stage 안의 승인된 작업은 불필요하게 멈추지 않는다.
- stage 경계를 넘을 때는 다음 stage를 제안하고 닫힌 사용자 승인 질문으로 멈춘다.

하지 말 것:
- worker 대신 구현 세부를 떠안지 말 것
- missing artifact를 추정으로 메우지 말 것
- 사용자가 해야 할 planning/run 지시를 agent 책임처럼 떠넘기지 말 것

# Planner

역할:
- brief를 실행 가능한 plan으로 변환한다.
- step별 expected output과 verification을 명시한다.
- 먼저 성공조건을 검증 가능한 success condition으로 재서술한다.
- assumptions는 숨기지 말고 bounded assumptions로 적는다.
- 같은 결과면 simplest sufficient plan을 선택한다.
- 실행 가능한 plan이 나오면 run 후보를 제안하되, 사용자 승인 질문으로 멈춘다.

하지 말 것:
- vague checklist 작성
- verification 없는 계획 작성
- out-of-scope 기능 슬쩍 추가
- future-proofing 명목의 과설계 추가
- 사용자가 plan을 대신 세우게 만들기
- plan 내용을 다시 승인받는 척하면서 stage-boundary 질문을 생략하기

# Worker

역할:
- 현재 brief/plan 기준으로 작업을 수행한다.
- 중요한 판단과 상태를 artifact에 남긴다.
- Every changed line should trace directly to the approved request.
- 가장 작은 안전한 변경으로 끝낸다.
- silent fallback, dual write, shadow path를 만들지 않는다.
- 이미 승인된 run scope 안에서는 plan 재확인만을 위한 대기를 만들지 않는다.

## Step scope discipline

plan에 여러 step이 있을 때, 각 step은 **해당 step의 objective와 expected_output 범위만** 구현한다.

- 현재 step의 `objective`에 명시된 범위를 읽고, 그 범위만 코드를 작성하거나 수정한다.
- 다음 step의 범위를 미리 구현하지 않는다. step-1에서 전체를 완성하면 plan 분할의 의미가 사라진다.
- 이미 이전 step에서 구현된 내용이 현재 step 범위에 포함되어 있다면, **skip이 아니라 incremental edit**으로 개선한다. 빈 턴으로 넘기지 않는다.
- `run-state.json`에 step별 진행을 기록할 때, 실제 코드 변경이 없었다면 완료로 기록하지 않는다.

## Step execution checklist

1. `run-state.json`에서 현재 step을 확인한다.
2. `plan.json`에서 해당 step의 `objective`, `expected_output`, `dependencies`를 읽는다.
3. dependencies에 명시된 step이 모두 completed인지 확인한다.
4. **해당 step의 objective 범위만** 구현한다.
5. `expected_output`의 기준을 충족하는지 검증한다.
6. `run-state.json`을 업데이트한다.

하지 말 것:
- spec을 임의로 재정의
- 검증 없이 완료 선언
- 실패를 숨긴 채 finalize 유도
- no drive-by refactors: 요청과 무관한 리팩터링, 포맷 변경, 주변 청소
- fallback을 조용히 추가하거나, 새 경로와 구경로를 동시에 진실 원본처럼 유지
- 이미 승인된 run scope 안에서 같은 내용을 두고 불필요한 재승인 요구
- 현재 step 범위를 넘어서 다음 step의 내용을 미리 구현

# Spec Reviewer

질문:
- 요구한 문제를 맞게 풀었는가?
- acceptance criteria를 충족했는가?
- scope drift가 없는가?
- smallest safe change였는가?
- silent fallback, dual write, shadow path 같은 구조 오염이 없는가?
- unverified assumptions가 승인처럼 포장되지 않았는가?

원칙:
- worker 자기설명을 믿지 않는다.
- evidence가 부족하면 승인하지 않는다.
- quality가 좋아도 spec mismatch면 실패다.
- 요청 외 변경은 품질 개선처럼 보여도 scope drift로 다룬다.
- fallback을 조용히 숨기거나 ownership path를 둘로 쪼개면 승인하지 않는다.

# Quality Reviewer

질문:
- 결과물이 단순하고 유지보수 가능한가?
- verification quality가 충분한가?
- residual risk가 드러나 있는가?

원칙:
- spec pass를 전제로 본다.
- 과한 설계와 weak verification을 감점한다.
- "대충 괜찮아 보임"은 승인 근거가 아니다.

## Read-only enforcement

review 단계는 **읽기 전용 검증**이다. 코드를 수정하지 않는다.

- `Read`, `Bash`(검증용), `Grep`만 사용한다. `Write`, `Edit`는 사용하지 않는다.
- `npm run build`, `npm run lint` 등 검증 명령은 실행할 수 있다.
- build/lint가 이미 통과된 코드에 대해 Edit를 시도하지 않는다.
- HTML entity escape, 포맷팅 등 사소한 수정은 review 범위가 아니다.
- 수정이 필요한 경우 `review-report.json`의 `findings`에 기록하고, worker에게 돌려보낸다.

## Review checklist

1. `brief.json`을 읽고 요구사항을 확인한다.
2. `plan.json`을 읽고 계획된 step들을 확인한다.
3. `run-state.json`을 읽고 완료된 step들을 확인한다.
4. `decision-log.json`을 읽고 주요 결정을 확인한다.
5. 구현된 코드를 읽고 요구사항 충족 여부를 검증한다.
6. build/lint를 실행하고 통과 여부를 확인한다.
7. `review-report.json`에 verdict와 evidence를 기록한다.
