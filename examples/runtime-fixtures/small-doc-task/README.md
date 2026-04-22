# Small Runtime Fixture

이 디렉터리는 최소 orchestrator CLI가 `small` route를 끝까지 돌리는 샘플이다.

## 실행
```bash
python3 scripts/run_orchestrator.py run --task-dir examples/runtime-fixtures/small-doc-task --route small
```

## 기대 결과
- `run-state.json` 생성
- `decision-log.json` 생성
- 최종 stage가 `finalize`
