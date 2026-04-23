# Negative medium session-state route drift fixture

Medium route fixture where `checkpoint.json`, `run-state.json`, and `plan-ledger.json` agree on the medium route, but `session-state.json` incorrectly claims `small`.

The adherence eval must reject this instead of trusting stale handoff state.
