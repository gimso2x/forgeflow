"""Tests for forgeflow_runtime.constraint_checker and gate_evaluation integration."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from forgeflow_runtime.constraint_checker import (
    DEFAULT_CONSTRAINTS,
    Constraint,
    ScanResult,
    Violation,
    check_directory,
    check_with_registry,
    load_constraint_registry,
    max_file_lines_check,
)
from forgeflow_runtime.gate_evaluation import check_quality_constraints
from forgeflow_runtime.policy_loader import RuntimePolicy


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def _make_sample_dir(tmp_path: Path) -> Path:
    """Create a sample project structure with violations."""
    src = tmp_path / "src"
    _write_file(
        src / "good.py",
        """\
        import logging

        logger = logging.getLogger(__name__)

        def add(a: int, b: int) -> int:
            return a + b
        """,
    )
    _write_file(
        src / "bad.py",
        """\
        # TODO fix this later
        password = "supersecretvalue123"
        print("debugging here")
        try:
            x = 1 / 0
        except:
            pass
        """,
    )
    # oversized file — 350 lines
    lines = [f"line_{i} = {i}" for i in range(350)]
    _write_file(src / "oversized.py", "\n".join(lines))
    # file in a skip dir
    _write_file(
        src / "skipme" / "hidden.py",
        """\
        TODO: this should be skipped
        print("also skipped")
        """,
    )
    return tmp_path


def _make_registry_file(tmp_path: Path) -> Path:
    p = tmp_path / "registry.yaml"
    p.write_text(
        textwrap.dedent("""\
        constraints:
          - id: no-hack
            pattern: "hack"
            reason: "No hacks allowed"
            suggestion: "Use proper implementation"
            category: "style"
            severity: "error"
        """),
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# Built-in constraint detection
# ---------------------------------------------------------------------------

class TestBuiltinConstraints:
    def test_no_todo_detects_TODO(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "# TODO refactor this\n")
        result = check_directory(tmp_path)
        ids = [v.constraint_id for v in result.violations]
        assert "no-todo" in ids

    def test_no_fixme_detects_FIXME(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "# FIXME broken\n")
        result = check_directory(tmp_path)
        ids = [v.constraint_id for v in result.violations]
        assert "no-fixme" in ids

    def test_no_hardcoded_secret_detects_password(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", 'password = "longsecretvalue123"\n')
        result = check_directory(tmp_path)
        ids = [v.constraint_id for v in result.violations]
        assert "no-hardcoded-secret" in ids

    def test_no_print_debug_detects_print(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "print('hello')\n")
        result = check_directory(tmp_path)
        ids = [v.constraint_id for v in result.violations]
        assert "no-print-debug" in ids

    def test_no_empty_except_detects_bare_except(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "try:\n    x = 1\nexcept:\n    pass\n")
        result = check_directory(tmp_path)
        ids = [v.constraint_id for v in result.violations]
        assert "no-empty-except" in ids

    def test_clean_file_produces_no_violations(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "clean.py", "x = 42\n")
        result = check_directory(tmp_path)
        assert len(result.violations) == 0


# ---------------------------------------------------------------------------
# check_directory
# ---------------------------------------------------------------------------

class TestCheckDirectory:
    def test_scans_and_finds_violations(self, tmp_path: Path) -> None:
        d = _make_sample_dir(tmp_path)
        result = check_directory(d)
        assert result.files_scanned >= 2
        assert len(result.violations) > 0

    def test_skips_hidden_dirs(self, tmp_path: Path) -> None:
        d = _make_sample_dir(tmp_path)
        result = check_directory(d)
        # skipme is not hidden but let's also test .hidden
        _write_file(tmp_path / ".hidden" / "secret.py", "# TODO should be skipped\n")
        result2 = check_directory(d)
        hidden_files = [v for v in result2.violations if ".hidden" in v.file]
        assert len(hidden_files) == 0

    def test_skips_pycache(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "__pycache__" / "mod.py",
            "# TODO inside pycache\n",
        )
        result = check_directory(tmp_path)
        assert all("__pycache__" not in v.file for v in result.violations)

    def test_skips_node_modules(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "node_modules" / "pkg" / "index.js",
            "TODO inside node_modules\n",
        )
        result = check_directory(tmp_path)
        assert all("node_modules" not in v.file for v in result.violations)

    def test_extension_filtering(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "print('py')\n")
        _write_file(tmp_path / "a.js", "print('js')\n")
        result = check_directory(tmp_path, extensions=[".py"])
        assert result.files_scanned == 1

    def test_category_filtering(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "# TODO stuff\npassword = 'longsecretvalue'\n")
        result = check_directory(tmp_path, categories=["security"])
        ids = [v.constraint_id for v in result.violations]
        assert "no-hardcoded-secret" in ids
        assert "no-todo" not in ids

    def test_severity_filtering(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "# TODO stuff\npassword = 'longsecretvalue'\n")
        result = check_directory(tmp_path, severities=["error"])
        ids = [v.constraint_id for v in result.violations]
        assert "no-hardcoded-secret" in ids
        assert "no-todo" not in ids

    def test_empty_directory_no_violations(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        result = check_directory(empty)
        assert len(result.violations) == 0
        assert result.files_scanned == 0

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        result = check_directory(tmp_path / "nope")
        assert len(result.violations) == 0
        assert result.files_scanned == 0

    def test_duration_seconds_populated(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "x = 1\n")
        result = check_directory(tmp_path)
        assert result.duration_seconds >= 0


# ---------------------------------------------------------------------------
# max_file_lines_check
# ---------------------------------------------------------------------------

class TestMaxFileLinesCheck:
    def test_detects_oversized_file(self, tmp_path: Path) -> None:
        d = _make_sample_dir(tmp_path)
        violations = max_file_lines_check(d, max_lines=300)
        oversized = [v for v in violations if "oversized.py" in v.file]
        assert len(oversized) == 1
        assert oversized[0].line > 300

    def test_returns_empty_for_small_files(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "small.py", "x = 1\n")
        violations = max_file_lines_check(tmp_path, max_lines=300)
        assert len(violations) == 0

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        violations = max_file_lines_check(tmp_path / "nope", 100)
        assert violations == []


# ---------------------------------------------------------------------------
# load_constraint_registry
# ---------------------------------------------------------------------------

class TestLoadConstraintRegistry:
    def test_loads_valid_yaml(self, tmp_path: Path) -> None:
        reg = _make_registry_file(tmp_path)
        constraints = load_constraint_registry(reg)
        assert len(constraints) == 1
        assert constraints[0].id == "no-hack"
        assert constraints[0].category == "style"
        assert constraints[0].severity == "error"

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        constraints = load_constraint_registry(tmp_path / "nonexistent.yaml")
        assert constraints == []

    def test_malformed_yaml_returns_empty(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("{: invalid yaml ::}", encoding="utf-8")
        constraints = load_constraint_registry(bad)
        assert constraints == []

    def test_missing_required_fields_skipped(self, tmp_path: Path) -> None:
        p = tmp_path / "partial.yaml"
        p.write_text(
            "constraints:\n  - id: x\n  - pattern: y\n",
            encoding="utf-8",
        )
        constraints = load_constraint_registry(p)
        assert constraints == []

    def test_defaults_applied(self, tmp_path: Path) -> None:
        p = tmp_path / "minimal.yaml"
        p.write_text(
            "constraints:\n  - id: my-id\n    pattern: 'bad'\n",
            encoding="utf-8",
        )
        constraints = load_constraint_registry(p)
        assert len(constraints) == 1
        assert constraints[0].category == "custom"
        assert constraints[0].severity == "warning"


# ---------------------------------------------------------------------------
# check_with_registry
# ---------------------------------------------------------------------------

class TestCheckWithRegistry:
    def test_combines_default_and_custom(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "# TODO stuff\nhack = True\n")
        reg = _make_registry_file(tmp_path)
        result = check_with_registry(tmp_path, registry_path=reg)
        ids = [v.constraint_id for v in result.violations]
        assert "no-todo" in ids  # default
        assert "no-hack" in ids  # custom

    def test_use_defaults_false_only_uses_registry(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "# TODO stuff\nhack = True\n")
        reg = _make_registry_file(tmp_path)
        result = check_with_registry(tmp_path, registry_path=reg, use_defaults=False)
        ids = [v.constraint_id for v in result.violations]
        assert "no-todo" not in ids
        assert "no-hack" in ids

    def test_no_registry_path_uses_defaults(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "# TODO stuff\n")
        result = check_with_registry(tmp_path, registry_path=None)
        ids = [v.constraint_id for v in result.violations]
        assert "no-todo" in ids


# ---------------------------------------------------------------------------
# Integration: RuntimePolicy + check_quality_constraints
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_policy_without_constraints_returns_empty(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "# TODO stuff\n")
        policy = RuntimePolicy(
            workflow_stages=[],
            stage_requirements={},
            stage_gate_map={},
            gate_requirements={},
            gate_reviews={},
            routes={},
            finalize_flags=[],
            review_order=[],
        )
        violations = check_quality_constraints(
            tmp_path, policy, canonical_task_id="task-001",
        )
        assert violations == []

    def test_policy_constraints_disabled_returns_empty(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "# TODO stuff\n")
        policy = RuntimePolicy(
            workflow_stages=[],
            stage_requirements={},
            stage_gate_map={},
            gate_requirements={},
            gate_reviews={},
            routes={},
            finalize_flags=[],
            review_order=[],
            constraints={"enabled": False},
        )
        violations = check_quality_constraints(
            tmp_path, policy, canonical_task_id="task-001",
        )
        assert violations == []

    def test_policy_constraints_enabled_finds_violations(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "# TODO stuff\n")
        policy = RuntimePolicy(
            workflow_stages=[],
            stage_requirements={},
            stage_gate_map={},
            gate_requirements={},
            gate_reviews={},
            routes={},
            finalize_flags=[],
            review_order=[],
            constraints={"enabled": True},
        )
        violations = check_quality_constraints(
            tmp_path, policy, canonical_task_id="task-001",
        )
        ids = [v.constraint_id for v in violations]
        assert "no-todo" in ids

    def test_policy_with_max_file_lines(self, tmp_path: Path) -> None:
        d = _make_sample_dir(tmp_path)
        policy = RuntimePolicy(
            workflow_stages=[],
            stage_requirements={},
            stage_gate_map={},
            gate_requirements={},
            gate_reviews={},
            routes={},
            finalize_flags=[],
            review_order=[],
            constraints={"enabled": True, "max_file_lines": 300},
        )
        violations = check_quality_constraints(
            d, policy, canonical_task_id="task-001",
        )
        oversized = [v for v in violations if v.constraint_id == "max-file-lines"]
        assert len(oversized) >= 1


# ---------------------------------------------------------------------------
# ScanResult dataclass
# ---------------------------------------------------------------------------

class TestScanResult:
    def test_fields(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "# TODO fix\n")
        result = check_directory(tmp_path)
        assert isinstance(result, ScanResult)
        assert isinstance(result.violations, tuple)
        assert isinstance(result.files_scanned, int)
        assert isinstance(result.files_skipped, int)
        assert isinstance(result.duration_seconds, float)

    def test_violations_are_frozen(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "# TODO fix\n")
        result = check_directory(tmp_path)
        v = result.violations[0]
        assert isinstance(v, Violation)
        # frozen dataclass — attribute assignment should raise
        with pytest.raises(AttributeError):
            v.line = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DEFAULT_CONSTRAINTS sanity
# ---------------------------------------------------------------------------

class TestDefaultConstraints:
    def test_all_have_required_fields(self) -> None:
        for c in DEFAULT_CONSTRAINTS:
            assert c.id
            assert c.pattern
            assert c.reason
            assert c.suggestion
            assert c.category
            assert c.severity in ("error", "warning")

    def test_no_duplicate_ids(self) -> None:
        ids = [c.id for c in DEFAULT_CONSTRAINTS]
        assert len(ids) == len(set(ids))

    def test_patterns_compile(self) -> None:
        import re
        for c in DEFAULT_CONSTRAINTS:
            re.compile(c.pattern)
