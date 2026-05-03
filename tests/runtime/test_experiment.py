"""Tests for forgeflow_runtime.experiment (XLOOP)."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest

from forgeflow_runtime.experiment.circuit import CircuitBreaker, CircuitState
from forgeflow_runtime.experiment.git_ops import ExperimentGit, GitDiff
from forgeflow_runtime.experiment.loop import (
    ExperimentConfig,
    ExperimentResult,
    IterationResult,
    run_experiment,
)
from forgeflow_runtime.experiment.metric import MetricResult, execute_metric, extract_json_values
from forgeflow_runtime.experiment.simplicity import improvement_efficiency, simplicity_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_script(tmp_path: Path, name: str, content: str) -> Path:
    """Write a small executable Python script and return its path."""
    script = tmp_path / name
    script.write_text(content, encoding="utf-8")
    script.chmod(0o755)
    return script


# ---------------------------------------------------------------------------
# metric.py tests
# ---------------------------------------------------------------------------

class TestExecuteMetric:
    def test_successful_command(self, tmp_path: Path) -> None:
        script = _write_script(
            tmp_path,
            "metric_ok.py",
            'import sys, json; json.dump({"passed": 10, "failed": 2}, sys.stdout)',
        )
        result = execute_metric(["python3", str(script)])
        assert result.values["passed"] == 10.0
        assert result.values["failed"] == 2.0
        assert len(result.timestamp) > 0

    def test_failing_command_nonzero_exit(self, tmp_path: Path) -> None:
        script = _write_script(tmp_path, "metric_fail.py", "import sys; sys.exit(1)")
        with pytest.raises(subprocess.CalledProcessError):
            execute_metric(["python3", str(script)])

    def test_timeout(self, tmp_path: Path) -> None:
        script = _write_script(
            tmp_path,
            "metric_slow.py",
            "import time; time.sleep(60)",
        )
        with pytest.raises(subprocess.TimeoutExpired):
            execute_metric(["python3", str(script)], timeout=1)

    def test_cwd_parameter(self, tmp_path: Path) -> None:
        script = _write_script(
            tmp_path,
            "metric_cwd.py",
            "import os, sys, json; json.dump({'exists': 1 if os.path.exists(os.getcwd()) else 0}, sys.stdout)",
        )
        result = execute_metric(["python3", str(script)], cwd=tmp_path)
        assert result.values["exists"] == 1.0


class TestExtractJsonValues:
    def test_clean_json(self) -> None:
        output = json.dumps({"passed": 42, "failed": 1})
        values = extract_json_values(output)
        assert values == {"passed": 42.0, "failed": 1.0}

    def test_mixed_stdout(self) -> None:
        output = "Some log lines\n{\"passed\": 10, \"skipped\": 2}\nDone."
        values = extract_json_values(output)
        assert values == {"passed": 10.0, "skipped": 2.0}

    def test_multiple_json_objects(self) -> None:
        output = "{\"a\": 1}\nnoise\n{\"b\": 2, \"a\": 99}"
        values = extract_json_values(output)
        # Later object overwrites on collision
        assert values["a"] == 99.0
        assert values["b"] == 2.0

    def test_empty_output(self) -> None:
        values = extract_json_values("")
        assert values == {}

    def test_non_numeric_values_ignored(self) -> None:
        output = json.dumps({"name": "test", "score": 5.5, "ok": True})
        values = extract_json_values(output)
        assert "name" not in values
        assert values["score"] == 5.5
        assert values["ok"] == 1.0  # bool is int subclass

    def test_nested_braces(self) -> None:
        output = json.dumps({"outer": {"inner": 7}})
        values = extract_json_values(output)
        # Only top-level numeric keys extracted
        assert "outer" not in values


# ---------------------------------------------------------------------------
# circuit.py tests
# ---------------------------------------------------------------------------

class TestCircuitBreaker:
    def test_improvement_resets_count(self) -> None:
        cb = CircuitBreaker(max_stagnant=3)
        cb.record(False)
        cb.record(False)
        state = cb.record(True)
        assert state.consecutive_no_improvements == 0
        assert not state.tripped

    def test_non_improvement_increments(self) -> None:
        cb = CircuitBreaker(max_stagnant=3)
        s1 = cb.record(False)
        s2 = cb.record(False)
        assert s1.consecutive_no_improvements == 1
        assert s2.consecutive_no_improvements == 2

    def test_trips_after_max_stagnant(self) -> None:
        cb = CircuitBreaker(max_stagnant=3)
        cb.record(False)
        cb.record(False)
        state = cb.record(False)
        assert state.tripped
        assert state.consecutive_no_improvements == 3

    def test_reset_clears_state(self) -> None:
        cb = CircuitBreaker(max_stagnant=3)
        cb.record(False)
        cb.record(False)
        cb.reset()
        state = cb.record(False)
        assert state.consecutive_no_improvements == 1
        assert not state.tripped

    def test_immediate_improvement_no_trip(self) -> None:
        cb = CircuitBreaker(max_stagnant=3)
        for _ in range(5):
            state = cb.record(True)
        assert not state.tripped

    def test_tripped_property(self) -> None:
        cb = CircuitBreaker(max_stagnant=2)
        assert not cb.tripped
        cb.record(False)
        assert not cb.tripped
        cb.record(False)
        assert cb.tripped


# ---------------------------------------------------------------------------
# simplicity.py tests
# ---------------------------------------------------------------------------

class TestSimplicityScore:
    def test_focused_changes_high_score(self) -> None:
        score = simplicity_score(files_changed=1, lines_added=10, lines_removed=5)
        assert score == 1.0

    def test_scattered_changes_low_score(self) -> None:
        score = simplicity_score(files_changed=15, lines_added=200, lines_removed=0)
        assert score < 0.5

    def test_clamped_minimum(self) -> None:
        score = simplicity_score(files_changed=100, lines_added=5000, lines_removed=0)
        assert score == 0.0

    def test_clamped_maximum(self) -> None:
        score = simplicity_score(files_changed=1, lines_added=10, lines_removed=1000)
        assert score == 1.0

    def test_bloat_penalty(self) -> None:
        s1 = simplicity_score(files_changed=3, lines_added=100, lines_removed=0)
        s2 = simplicity_score(files_changed=3, lines_added=50, lines_removed=0)
        assert s1 < s2

    def test_removal_reward(self) -> None:
        s1 = simplicity_score(files_changed=5, lines_added=100, lines_removed=0)
        s2 = simplicity_score(files_changed=5, lines_added=100, lines_removed=100)
        assert s2 > s1


class TestImprovementEfficiency:
    def test_penalizes_low_simplicity(self) -> None:
        eff_low = improvement_efficiency(10.0, 0.1)
        eff_high = improvement_efficiency(10.0, 1.0)
        assert eff_low < eff_high

    def test_rewards_high_simplicity(self) -> None:
        eff = improvement_efficiency(10.0, 1.0)
        # At simplicity=1.0: 10 * (0.3 + 0.7) = 10.0
        assert eff == pytest.approx(10.0)

    def test_zero_improvement(self) -> None:
        eff = improvement_efficiency(0.0, 0.5)
        assert eff == 0.0

    def test_floor_simplicity(self) -> None:
        # At simplicity=0.0: improvement * (0.3 + 0) = improvement * 0.3
        eff = improvement_efficiency(10.0, 0.0)
        assert eff == pytest.approx(3.0)

    def test_negative_improvement(self) -> None:
        eff = improvement_efficiency(-5.0, 0.5)
        assert eff < 0


# ---------------------------------------------------------------------------
# git_ops.py tests
# ---------------------------------------------------------------------------

class TestExperimentGit:
    @pytest.fixture()
    def git_repo(self, tmp_path: Path) -> ExperimentGit:
        """Create a real git repo in a temp directory."""
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@xloop.local"],
            cwd=repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "XLOOP Test"],
            cwd=repo,
            capture_output=True,
            check=True,
        )
        # Create initial commit so branch switching works
        (repo / "README.md").write_text("# test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=repo,
            capture_output=True,
            check=True,
        )
        return ExperimentGit(repo_root=repo, branch_prefix="xloop-test")

    def test_create_and_switch_branch(self, git_repo: ExperimentGit) -> None:
        branch = git_repo.create_branch("exp-001")
        assert branch == "xloop-test/exp-001"
        current = git_repo._git("branch", "--show-current")
        assert current.stdout.strip() == branch
        # Cleanup
        git_repo.checkout_original()

    def test_commit_changes(self, git_repo: ExperimentGit) -> None:
        git_repo.create_branch("exp-002")
        (git_repo.repo_root / "new_file.txt").write_text("hello\n", encoding="utf-8")
        commit_hash = git_repo.commit_changes("add new file")
        assert len(commit_hash) >= 7
        git_repo.checkout_original()

    def test_get_diff(self, git_repo: ExperimentGit) -> None:
        git_repo.create_branch("exp-003")
        (git_repo.repo_root / "a.py").write_text("print('a')\n", encoding="utf-8")
        git_repo.commit_changes("add a.py")
        diff = git_repo.get_diff()
        assert diff.files_changed == 1
        assert diff.lines_added == 1
        git_repo.checkout_original()

    def test_reset_to_start_discards(self, git_repo: ExperimentGit) -> None:
        git_repo.create_branch("exp-004")
        (git_repo.repo_root / "discard.txt").write_text("gone\n", encoding="utf-8")
        git_repo.commit_changes("will discard")
        git_repo.reset_to_start()
        assert not (git_repo.repo_root / "discard.txt").exists()
        git_repo.checkout_original()

    def test_checkout_original_cleans_up(self, git_repo: ExperimentGit) -> None:
        git_repo.create_branch("exp-005")
        (git_repo.repo_root / "keep.txt").write_text("data\n", encoding="utf-8")
        git_repo.commit_changes("add keep.txt")
        git_repo.checkout_original()
        # Should be back on main/master
        current = git_repo._git("branch", "--show-current")
        assert current.stdout.strip() in ("main", "master")
        # Experiment branch should be deleted
        result = git_repo._git(
            "branch", "--list", "xloop-test/exp-005", check=False
        )
        assert result.stdout.strip() == ""

    def test_is_clean(self, git_repo: ExperimentGit) -> None:
        assert git_repo.is_clean()
        (git_repo.repo_root / "untracked.txt").write_text("x\n", encoding="utf-8")
        assert not git_repo.is_clean()
        # Clean up
        (git_repo.repo_root / "untracked.txt").unlink()

    def test_multiple_commits_diff_accumulates(self, git_repo: ExperimentGit) -> None:
        git_repo.create_branch("exp-006")
        (git_repo.repo_root / "f1.py").write_text("a\n", encoding="utf-8")
        git_repo.commit_changes("first")
        (git_repo.repo_root / "f2.py").write_text("b\n", encoding="utf-8")
        git_repo.commit_changes("second")
        diff = git_repo.get_diff()
        assert diff.files_changed == 2
        git_repo.checkout_original()


# ---------------------------------------------------------------------------
# loop.py tests
# ---------------------------------------------------------------------------

class TestExperimentLoop:
    @pytest.fixture()
    def git_cwd(self, tmp_path: Path) -> Path:
        """Create a real git repo in tmp_path/repo and return its path."""
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@xloop.local"],
            cwd=repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "XLOOP Test"],
            cwd=repo,
            capture_output=True,
            check=True,
        )
        (repo / "README.md").write_text("# test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=repo,
            capture_output=True,
            check=True,
        )
        return repo

    def _make_metric_script(
        self,
        tmp_path: Path,
        values_sequence: list[dict[str, Any]],
    ) -> Path:
        """Create a metric script that emits values from a sequence.

        Each call prints the next dict in the sequence as JSON, then the
        last value repeats forever.
        """
        import json as _json

        encoded = _json.dumps(values_sequence)
        script = _write_script(
            tmp_path,
            "mock_metric.py",
            f"""
