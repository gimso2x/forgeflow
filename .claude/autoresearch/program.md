# ForgeFlow AutoResearch Program

STATUS: ACTIVE

## 목표
ForgeFlow의 기능 완성도와 안정성을 10분 단위의 작은 실험으로 지속 개선한다.

## 우선순위
1. 안전성: broken state, unsafe automation, stale generated artifacts, CI drift 방지
2. 기능: ForgeFlow 실행/검증/adapter/monitoring 사용성이 실제 프로젝트에서 좋아지는 작은 기능
3. 테스트: 회귀가 잘 잠기는 focused regression 추가
4. 문서: README/plan/spec가 실제 동작과 어긋나는 부분 수정
5. 단순화: 중복 fixture/assertion/helper 정리, 불필요한 복잡도 제거

## 실행 규칙
- 작업 루트는 `/home/ubuntu/work/forgeflow`만 사용한다.
- 매 tick 시작 시 `git status --short --branch`를 확인한다.
- 한 tick에서는 정확히 하나의 작은 개선만 수행한다.
- 변경 전 가설을 한 문장으로 확정한다.
- TDD 우선: 가능하면 실패 테스트를 먼저 추가하고, 최소 구현으로 통과시킨다.
- 모든 변경은 관련 좁은 테스트 → 필요 시 `make validate` 또는 `python -m pytest -q`로 검증한다.
- 실패하면 같은 tick에서 고치거나 변경을 되돌린다.
- `.claude/autoresearch/**` metadata는 관리 가능하지만, 사용자 변경과 섞이지 않게 한다.
- generated artifacts는 명시적으로 필요한 경우에만 재생성한다.
- 대규모 리팩터링, force push, release, 배포, dependency 추가는 하지 않는다.
- PR/merge는 하지 않는다. 변경은 로컬 commit까지만 가능하다.

## 리뷰/논의 규칙
각 tick에서 실제 코드/문서 변경을 만들었다면:
- Claude 관점 리뷰: agent UX, safety, adapter ergonomics, hook/runtime contract를 본다.
- Codex 관점 리뷰: testability, edge cases, implementation correctness, CI drift를 본다.
- 두 관점이 충돌하면 더 단순하고 테스트로 증명 가능한 쪽을 선택한다.
- 리뷰 결과는 experiment note와 results.tsv description에 짧게 남긴다.

## KEEP/DISCARD 기준
KEEP:
- 테스트/검증이 통과하고 기능·안정성·단순성 중 하나가 명확히 개선됨
- 복잡도 증가가 작거나, 중복/불명확성이 줄어듦

DISCARD:
- 검증 실패를 tick 안에서 해결하지 못함
- 사용자 변경을 건드릴 위험이 큼
- 개선보다 복잡도 증가가 큼
- Claude/Codex 리뷰 모두 회의적이고 테스트로 방어 불가

## 정지 조건
- 사용자가 중단 요청
- state.json의 `stop_requested`가 true
- 3회 연속 DISCARD
