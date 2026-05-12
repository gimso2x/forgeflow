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
