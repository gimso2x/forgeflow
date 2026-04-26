from pathlib import Path
from typing import Callable


def test_make_task_dir_fixture_writes_basic_runtime_artifacts(make_task_dir: Callable[[Path], Path], tmp_path: Path) -> None:
    task_dir = make_task_dir(tmp_path)

    assert (task_dir / "brief.json").exists()
    assert (task_dir / "run-state.json").exists()
