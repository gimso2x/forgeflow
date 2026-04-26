import ast
from collections.abc import Callable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_runtime_tests_do_not_define_local_json_writer_helpers() -> None:
    local_helpers = []
    for path in (ROOT / "tests" / "runtime").glob("test_*.py"):
        if path.name == "test_runtime_fixtures.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        local_helpers.extend(
            f"{path.relative_to(ROOT)}::{node.name}"
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_write_json"
        )

    assert local_helpers == []


def test_medium_plan_artifacts_fixture_writes_plan_and_ledger(
    make_task_dir: Callable[[Path], Path],
    medium_plan_artifacts: Callable[..., None],
    tmp_path: Path,
) -> None:
    task_dir = make_task_dir(tmp_path)

    medium_plan_artifacts(task_dir)

    assert (task_dir / "plan.json").exists()
    assert (task_dir / "plan-ledger.json").exists()
