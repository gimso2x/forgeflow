from pathlib import Path

from forgeflow_runtime.orchestrator import load_runtime_policy


ROOT = Path(__file__).resolve().parents[2]


def test_load_runtime_policy_and_resolve_small_route() -> None:
    policy = load_runtime_policy(ROOT)

    assert policy.workflow_stages == [
        "clarify",
        "plan",
        "execute",
        "spec-review",
        "quality-review",
        "finalize",
        "long-run",
    ]
    assert policy.routes["small"]["stages"] == [
        "clarify",
        "execute",
        "quality-review",
        "finalize",
    ]
