"""Tests for forgeflow_runtime/orchestrator.py — public API + internal helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from .helpers import add_checkpoint_and_session, medium_task_dir, small_task_dir, write_json_file
from forgeflow_runtime.errors import RuntimeViolation
from forgeflow_runtime.executor import RunTaskResult
from forgeflow_runtime.orchestrator import (
    TransitionResult,
    _artifact_ref_path,
    _execution_payload,
    _infer_route_for_recovery,
    _allocate_parallel_worker_worktrees,
    _resolve_route,
    _sync_parallel_worktree_plan,
    _validate_review_semantics,
    advance_to_next_stage,
    clarify_task,
    escalate_route,
    init_task,
    resume_task,
    retry_stage,
    start_task,
    status_summary,
    step_back,
)
from forgeflow_runtime.policy_loader import RuntimePolicy, load_runtime_policy

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def policy() -> RuntimePolicy:
    return load_runtime_policy(REPO_ROOT)


# =========================================================================
# 1–5: init_task tests
# =========================================================================


class TestInitTask:
    def test_init_task_small_route(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "small-task"
        project_root = tmp_path / "project"
        project_root.mkdir()
        result = init_task(task_dir, policy, task_id="t-01", objective="do it", risk_level="low", project_root=project_root)

        assert result["route"] == "small"
        assert result["task_id"] == "t-01"
        # init only creates the 4 core artifacts — no drafts
        for name in ["brief.json", "run-state.json", "checkpoint.json", "session-state.json"]:
            assert (task_dir / name).exists(), f"{name} missing"
        # docs/ and tasks/ should NOT exist after init
        assert not (task_dir / "docs").exists(), "docs/ should not exist after init"
        assert not (task_dir / "tasks").exists(), "tasks/ should not exist after init"
        assert not (task_dir / "CLAUDE.md").exists(), "CLAUDE.md should not exist after init"
        # no selected_architecture in init result
        assert "selected_architecture" not in result

        # verify brief has empty arrays (raw objective only)
        brief = json.loads((task_dir / "brief.json").read_text())
        assert brief["task_id"] == "t-01"
        assert brief["risk_level"] == "low"
        assert brief["in_scope"] == []
        assert brief["constraints"] == []

        # verify run-state current_stage is first stage of small route
        run_state = json.loads((task_dir / "run-state.json").read_text())
        small_stages = _resolve_route(policy, "small")
        assert run_state["current_stage"] == small_stages[0]

        # verify next_action
        assert "clarify" in result["next_action"]

    def test_init_task_medium_route(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "medium-task"
        result = init_task(task_dir, policy, task_id="t-02", objective="fix bug in REST api endpoint", risk_level="medium")

        assert result["route"] == "medium"
        assert result["task_id"] == "t-02"
        for name in ["brief.json", "run-state.json", "checkpoint.json", "session-state.json"]:
            assert (task_dir / name).exists(), f"{name} missing"
        # init does NOT create docs/ or markdown drafts
        assert not (task_dir / "docs").exists()
        assert "selected_architecture" not in result

        run_state = json.loads((task_dir / "run-state.json").read_text())
        medium_stages = _resolve_route(policy, "medium")
        assert run_state["current_stage"] == medium_stages[0]

    def test_init_task_rejects_existing_artifacts(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "task"
        task_dir.mkdir()
        (task_dir / "brief.json").write_text("{}")

        with pytest.raises(RuntimeViolation, match="init refuses to overwrite"):
            init_task(task_dir, policy, task_id="t-01", objective="x", risk_level="low")

    def test_init_task_invalid_risk_level(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "task"
        with pytest.raises(RuntimeViolation, match="unknown risk level"):
            init_task(task_dir, policy, task_id="t-01", objective="x", risk_level="critical")

    def test_init_task_creates_valid_checkpoint_and_session(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        """Verify checkpoint and session-state have correct route/stage refs."""
        task_dir = tmp_path / "small-task"
        init_task(task_dir, policy, task_id="t-chk", objective="x", risk_level="low")

        checkpoint = json.loads((task_dir / "checkpoint.json").read_text())
        session = json.loads((task_dir / "session-state.json").read_text())
        assert checkpoint["route"] == "small"
        assert session["route"] == "small"
        assert session["latest_checkpoint_ref"] == "checkpoint.json"
        assert session["run_state_ref"] == "run-state.json"


# =========================================================================
# clarify_task tests
# =========================================================================


class TestClarifyTask:
    def test_clarify_small_route_creates_drafts(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        project_root = tmp_path / "project"
        project_root.mkdir()
        task_dir = tmp_path / "small-task"
        init_task(task_dir, policy, task_id="t-01", objective="do it", risk_level="low", project_root=project_root)

        result = clarify_task(task_dir, policy, project_root=project_root)

        assert result["task_id"] == "t-01"
        assert result["route"] == "small"
        assert "producer-reviewer" in result["selected_architecture"]

        # docs/ and tasks/ now exist after clarify
        for name in [
            "docs/PRD.md",
            "docs/ARCHITECTURE.md",
            "docs/QA.md",
            "docs/DECISIONS.md",
            "tasks/init-summary.md",
            "CLAUDE.md",
        ]:
            assert (task_dir / name).exists(), f"{name} missing"

        # agents/skills go in project_root
        assert (project_root / ".claude" / "agents").exists()
        assert (project_root / ".claude" / "skills").exists()

        # Verify domain-specific agents have proper structure
        agents_dir = project_root / ".claude" / "agents"
        agent_files = list(agents_dir.glob("*.md"))
        assert len(agent_files) >= 2, f"Expected ≥2 agents, got {agent_files}"

        for agent_file in agent_files:
            text = agent_file.read_text()
            assert "## Input Artifacts" in text, f"{agent_file.name} missing Input Artifacts"

        # Verify domain-specific skills have proper structure
        skills_dir = project_root / ".claude" / "skills"
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
        assert len(skill_dirs) >= 1, f"Expected ≥1 skill, got {skill_dirs}"

        for skill_dir in skill_dirs:
            skill_file = skill_dir / "SKILL.md"
            assert skill_file.exists(), f"{skill_dir.name}/SKILL.md missing"
            text = skill_file.read_text()
            assert "---" in text, f"{skill_dir.name} missing frontmatter"

        pointer = (task_dir / "CLAUDE.md").read_text()
        assert "ForgeFlow" in pointer
        assert "Work Mode" in pointer
        assert "/forgeflow:review" in pointer

        # verify brief is enriched
        brief = json.loads((task_dir / "brief.json").read_text())
        assert brief["in_scope"] == ["do it"]
        assert brief["constraints"] == ["initialized from operator CLI"]

        # verify domain analysis in PRD
        prd_text = (task_dir / "docs/PRD.md").read_text()
        assert "## Domain Analysis" in prd_text
        assert "general" in prd_text
        assert "feature" in prd_text
        assert "## Domain-Specific Considerations" in prd_text

        # verify domain context in ARCHITECTURE
        arch_text = (task_dir / "docs/ARCHITECTURE.md").read_text()
        assert "## Domain Context" in arch_text
        assert "## Architecture Considerations" in arch_text

        # verify QA domain checklist
        qa_text = (task_dir / "docs/QA.md").read_text()
        assert "## Domain Context" in qa_text
        assert "## Domain-Specific QA Checklist" in qa_text

    def test_clarify_medium_route_domain_analysis(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "medium-task"
        init_task(task_dir, policy, task_id="t-02", objective="fix bug in REST api endpoint", risk_level="medium")

        result = clarify_task(task_dir, policy)

        assert result["route"] == "medium"
        assert result["selected_architecture"] == "pipeline + producer-reviewer"

        # verify domain analysis detects api and bugfix
        prd_text = (task_dir / "docs/PRD.md").read_text()
        assert "api" in prd_text
        assert "bugfix" in prd_text

        # verify QA has domain-specific checklist for api
        qa_text = (task_dir / "docs/QA.md").read_text()
        assert "API contract verified" in qa_text
        assert "Bug reproduced before fix" in qa_text

    def test_clarify_selects_higher_rigor_architecture_for_risky_work(
        self, tmp_path: Path, policy: RuntimePolicy
    ) -> None:
        task_dir = tmp_path / "risky-task"
        init_task(
            task_dir,
            policy,
            task_id="t-risk",
            objective="security migration for auth architecture",
            risk_level="high",
        )

        result = clarify_task(task_dir, policy)

        assert result["selected_architecture"] == "fan-out/fan-in + producer-reviewer"
        architecture = (task_dir / "docs/ARCHITECTURE.md").read_text()
        assert "fan-out/fan-in + producer-reviewer" in architecture
        assert "security migration for auth architecture" in (task_dir / "tasks/init-summary.md").read_text()

    def test_clarify_enriches_brief(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        """Clarify fills in empty brief fields with domain analysis results."""
        task_dir = tmp_path / "brief-task"
        init_task(task_dir, policy, task_id="t-brief", objective="do something", risk_level="low")

        # Before clarify, brief has empty arrays
        brief_before = json.loads((task_dir / "brief.json").read_text())
        assert brief_before["in_scope"] == []
        assert brief_before["constraints"] == []

        clarify_task(task_dir, policy)

        # After clarify, brief is enriched
        brief_after = json.loads((task_dir / "brief.json").read_text())
        assert brief_after["in_scope"] == ["do something"]
        assert brief_after["constraints"] == ["initialized from operator CLI"]
        assert brief_after["acceptance_criteria"] == ["task artifacts are initialized and schema-valid"]


def test_sync_parallel_worktree_plan_records_conflicts_in_run_state_and_ledger() -> None:
    plan_ledger = {
        "schema_version": "0.2",
        "task_id": "task-001",
        "route": "medium",
        "current_task_id": "ui",
        "tasks": [
            {
                "id": "ui",
                "title": "UI",
                "depends_on": [],
                "files": ["src/login.tsx"],
                "parallel_safe": True,
                "status": "in_progress",
                "required_gates": ["validator"],
                "evidence_refs": [],
                "attempt_count": 0,
            },
            {
                "id": "api",
                "title": "API",
                "depends_on": [],
                "files": ["src/login.tsx"],
                "parallel_safe": True,
                "status": "pending",
                "required_gates": ["validator"],
                "evidence_refs": [],
                "attempt_count": 0,
            },
        ],
    }
    run_state: dict[str, Any] = {}
    decision_log = {"schema_version": "0.2", "task_id": "task-001", "entries": []}

    summary = _sync_parallel_worktree_plan(plan_ledger, run_state, decision_log)

    assert summary == {
        "parallel_safe": False,
        "worker_count": 2,
        "conflicts": [{"path": "src/login.tsx", "task_ids": ["ui", "api"], "reason": "shared_path"}],
    }
    assert plan_ledger["parallel_execution"] == summary
    assert run_state["parallel_execution"] == summary
    assert decision_log["entries"][-1]["category"] == "execution"
    assert "blocked" in decision_log["entries"][-1]["decision"]


def test_allocate_parallel_worker_worktrees_creates_task_scoped_artifacts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "forgeflow@example.test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "ForgeFlow Test"], cwd=repo, check=True)
    (repo / "src").mkdir()
    (repo / "src" / "ui.tsx").write_text("export const ui = 1\n", encoding="utf-8")
    (repo / "src" / "api.ts").write_text("export const api = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True, text=True)

    task_dir = repo / ".forgeflow" / "tasks" / "task-001"
    task_dir.mkdir(parents=True)
    (task_dir / "brief.json").write_text(
        json.dumps({"schema_version": "0.2", "task_id": "task-001", "use_worktree": True}),
        encoding="utf-8",
    )
    plan_ledger = {
        "schema_version": "0.2",
        "task_id": "task-001",
        "route": "medium",
        "current_task_id": "ui",
        "tasks": [
            {"id": "ui", "files": ["src/ui.tsx"], "status": "pending"},
            {"id": "api", "files": ["src/api.ts"], "status": "pending"},
        ],
    }
    run_state = {"schema_version": "0.2", "task_id": "task-001"}
    decision_log = {"schema_version": "0.2", "task_id": "task-001", "entries": []}

    _sync_parallel_worktree_plan(plan_ledger, run_state, decision_log)
    workers = _allocate_parallel_worker_worktrees(task_dir, plan_ledger, run_state, decision_log)

    assert [worker["plan_task_id"] for worker in workers] == ["ui", "api"]
    assert run_state["workers"] == workers
    assert (task_dir / "workers" / "ui" / "worker-state.json").exists()
    assert (task_dir / "workers" / "ui" / "worktree.json").exists()
    assert (task_dir / "workers" / "ui" / "output.md").exists()
    assert all(Path(worker["worktree"]["path"]).exists() for worker in workers)
    assert decision_log["entries"][-1]["decision"] == "parallel worker worktrees allocated"


# =========================================================================
# 6–8: start_task tests
# =========================================================================


class TestStartTask:
    def test_start_task_small_route(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "my-task"
        result = start_task(task_dir, policy, "small")

        assert result["route"] == "small"
        assert "brief.json" in result["created_artifacts"]
        assert "run-state.json" in result["created_artifacts"]
        assert "checkpoint.json" in result["created_artifacts"]
        assert "session-state.json" in result["created_artifacts"]
        assert "decision-log.json" in result["created_artifacts"]
        # small route should NOT have plan/plan-ledger
        assert "plan.json" not in result["created_artifacts"]
        assert "plan-ledger.json" not in result["created_artifacts"]

        run_state = json.loads((task_dir / "run-state.json").read_text())
        small_stages = _resolve_route(policy, "small")
        assert run_state["current_stage"] == small_stages[0]

    def test_start_task_medium_route(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "med-task"
        result = start_task(task_dir, policy, "medium")

        assert result["route"] == "medium"
        assert "plan.json" in result["created_artifacts"]
        assert "plan-ledger.json" in result["created_artifacts"]

        plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text())
        assert plan_ledger["route"] == "medium"

    def test_start_task_rejects_existing_files(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "task"
        task_dir.mkdir()
        (task_dir / "brief.json").write_text("{}")

        with pytest.raises(RuntimeViolation, match="start requires an empty"):
            start_task(task_dir, policy, "small")


# =========================================================================
# 9–11: resume_task tests
# =========================================================================


class TestResumeTask:
    def test_resume_task_basic(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        """resume_task succeeds after start_task on a small route."""
        task_dir = tmp_path / "resume-task"
        start_task(task_dir, policy, "small")

        result = resume_task(task_dir, policy, "small")

        assert result["route"] == "small"
        assert result["current_stage"] == _resolve_route(policy, "small")[0]
        assert "next_action" in result

    def test_resume_task_missing_checkpoint(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = small_task_dir(tmp_path)
        # checkpoint is missing
        with pytest.raises(RuntimeViolation, match="resume requires checkpoint"):
            resume_task(task_dir, policy, "small")

    def test_resume_task_missing_session_state(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = small_task_dir(tmp_path)
        add_checkpoint_and_session(task_dir, route_name="small")
        # remove session-state
        (task_dir / "session-state.json").unlink()

        with pytest.raises(RuntimeViolation, match="resume requires session-state"):
            resume_task(task_dir, policy, "small")


# =========================================================================
# 12: status_summary
# =========================================================================


class TestStatusSummary:
    def test_status_summary_returns_expected_fields(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "status-task"
        start_task(task_dir, policy, "small")

        result = status_summary(task_dir, policy, "small")

        for field in ["task_id", "route", "current_stage", "current_task_id",
                      "open_blockers", "required_gates", "latest_review_verdict", "next_action"]:
            assert field in result, f"missing field: {field}"
        assert result["route"] == "small"
        assert isinstance(result["required_gates"], list)
        assert isinstance(result["open_blockers"], list)


class TestParallelWorkerExecution:
    def test_advance_execute_immediately_dispatches_allocated_workers(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "parallel-execute"
        start_task(task_dir, policy, "small")
        wt_a = tmp_path / "wt-a"
        wt_b = tmp_path / "wt-b"
        wt_a.mkdir()
        wt_b.mkdir()
        run_state = json.loads((task_dir / "run-state.json").read_text())
        run_state["workers"] = [
            {
                "schema_version": "1.0",
                "task_id": run_state["task_id"],
                "plan_task_id": "ui",
                "status": "pending",
                "owned_paths": ["app/page.tsx"],
                "worktree": {"path": str(wt_a), "branch": "ff/ui", "active": True},
                "output_ref": "workers/ui/output.md",
            },
            {
                "schema_version": "1.0",
                "task_id": run_state["task_id"],
                "plan_task_id": "api",
                "status": "pending",
                "owned_paths": ["api/route.ts"],
                "worktree": {"path": str(wt_b), "branch": "ff/api", "active": True},
                "output_ref": "workers/api/output.md",
            },
        ]
        write_json_file(task_dir / "run-state.json", run_state)

        result = advance_to_next_stage(
            task_dir,
            policy,
            "small",
            "clarify",
            execute_immediately=True,
        )

        persisted = json.loads((task_dir / "run-state.json").read_text())
        assert result.next_stage == "execute"
        assert result.execution["worker_count"] == 2
        assert [worker["status"] for worker in persisted["workers"]] == ["completed", "completed"]
        assert (task_dir / "workers" / "ui" / "output.md").exists()

    def test_finalize_merges_review_approved_parallel_worker_worktrees(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
        (repo / "frontend.txt").write_text("base\n", encoding="utf-8")
        (repo / "backend.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, stdout=subprocess.DEVNULL)

        task_dir = repo / ".forgeflow" / "tasks" / "task-001"
        task_dir.mkdir(parents=True)
        write_json_file(
            task_dir / "brief.json",
            {
                "schema_version": "0.2",
                "task_id": "task-001",
                "objective": "Merge approved parallel workers",
                "in_scope": ["parallel merge"],
                "out_of_scope": [],
                "constraints": ["local only"],
                "acceptance_criteria": ["approved worker changes are merged"],
                "risk_level": "medium",
                "use_worktree": True,
            },
        )
        plan_ledger = {
            "schema_version": "0.2",
            "task_id": "task-001",
            "route": "medium",
            "completed_stages": [],
            "completed_gates": [],
            "retries": {},
            "current_task_id": "frontend",
            "tasks": [
                {
                    "id": "frontend",
                    "title": "frontend",
                    "depends_on": [],
                    "files": ["frontend.txt"],
                    "parallel_safe": True,
                    "status": "done",
                    "required_gates": ["machine"],
                    "evidence_refs": ["workers/frontend/output.md"],
                    "attempt_count": 0,
                },
                {
                    "id": "backend",
                    "title": "backend",
                    "depends_on": [],
                    "files": ["backend.txt"],
                    "parallel_safe": True,
                    "status": "done",
                    "required_gates": ["machine"],
                    "evidence_refs": ["workers/backend/output.md"],
                    "attempt_count": 0,
                },
            ],
        }
        run_state = {
            "schema_version": "0.2",
            "task_id": "task-001",
            "current_stage": "quality-review",
            "status": "in_progress",
            "completed_gates": ["clarification_complete", "plan_executable", "execution_evidenced"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "frontend",
            "spec_review_approved": False,
            "quality_review_approved": True,
        }
        decision_log = {"schema_version": "0.2", "task_id": "task-001", "entries": []}
        _sync_parallel_worktree_plan(plan_ledger, run_state, decision_log)
        workers = _allocate_parallel_worker_worktrees(task_dir, plan_ledger, run_state, decision_log)
        for worker in workers:
            path = Path(worker["worktree"]["path"])
            if worker["plan_task_id"] == "frontend":
                (path / "frontend.txt").write_text("base\nfrontend\n", encoding="utf-8")
            else:
                (path / "backend.txt").write_text("base\nbackend\n", encoding="utf-8")
            worker["status"] = "completed"
            write_json_file(task_dir / "workers" / worker["plan_task_id"] / "worker-state.json", worker)

        run_state["workers"] = workers
        write_json_file(task_dir / "plan-ledger.json", plan_ledger)
        write_json_file(task_dir / "run-state.json", run_state)
        write_json_file(
            task_dir / "review-report-quality.json",
            {
                "schema_version": "0.2",
                "task_id": "task-001",
                "review_type": "quality",
                "verdict": "approved",
                "findings": ["worker outputs are review-approved"],
                "approved_by": "test-reviewer",
                "next_action": "finalize",
                "safe_for_next_stage": True,
                "open_blockers": [],
            },
        )

        result = advance_to_next_stage(task_dir, policy, "medium", "quality-review")

        assert result.next_stage == "finalize"
        assert (repo / "frontend.txt").read_text(encoding="utf-8") == "base\nfrontend\n"
        assert (repo / "backend.txt").read_text(encoding="utf-8") == "base\nbackend\n"
        persisted = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
        assert [item["status"] for item in persisted["worker_merge_results"]] == ["merged", "merged"]
        assert [worker["status"] for worker in persisted["workers"]] == ["merged", "merged"]


# =========================================================================
# 13–14: step_back
# =========================================================================


class TestStepBack:
    def test_step_back_basic(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        """step_back moves to previous stage and clears review flags."""
        task_dir = tmp_path / "step-task"
        start_task(task_dir, policy, "small")
        small_stages = _resolve_route(policy, "small")
        # Advance to stage index 1 (execute for small route)
        result = advance_to_next_stage(
            task_dir, policy, "small", small_stages[0],
        )
        assert result.next_stage == small_stages[1]

        # Now set some review flags and step back
        run_state = json.loads((task_dir / "run-state.json").read_text())
        run_state["spec_review_approved"] = True
        run_state["quality_review_approved"] = True
        write_json_file(task_dir / "run-state.json", run_state)

        stepped = step_back(task_dir, policy, "small", small_stages[1])
        assert stepped["current_stage"] == small_stages[0]
        assert stepped["status"] == "in_progress"
        # quality_review should be cleared since quality-review was removed
        assert stepped["quality_review_approved"] is False

    def test_step_back_first_stage_raises(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "step-first"
        start_task(task_dir, policy, "small")
        small_stages = _resolve_route(policy, "small")

        with pytest.raises(RuntimeViolation, match="cannot step back before first stage"):
            step_back(task_dir, policy, "small", small_stages[0])


# =========================================================================
# 15–16: escalate_route
# =========================================================================


class TestEscalateRoute:
    def test_escalate_route_basic(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "esc-task"
        start_task(task_dir, policy, "small")

        result = escalate_route(task_dir, "small")

        assert result["current_stage"] == "clarify"
        assert result["status"] == "blocked"

    def test_escalate_route_invalid_from(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "esc-task"
        start_task(task_dir, policy, "small")

        with pytest.raises(RuntimeViolation, match="unknown route for escalation"):
            escalate_route(task_dir, "nonexistent")


# =========================================================================
# 17–18: retry_stage
# =========================================================================


class TestRetryStage:
    def test_retry_stage_basic(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "retry-task"
        start_task(task_dir, policy, "small")
        small_stages = _resolve_route(policy, "small")

        result = retry_stage(task_dir, small_stages[1], max_retries=2)

        assert result["retries"].get(small_stages[1]) == 1
        assert result["current_stage"] == small_stages[1]
        assert result["status"] == "in_progress"

    def test_retry_stage_exceeds_budget(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "retry-max-task"
        start_task(task_dir, policy, "small")
        small_stages = _resolve_route(policy, "small")

        # Exhaust retries
        retry_stage(task_dir, small_stages[1], max_retries=2)
        retry_stage(task_dir, small_stages[1], max_retries=2)

        with pytest.raises(RuntimeViolation, match="retry budget exceeded"):
            retry_stage(task_dir, small_stages[1], max_retries=2)


# =========================================================================
# 19–21: _infer_route_for_recovery
# =========================================================================


class TestInferRouteForRecovery:
    def test_uses_plan_ledger(self) -> None:
        plan_ledger = {"route": "medium"}
        checkpoint = {"route": "medium"}
        assert _infer_route_for_recovery(
            checkpoint=checkpoint, plan_ledger=plan_ledger, fallback_route="small"
        ) == "medium"

    def test_falls_back_to_checkpoint(self) -> None:
        plan_ledger = None
        checkpoint = {"route": "small"}
        assert _infer_route_for_recovery(
            checkpoint=checkpoint, plan_ledger=plan_ledger, fallback_route="medium"
        ) == "small"

    def test_conflict_raises(self) -> None:
        plan_ledger = {"route": "medium"}
        checkpoint = {"route": "small"}
        with pytest.raises(RuntimeViolation, match="does not match canonical route"):
            _infer_route_for_recovery(
                checkpoint=checkpoint, plan_ledger=plan_ledger, fallback_route="small"
            )


# =========================================================================
# 22: _execution_payload format
# =========================================================================


class TestExecutionPayload:
    def test_execution_payload_format(self) -> None:
        result = RunTaskResult(
            status="success",
            artifacts_produced=["plan.json"],
            token_usage={"prompt": 100, "completion": 50},
            raw_output="done",
            error=None,
        )
        payload = _execution_payload(
            stage="execute", role="coder", adapter="claude", result=result, use_real=True
        )
        assert payload["stage"] == "execute"
        assert payload["role"] == "coder"
        assert payload["adapter"] == "claude"
        assert payload["execution_mode"] == "real"
        assert payload["status"] == "success"
        assert payload["artifacts_produced"] == ["plan.json"]
        assert payload["token_usage"] == {"prompt": 100, "completion": 50}
        assert "error" not in payload

    def test_execution_payload_includes_error(self) -> None:
        result = RunTaskResult(
            status="failure",
            artifacts_produced=[],
            token_usage={},
            error="timeout",
        )
        payload = _execution_payload(
            stage="clarify", role="planner", adapter="codex", result=result
        )
        assert payload["error"] == "timeout"
        assert payload["execution_mode"] == "stub"
        assert "STUB EXECUTION" in payload["warning"]


# =========================================================================
# 23–24: _artifact_ref_path
# =========================================================================


class TestArtifactRefPath:
    def test_validates_absolute(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeViolation, match="must be task-relative"):
            _artifact_ref_path(
                tmp_path, str(Path.cwd().anchor or Path.cwd()), source_name="test.json", field_name="ref"
            )

    def test_validates_escape(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeViolation, match="escapes task directory"):
            _artifact_ref_path(
                tmp_path, "../secrets/key.pem", source_name="test.json", field_name="ref"
            )


# =========================================================================
# 25–26: _validate_review_semantics
# =========================================================================


class TestValidateReviewSemantics:
    def test_approved_with_blockers_raises(self) -> None:
        payload = {"verdict": "approved", "open_blockers": ["gate-x-failed"]}
        with pytest.raises(RuntimeViolation, match="cannot declare open_blockers"):
            _validate_review_semantics(payload, source_name="review.json")

    def test_approved_with_safe_false_raises(self) -> None:
        payload = {"verdict": "approved", "safe_for_next_stage": False, "open_blockers": []}
        with pytest.raises(RuntimeViolation, match="cannot set safe_for_next_stage"):
            _validate_review_semantics(payload, source_name="review.json")

    def test_rejected_with_blockers_ok(self) -> None:
        """rejected verdict with open_blockers is fine."""
        payload = {"verdict": "rejected", "open_blockers": ["issue-1"]}
        _validate_review_semantics(payload, source_name="review.json")  # no error

    def test_approved_clean_ok(self) -> None:
        """approved with no blockers and safe=True is fine."""
        payload = {"verdict": "approved", "safe_for_next_stage": True, "open_blockers": []}
        _validate_review_semantics(payload, source_name="review.json")  # no error
