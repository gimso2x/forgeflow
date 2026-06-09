---
schema: telemetry-event/v1
task_id: <!-- TASK_ID -->
---

# Telemetry Event Log

## Events

### <!-- timestamp -->
- **event**: stage_start | stage_complete | stage_fail | token_usage | boundary_alert
- **stage**: clarify | plan | execute | review | ship
- **duration_seconds**: <!-- N -->
- **tokens_used**: <!-- N -->
- **model**: <!-- model id -->
- **adapter**: claude | codex | cursor
- **route**: small | medium | high | epic
- **specialist**: <!-- none or specialist name -->
- **outcome**: success | partial | failed
- **failure_type**: <!-- null or category -->

## 예시

### 정상 완료 이벤트

```yaml
### 2026-05-29T14:30:00+09:00
- **event**: stage_complete
- **stage**: execute
- **task_id**: feature-map-danji-marker-9a2
- **outcome**: success
- **route**: medium
- **adapter**: claude
- **timestamp**: 2026-05-29T14:30:00+09:00
```

### 경계 위반 이벤트

```yaml
### 2026-05-29T14:35:00+09:00
- **event**: boundary_alert
- **stage**: execute
- **task_id**: feature-naver-marker-guide-a29
- **outcome**: partial
- **route**: medium
- **adapter**: claude
- **timestamp**: 2026-05-29T14:35:00+09:00
```
