from collections.abc import Callable
from pathlib import Path


def test_medium_plan_artifacts_fixture_writes_plan_and_ledger(
    make_task_dir: Callable[[Path], Path],
    medium_plan_artifacts: Callable[..., None],
    tmp_path: Path,
) -> None:
    task_dir = make_task_dir(tmp_path)

    medium_plan_artifacts(task_dir)

    assert (task_dir / "plan.json").exists()
    assert (task_dir / "plan-ledger.json").exists()
