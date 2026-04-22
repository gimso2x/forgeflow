# ForgeFlow

ForgeFlow artifact-first delivery harness seed.

## 목적
이 repo는 AI 코딩 에이전트를 위한 범용 잡탕 프레임워크가 아니다.
목표는 더 단순하다.

- 작업을 stage machine으로 관리한다
- artifact를 남겨서 상태를 복구 가능하게 만든다
- worker와 reviewer를 분리해 self-approval를 막는다
- runtime 차이는 adapter로 격리한다
- 작은 일은 가볍게, 큰 일은 엄격하게 처리한다

## 설계 계보
- skeleton: engineering-discipline
- artifact/state rigor: hoyeon
- runtime adapter generation: gstack
- adversarial review discipline: superpowers

## 핵심 stage
1. clarify
2. plan
3. execute
4. spec-review
5. quality-review
6. finalize
7. long-run

## complexity routing
- small → clarify -> execute -> quality-review -> finalize
- medium → clarify -> plan -> execute -> quality-review -> finalize
- large/high-risk → clarify -> plan -> execute -> spec-review -> quality-review -> finalize -> long-run

## source of truth
- 사람 설명용: `docs/`
- 운영 의미론: `policy/canonical/`
- artifact 계약: `schemas/`
- 역할 정의: `prompts/canonical/`
- 런타임 차이: `adapters/targets/`
- 생성물: `adapters/generated/`

## P0 완료 기준
- stage machine 문서화
- core artifact schema 6종 존재
- gate와 review order 정의
- worker / reviewer role 문서화
- adapter manifest 정의
- 예시 task 흐름 존재
- workflow adherence eval 자리 존재
