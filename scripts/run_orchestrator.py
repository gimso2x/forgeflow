#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forgeflow_runtime.orchestrator import (  # noqa: E402
    RuntimeViolation,
    advance_to_next_stage,
    escalate_route,
    init_task,
    load_runtime_policy,
    resume_task,
    retry_stage,
    run_route,
    start_task,
    status_summary,
    step_back,
)
from forgeflow_runtime.engine import execute_stage  # noqa: E402
from forgeflow_runtime.executor import ExecutorError  # noqa: E402
from forgeflow_runtime.generator import GenerationError  # noqa: E402


def _execution_payload(*, stage: str, role: str, adapter: str, result, use_real: bool = False) -> dict:
    payload = {
        "stage": stage,
        "role": role,
        "adapter": adapter,
        "execution_mode": "real" if use_real else "stub",
        "status": result.status,
        "artifacts_produced": result.artifacts_produced,
        "token_usage": result.token_usage,
    }
    if result.error:
        payload["error"] = result.error
    return payload


def _print_payload(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


STAGE_ROLE_MAP: dict[str, str] = {
    "clarify": "coordinator",
    "plan": "planner",
    "execute": "worker",
    "spec-review": "spec-reviewer",
    "quality-review": "quality-reviewer",
    "finalize": "coordinator",
    "long-run": "worker",
}

ROUTE_ORDER: list[str] = ["small", "medium", "large_high_risk"]
RISK_TO_ROUTE: dict[str, str] = {
    "low": "small",
    "medium": "medium",
    "high": "large_high_risk",
}


def _role_for_stage(stage: str) -> str:
    role = STAGE_ROLE_MAP.get(stage)
    if not role:
        raise RuntimeViolation(f"no default role mapping for stage: {stage}")
    return role


def _route_rank(route_name: str) -> int:
    if route_name not in ROUTE_ORDER:
        raise RuntimeViolation(f"unknown route: {route_name}")
    return ROUTE_ORDER.index(route_name)


def _auto_route_for_task_dir(task_dir: Path) -> str:
    for artifact_name in ["session-state.json", "checkpoint.json", "plan-ledger.json"]:
        path = task_dir / artifact_name
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        route_name = payload.get("route")
        if isinstance(route_name, str) and route_name:
            return route_name

    brief_path = task_dir / "brief.json"
    if brief_path.exists():
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
        risk_level = brief.get("risk_level")
        if isinstance(risk_level, str) and risk_level in RISK_TO_ROUTE:
            return RISK_TO_ROUTE[risk_level]

    return "small"


def _effective_route(*, task_dir: Path, explicit_route: str | None, min_route: str | None) -> str:
    route_name = explicit_route or _auto_route_for_task_dir(task_dir)
    if min_route is None:
        return route_name
    return ROUTE_ORDER[max(_route_rank(route_name), _route_rank(min_route))]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "ForgeFlow stage-machine orchestrator. Preferred entry is clarify-first; direct start/run is a fallback "
            "operator path that can auto-detect a route when no state exists."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Operator shell examples:
  # Safe sample: copies the fixture to a disposable workspace before running.
  python3 scripts/run_runtime_sample.py --fixture-dir examples/runtime-fixtures/small-doc-task --route small

  # Bootstrap a real task from explicit operator inputs. Without --task-dir, writes under the current project.
  python3 scripts/run_orchestrator.py init --task-id my-task-001 --objective "Update README quickstart" --risk low
  python3 scripts/run_orchestrator.py init --task-dir work/my-task --task-id my-task-001 --objective "Update README quickstart" --risk low

  # Fallback entries mutate task artifacts, so keep them explicit operator commands.
  # Route omitted: persisted state or brief/checkpoint artifacts decide.
  python3 scripts/run_orchestrator.py start --task-dir examples/runtime-fixtures/small-doc-task
  python3 scripts/run_orchestrator.py run --task-dir examples/runtime-fixtures/small-doc-task
  # Raise the minimum route floor without lowering persisted or explicit route choice.
  python3 scripts/run_orchestrator.py run --task-dir examples/runtime-fixtures/small-doc-task --min-route medium

  # Manual stage control: inspect status, then execute current stage, advance, retry, rewind, or escalate.
  # Read-only status path is repo-managed for first-clone shells.
  make setup
  make check-env
  make orchestrator-status
  # Mutating manual stage commands stay explicit operator commands.
  python3 scripts/run_orchestrator.py execute --task-dir examples/runtime-fixtures/small-doc-task --route small --adapter codex
  python3 scripts/run_orchestrator.py advance --task-dir examples/runtime-fixtures/small-doc-task --route small --current-stage clarify --execute --adapter cursor
  python3 scripts/run_orchestrator.py retry --task-dir examples/runtime-fixtures/small-doc-task --stage execute --max-retries 2
  python3 scripts/run_orchestrator.py step-back --task-dir examples/runtime-fixtures/small-doc-task --route small --current-stage quality-review
  python3 scripts/run_orchestrator.py escalate --task-dir examples/runtime-fixtures/small-doc-task --from-route small

Notes:
  - clarify-first is canonical; direct start/run is only an operator fallback surface.
  - --route is an explicit override. Without it, the CLI reuses persisted state or auto-detects from artifacts.
  - --min-route can raise the route floor but must not lower an explicit or persisted route.
  - Manual commands mutate the target task-dir. Use run_runtime_sample.py for disposable fixture runs.
""",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    route_help = "explicit route override; omit to reuse persisted route or auto-detect from brief/checkpoint state"
    min_route_help = "minimum allowed route when auto-detecting or reusing state; never lowers an explicit or persisted route"

    start_parser = subparsers.add_parser(
        "start",
        help="initialize task artifacts; fallback path when operator starts outside clarify",
    )
    start_parser.add_argument("--task-dir", required=True)
    start_parser.add_argument("--route", help=route_help)
    start_parser.add_argument("--min-route", choices=ROUTE_ORDER, help=min_route_help)

    init_parser = subparsers.add_parser(
        "init",
        help="bootstrap a new task from explicit operator inputs without overwriting existing artifacts",
    )
    init_parser.add_argument("--task-dir", help="task artifact directory; defaults to ./.forgeflow/tasks/<task-id>")
    init_parser.add_argument("--task-id", required=True)
    init_parser.add_argument("--objective", required=True)
    init_parser.add_argument("--risk", choices=["low", "medium", "high"], required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="run a route end-to-end; fallback path can auto-route when no prior state exists",
    )
    run_parser.add_argument("--task-dir", required=True)
    run_parser.add_argument("--route", help=route_help)
    run_parser.add_argument("--min-route", choices=ROUTE_ORDER, help=min_route_help)

    resume_parser = subparsers.add_parser("resume", help="reload task state from session-state and checkpoint artifacts")
    resume_parser.add_argument("--task-dir", required=True)
    resume_parser.add_argument("--route", help=route_help)
    resume_parser.add_argument("--min-route", choices=ROUTE_ORDER, help=min_route_help)

    status_parser = subparsers.add_parser("status", help="show current task status from canonical artifacts")
    status_parser.add_argument("--task-dir", required=True)
    status_parser.add_argument("--route", help=route_help)
    status_parser.add_argument("--min-route", choices=ROUTE_ORDER, help=min_route_help)

    advance_parser = subparsers.add_parser("advance", help="advance one stage forward")
    advance_parser.add_argument("--task-dir", required=True)
    advance_parser.add_argument("--route", help=route_help)
    advance_parser.add_argument("--min-route", choices=ROUTE_ORDER, help=min_route_help)
    advance_parser.add_argument("--current-stage", required=True)
    advance_parser.add_argument("--execute", action="store_true", help="execute the next stage immediately after advancing")
    advance_parser.add_argument("--adapter", choices=["claude", "codex", "cursor"], default="claude")
    advance_parser.add_argument("--role", default=None, help="override role when --execute is used")
    advance_parser.add_argument("--artifacts", nargs="+", default=None, help="artifact names to stream when --execute is used")
    advance_parser.add_argument("--real", action="store_true", help="use real CLI adapters when --execute is used")

    retry_parser = subparsers.add_parser("retry", help="retry the current stage within budget")
    retry_parser.add_argument("--task-dir", required=True)
    retry_parser.add_argument("--stage", required=True)
    retry_parser.add_argument("--max-retries", type=int, default=2)

    step_back_parser = subparsers.add_parser("step-back", help="rewind to the previous stage")
    step_back_parser.add_argument("--task-dir", required=True)
    step_back_parser.add_argument("--route", help=route_help)
    step_back_parser.add_argument("--min-route", choices=ROUTE_ORDER, help=min_route_help)
    step_back_parser.add_argument("--current-stage", required=True)

    escalate_parser = subparsers.add_parser("escalate", help="escalate a route to large_high_risk")
    escalate_parser.add_argument("--task-dir", required=True)
    escalate_parser.add_argument("--from-route", required=True)

    exec_parser = subparsers.add_parser("execute", help="execute the current stage via an LLM adapter")
    exec_parser.add_argument("--task-dir", required=True)
    exec_parser.add_argument("--route", help=route_help)
    exec_parser.add_argument("--min-route", choices=ROUTE_ORDER, help=min_route_help)
    exec_parser.add_argument("--adapter", choices=["claude", "codex", "cursor"], default="claude")
    exec_parser.add_argument("--role", default=None, help="override role (auto-detected from stage if omitted)")
    exec_parser.add_argument("--artifacts", nargs="+", default=None, help="artifact names to stream")
    exec_parser.add_argument("--real", action="store_true", help="use real CLI adapters instead of stubs")

    return parser


def _default_task_dir_for_init(task_id: str) -> Path:
    return (Path.cwd() / ".forgeflow" / "tasks" / task_id).resolve()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    task_dir_arg = getattr(args, "task_dir", None)
    if task_dir_arg:
        task_dir = Path(task_dir_arg).resolve()
    elif args.command == "init":
        task_dir = _default_task_dir_for_init(args.task_id)
    else:
        parser.error("--task-dir is required for this command")
    policy = load_runtime_policy(ROOT)

    try:
        route_name = _effective_route(
            task_dir=task_dir,
            explicit_route=getattr(args, "route", None),
            min_route=getattr(args, "min_route", None),
        )
        if args.command == "start":
            _print_payload(start_task(task_dir=task_dir, policy=policy, route_name=route_name))
        elif args.command == "init":
            _print_payload(
                init_task(
                    task_dir=task_dir,
                    policy=policy,
                    task_id=args.task_id,
                    objective=args.objective,
                    risk_level=args.risk,
                )
            )
        elif args.command == "run":
            _print_payload(run_route(task_dir=task_dir, policy=policy, route_name=route_name))
        elif args.command == "resume":
            _print_payload(resume_task(task_dir=task_dir, policy=policy, route_name=route_name))
        elif args.command == "status":
            _print_payload(status_summary(task_dir=task_dir, policy=policy, route_name=route_name))
        elif args.command == "advance":
            transition = advance_to_next_stage(
                task_dir=task_dir,
                policy=policy,
                route_name=route_name,
                current_stage=args.current_stage,
                execute_immediately=args.execute,
                adapter_target=args.adapter,
                role=args.role,
                artifacts_to_stream=args.artifacts,
                use_real=args.real,
            )
            payload = {"next_stage": transition.next_stage}
            if transition.execution is not None:
                payload["execution"] = transition.execution
            _print_payload(payload)
        elif args.command == "retry":
            _print_payload(retry_stage(task_dir=task_dir, stage_name=args.stage, max_retries=args.max_retries))
        elif args.command == "step-back":
            _print_payload(
                step_back(task_dir=task_dir, policy=policy, route_name=route_name, current_stage=args.current_stage)
            )
        elif args.command == "escalate":
            _print_payload(escalate_route(task_dir=task_dir, from_route=args.from_route))
        elif args.command == "execute":
            run_state_path = task_dir / "run-state.json"
            if not run_state_path.exists():
                print("ERROR: run-state.json not found; start or resume the task first.", file=sys.stderr)
                return 1
            run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
            current_stage = run_state.get("current_stage")
            if not current_stage:
                print("ERROR: current_stage not set in run-state.", file=sys.stderr)
                return 1
            role = args.role or _role_for_stage(current_stage)
            result = execute_stage(
                task_dir=task_dir,
                task_id=run_state.get("task_id", "unknown"),
                stage=current_stage,
                route=route_name,
                role=role,
                adapter_target=args.adapter,
                artifacts_to_stream=args.artifacts,
                use_real=args.real,
            )
            if result.status == "success" and result.raw_output:
                (task_dir / f"{current_stage}-output.md").write_text(result.raw_output, encoding="utf-8")
            _print_payload(
                _execution_payload(
                    stage=current_stage,
                    role=role,
                    adapter=args.adapter,
                    result=result,
                    use_real=args.real,
                )
            )
        else:
            parser.error(f"unknown command: {args.command}")
    except RuntimeViolation as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except (GenerationError, ExecutorError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
