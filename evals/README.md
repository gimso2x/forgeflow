# ForgeFlow Evals

이 디렉토리는 ForgeFlow가 자기 workflow 규칙을 실제 executable check로 지키는지 검증합니다.

## 실행 명령

fresh clone에서는 repo-managed virtualenv를 먼저 준비합니다.

```bash
make setup
make check-env
make evals
```

`make evals`는 `.venv`의 Python으로 `scripts/run_evals.py`를 실행합니다. eval 실패 시 command는 non-zero로 종료합니다. CI나 로컬 검증에서 이 exit code를 그대로 믿으면 됩니다.

## 현재 eval suite

- `adherence` — route/stage/gate artifact가 정책을 우회하지 못하는지 검증합니다.
  - 상세 fixture 목록: [adherence/README.md](adherence/README.md)
  - 내부 runner: `scripts/run_adherence_evals.py`

## Pass/fail 출력 규칙

- 전체 성공: `FORGEFLOW EVALS: PASS`
- 전체 실패: `FORGEFLOW EVALS: FAIL`
- suite 성공: `EVAL SUITE: <name> PASS`
- suite 실패: `EVAL SUITE: <name> FAIL exit_code=<n>`

새 eval suite를 추가할 때는 `scripts/run_evals.py`의 suite 목록에 넣고, fixture/README/Makefile target을 같이 갱신합니다. 문서만 있는 eval은 eval이 아닙니다. 그건 그냥 소원빌기입니다.

## Eval이 막아주는 상황 예시

아래는 ForgeFlow의 gate와 artifact 규칙이 없으면 어떤 일이 발생하는지 보여주는 실패 시나리오입니다. 각 시나리오는 adherence eval fixture로 자동 검증됩니다.

### Example 1: Review gate bypass

```
Input:
  - execute 단계 완료
  - review-report.json 없음
  - ship 단계 진입 시도

Expected: FAIL
Reason: quality review artifact missing — worker self-report is not approval
```

의도: agent가 "다 됐다"고 말해도 독립 review가 없으면 ship할 수 없습니다.

### Example 2: Plan 없이 medium/high 실행

```
Input:
  - brief.json에 route: "medium"
  - plan.json 없음
  - execute 단계 진입 시도

Expected: FAIL
Reason: medium/high route requires plan artifact before execute
```

의도: medium 이상 작업은 계획 없이 실행을 시작할 수 없습니다.

### Example 3: Spec review 우회

```
Input:
  - brief.json에 route: "high"
  - spec-review 통과 안 함
  - quality-review 진입 시도

Expected: FAIL
Reason: high route requires spec-review approval before quality-review
```

의도: high route에서 spec review를 건너뛰고 품질 검사만 통과하려는 시도를 차단합니다.

### Example 4: Implementation notes 없이 review

```
Input:
  - execute 단계 완료
  - implementation-notes.md 없음
  - review 진입 시도

Expected: MINOR FINDING (not blocker)
Reason: implementation notes missing — execute should have created it
```

의도: 구현 중 발생한 편차와 결정이 추적되지 않으면 review 투명성이 떨어집니다.
