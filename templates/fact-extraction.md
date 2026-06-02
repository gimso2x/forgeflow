# Fact Extraction Guide

<!-- Used during ship and long-run stages to extract structured facts from task artifacts -->
<!-- "기억은 저장이 아니라 다음 실행 조건" -->

## Extraction Criteria

Extract a fact when:

| # | Signal | Fact Type | Example |
|---|--------|-----------|---------|
| 1 | Architectural choice in implementation-notes | `decision` | "상태 관리는 서버 컴포넌트에서 계산, 클라이언트는 표현만" |
| 2 | Hard constraint discovered | `constraint` | "이 프로젝트는 pnpm만 사용, npm/yarn 금지" |
| 3 | User-stated preference | `preference` | "에러 메시지는 한국어로 작성" |
| 4 | Reusable pattern that worked | `pattern` | "범위 수정은 항상 git diff로 확인 후 적용" |
| 5 | Bug fixed with root cause | `bug_fix` | "useEffect 누락으로 무한 리렌더 → 의존성 배열에 상태 추가" |
| 6 | Codebase behavior found | `discovery` | "이 API 라우트는 내부적으로 캐시 무효화를 트리거함" |

## Quality Criteria

Each fact must:

- Be a **self-contained statement** — understandable without the original task context
- Have a **concrete source** artifact (not chat sentiment)
- Be **reusable** in future tasks (not task-specific status)
- Include **domain** classification
- State **confidence**: high (review-verified), medium (observed), low (preliminary)

## Skip When

- Task was trivial (formatting, typo fix, config tweak)
- No decisions, constraints, or patterns emerged
- Content is already captured by an evolution rule
- Statement is vague ("이 프로젝트는 복잡하다")

## Route Limits

- **small**: Skip entirely
- **medium**: Max 3 facts, high-confidence only
- **high/epic**: No limit, but prefer quality over quantity

## Command Reference

```bash
python3 scripts/forgeflow_fact_store.py add \
  --content "팩트 내용" \
  --type decision \
  --domain architecture \
  --confidence high \
  --source-task task-xxx \
  --tags "tag1,tag2"
```
