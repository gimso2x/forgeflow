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
- **adapter**: claude | codex | gemini | cursor
- **route**: small | medium | high | epic
- **specialist**: <!-- none or specialist name -->
- **outcome**: success | partial | failed
- **failure_type**: <!-- null or category -->
