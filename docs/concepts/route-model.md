# Route Model

## 세 가지 Route

ForgeFlow는 작업의 리스크와 복잡도에 따라 세 route로 자동 분류합니다.

### small
- **대상**: 오타 수정, 간단한 설정 변경, one-liner 수정
- **흐름**: clarify → run → finish
- **artifact**: brief.json만 필수
- **review**: 생략

### medium
- **대상**: 기능 추가/수정, 다중 파일 변경, API 스펙 조정
- **흐름**: clarify → plan → run → review → ship
- **artifact**: brief.json, plan-ledger.json, run-state.json, review-report.json
- **review**: 권장

### high
- **대상**: 아키텍처 변경, 보안 관련, 마이그레이션, 대규모 리팩토링
- **흐름**: clarify → plan → run → review → ship (모든 gate 강제)
- **artifact**: 전체 세트 + 보충 문서
- **review**: 필수 (gate 강제)

## 자동 Route 선택

`auto_route_for_task_dir()`이 `brief.json`의 risk 필드와 작업 특성을 기준으로 route를 고릅니다.

수동으로 지정할 수도 있습니다:

```bash
forgeflow init --task-id my-task --objective "..." --risk high
```

## Architecture 패턴

**high** 라우트 작업은 자동으로 더 강건한 실행 패턴을 씁니다:

- **fan-out/fan-in + producer-reviewer**: security, migration, refactor, architecture
- **pipeline + producer-reviewer**: bug, fix, qa, test, regression
- **기본**: producer-reviewer + pipeline

## Operator Shell

`forgeflow_runtime/operator_routing.py`이 route 분류 로직을 담당합니다. operator shell은 사람이 로컬에서 상태를 점검할 때 쓰는 얇은 표면이며, 새 workflow 의미론이 아닙니다.

---

정본은 [docs/operator-shell.md](../operator-shell.md)을 참고하세요.
