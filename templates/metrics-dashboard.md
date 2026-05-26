---
schema: metrics-dashboard/v1
period: <!-- YYYY-MM-DD ~ YYYY-MM-DD or weekly/monthly -->
total_tasks: <!-- N -->
generated: <!-- ISO date -->
---

# ForgeFlow Metrics

## Stage Duration (p50 / p90)
| Stage | p50 | p90 |
|---|---|---|
| clarify | <!-- --> | <!-- --> |
| plan | <!-- --> | <!-- --> |
| execute | <!-- --> | <!-- --> |
| review | <!-- --> | <!-- --> |
| ship | <!-- --> | <!-- --> |

## Failure Distribution
| Failure Type | Count | Rate |
|---|---|---|
| <!-- type --> | <!-- N --> | <!-- %> |

## Token Cost by Adapter
| Adapter | Avg tokens/task | Total |
|---|---|---|
| <!-- adapter --> | <!-- N --> | <!-- N --> |

## Worktree Stability
- **Success rate**: <!-- %>%
- **Avg cleanup time**: <!-- Ns -->

## Route Distribution
| Route | Count | Avg Duration |
|---|---|---|
| small | <!-- N --> | <!-- --> |
| medium | <!-- N --> | <!-- --> |
| high | <!-- N --> | <!-- --> |
| epic | <!-- N --> | <!-- --> |