import json, os, sys

seq = json.loads({encoded!r})
counter_file = os.path.join(os.path.dirname(__file__), ".metric_counter")
try:
    with open(counter_file) as f:
        idx = int(f.read().strip())
except (FileNotFoundError, ValueError):
    idx = 0

if idx >= len(seq):
    idx = len(seq) - 1

val = seq[idx]
with open(counter_file, "w") as f:
    f.write(str(idx + 1))

json.dump(val, sys.stdout)
""",
        )
        # Remove counter file if it exists
        counter = tmp_path / ".metric_counter"
        if counter.exists():
            counter.unlink()
        return script

    def test_immediately_improves(self, tmp_path: Path, git_cwd: Path) -> None:
        """Metric goes from 5 -> 10 -> 15 -> 20 -> 25 (direction=higher). All kept."""
        script = self._make_metric_script(
            tmp_path,
            [
                {"passed": 5},
                {"passed": 10},
                {"passed": 15},
                {"passed": 20},
                {"passed": 25},
                {"passed": 30},
                {"passed": 35},
            ],
        )
        config = ExperimentConfig(
            metric_command=["python3", str(script)],
            metric_key="passed",
            direction="higher",
            max_iterations=5,
            circuit_breaker_limit=3,
            cwd=git_cwd,
        )
        result = run_experiment(config)
        assert result.total_iterations == 5
        assert not result.circuit_tripped
        assert result.baseline.values["passed"] == 5.0
        # All 5 iterations should be kept (each improves)
        kept = [i for i in result.iterations if i.kept]
        assert len(kept) == 5

    def test_never_improves_trips_circuit(self, tmp_path: Path, git_cwd: Path) -> None:
        """Metric always returns same value. Circuit breaker should trip."""
        script = self._make_metric_script(
            tmp_path,
            [{"passed": 5}],
        )
        config = ExperimentConfig(
            metric_command=["python3", str(script)],
            metric_key="passed",
            direction="higher",
            max_iterations=20,
            circuit_breaker_limit=3,
            cwd=git_cwd,
        )
        result = run_experiment(config)
        assert result.circuit_tripped
        assert result.total_iterations == 3  # baseline + 3 stagnant

    def test_mixed_improvements(self, tmp_path: Path, git_cwd: Path) -> None:
        """Metric: 5 -> 10 -> 8 -> 12 -> 7 -> 14. Improvements interspersed."""
        script = self._make_metric_script(
            tmp_path,
            [
                {"passed": 5},
                {"passed": 10},
                {"passed": 8},
                {"passed": 12},
                {"passed": 7},
                {"passed": 14},
                {"passed": 14},
            ],
        )
        config = ExperimentConfig(
            metric_command=["python3", str(script)],
            metric_key="passed",
            direction="higher",
            max_iterations=7,
            circuit_breaker_limit=5,
            cwd=git_cwd,
        )
        result = run_experiment(config)
        assert result.total_iterations == 7
        assert not result.circuit_tripped
        # Iterations 1 (5->10), 3 (10->12), 5 (12->14) should be kept
        kept = [i for i in result.iterations if i.kept]
        assert len(kept) == 3

    def test_top_improvements_sorted_by_efficiency(self, tmp_path: Path, git_cwd: Path) -> None:
        script = self._make_metric_script(
            tmp_path,
            [
                {"passed": 0},
                {"passed": 5},
                {"passed": 3},
                {"passed": 10},
                {"passed": 8},
                {"passed": 15},
                {"passed": 15},
            ],
        )
        config = ExperimentConfig(
            metric_command=["python3", str(script)],
            metric_key="passed",
            direction="higher",
            max_iterations=7,
            circuit_breaker_limit=10,
            cwd=git_cwd,
        )
        result = run_experiment(config)
        top = result.top_improvements
        assert len(top) <= 5
        # Verify sorted descending by efficiency
        for i in range(len(top) - 1):
            assert top[i].efficiency >= top[i + 1].efficiency

    def test_on_iteration_callback(self, tmp_path: Path, git_cwd: Path) -> None:
        script = self._make_metric_script(
            tmp_path,
            [{"passed": 5}, {"passed": 10}, {"passed": 10}],
        )
        collected: list[IterationResult] = []

        def callback(ir: IterationResult) -> None:
            collected.append(ir)

        config = ExperimentConfig(
            metric_command=["python3", str(script)],
            metric_key="passed",
            direction="higher",
            max_iterations=3,
            circuit_breaker_limit=5,
            cwd=git_cwd,
        )
        run_experiment(config, on_iteration=callback)
        assert len(collected) == 3
        assert collected[0].iteration == 1
        assert collected[2].iteration == 3

    def test_direction_lower(self, tmp_path: Path, git_cwd: Path) -> None:
        """When direction=lower, decreasing values are improvements."""
        script = self._make_metric_script(
            tmp_path,
            [
                {"errors": 100},
                {"errors": 50},
                {"errors": 25},
                {"errors": 25},
            ],
        )
        config = ExperimentConfig(
            metric_command=["python3", str(script)],
            metric_key="errors",
            direction="lower",
            max_iterations=4,
            circuit_breaker_limit=5,
            cwd=git_cwd,
        )
        result = run_experiment(config)
        kept = [i for i in result.iterations if i.kept]
        assert len(kept) == 2  # 100->50, 50->25


class TestExperimentConfig:
    def test_frozen_immutability(self) -> None:
        config = ExperimentConfig(
            metric_command=["echo", "hello"],
            metric_key="foo",
            direction="higher",
        )
        with pytest.raises(AttributeError):
            config.metric_command = ["changed"]  # type: ignore[misc]

    def test_defaults(self) -> None:
        config = ExperimentConfig(
            metric_command=["echo", "{}"],
            metric_key="val",
            direction="higher",
        )
        assert config.max_iterations == 10
        assert config.circuit_breaker_limit == 3
        assert config.branch_prefix == "xloop"
        assert config.min_improvement == 0.0
        assert config.cwd is None
