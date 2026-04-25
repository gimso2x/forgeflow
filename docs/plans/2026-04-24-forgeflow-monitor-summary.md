# ForgeFlow Monitor Summary Implementation Plan

> **For Hermes:** Implement directly with strict TDD. Keep this feature read-only, local-only, and dependency-free.

**Goal:** Add a lightweight CLI that summarizes recent ForgeFlow task artifacts so operators can see completion, blocking, review rejection, and repeated failure patterns without opening every JSON file by hand.

**Architecture:** `scripts/forgeflow_monitor.py` scans a local `.forgeflow/tasks` directory, reads known artifact files when present, tolerates missing/malformed artifacts, and emits either Markdown or JSON. It does not mutate tasks, call LLMs, run verification commands, or send notifications.

**Tech Stack:** Python stdlib (`argparse`, `json`, `pathlib`, `collections`), pytest, existing repo validation.

---

## Non-Goals

- No external DB, SaaS dashboard, cron, Telegram/Slack alerts, or web UI.
- No LLM-generated recommendations.
- No artifact mutation.
- No schema migration.
- No automatic task fixing.

## Data sources

For each task directory under `.forgeflow/tasks/*`, read when present:

```text
run-state.json
review-report.json
eval-record.json
decision-log.json
```

Minimum useful fields:
- task id: directory name, `task_id`, or `id`
- route/current stage/status from `run-state.json`
- review approved/rejected status and findings from `review-report.json`
- eval status/score when present
- decision or blocked/error messages when present

---

### Task 1: Add failing tests for JSON summary

**Files:**
- Create: `tests/test_forgeflow_monitor.py`

**Test behavior:**
1. Create three fake tasks under `tmp_path/.forgeflow/tasks`:
   - completed task with approved review
   - blocked task with `blocked_reason`
   - rejected task with `review-report.json` containing findings
2. Run through the repo-managed target:
   ```bash
   make setup
   make check-env
   make monitor-summary-json
   ```
3. Assert JSON includes:
   - `summary.total_tasks == 3`
   - `summary.completed == 1`
   - `summary.blocked == 1`
   - `summary.review_rejected == 1`
   - top failure pattern includes the blocked/review finding text

**RED command:**
```bash
pytest tests/test_forgeflow_monitor.py::test_monitor_json_summarizes_task_health -q
```

### Task 2: Add failing tests for Markdown and graceful fallback

**Files:**
- Modify: `tests/test_forgeflow_monitor.py`

**Test behavior:**
1. Markdown output contains:
   - `# ForgeFlow monitor summary`
   - `Total tasks: 3`
   - `Review rejected: 1`
   - task table rows
2. Missing artifacts do not crash; a task directory with no JSON still appears as `unknown`.
3. Malformed JSON is counted in `artifact_errors` but does not crash.

**RED command:**
```bash
pytest tests/test_forgeflow_monitor.py -q
```

### Task 3: Implement monitor CLI

**Files:**
- Create: `scripts/forgeflow_monitor.py`

**Implementation outline:**
- `load_json(path) -> tuple[dict | None, str | None]`
- `discover_tasks(tasks_root, recent) -> list[Path]`, newest by mtime descending
- `summarize_task(task_dir) -> dict`
- `build_summary(tasks) -> dict`
- `render_markdown(report) -> str`
- CLI args:
  ```text
  --tasks .forgeflow/tasks
  --recent 10
  --format md|json
  --output optional/path
  ```
- Exit 0 for empty/missing tasks root with zero summary.

### Task 4: Document usage

**Files:**
- Modify: `README.md`

Add a local monitoring section with the current repo-managed entrypoints:
```bash
make setup
make check-env
make monitor-summary
make monitor-summary-json
```

Explicitly say the Make targets use the repo-managed Python environment, read local artifacts only, and are not a dashboard.

### Task 5: Verify and commit

**Commands:**
```bash
python -m py_compile scripts/forgeflow_monitor.py
pytest tests/test_forgeflow_monitor.py -q
make validate
python -m pytest -q
git diff --check
```

**Commit:**
```bash
git add docs/plans/2026-04-24-forgeflow-monitor-summary.md scripts/forgeflow_monitor.py tests/test_forgeflow_monitor.py README.md
git commit -m "feat: add local forgeflow monitor summary"
```
