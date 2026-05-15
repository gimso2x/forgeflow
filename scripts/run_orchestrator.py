#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forgeflow_runtime.orchestrator import (  # noqa: E402
    RuntimeViolation,
    _stub_execution_warning,
    advance_to_next_stage,
    clarify_task,
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
from forgeflow_runtime.operator_routing import ROUTE_ORDER, effective_route, role_for_stage  # noqa: E402
from forgeflow_runtime.engine import execute_stage  # noqa: E402
from forgeflow_runtime.executor import ExecutorError, SUPPORTED_REAL_ADAPTERS  # noqa: E402
from forgeflow_runtime.generator import GenerationError  # noqa: E402
from forgeflow_runtime.workflow_override import resolve_project_workflow  # noqa: E402


def _execution_payload(*, stage: str, role: str, adapter: str, result, use_real: bool = False) -> dict:
    execution_mode = "real" if use_real else "stub"
    payload = {
        "stage": stage,
        "role": role,
        "adapter": adapter,
        "execution_mode": execution_mode,
        "status": result.status,
        "artifacts_produced": result.artifacts_produced,
        "token_usage": result.token_usage,
    }
    if execution_mode == "stub":
        payload["dry_run"] = True
        payload["warning"] = _stub_execution_warning()
    else:
        payload["dry_run"] = False
    if result.error:
        payload["error"] = result.error
    return payload


def _assert_real_requested(*, use_real: bool, assert_real: bool) -> None:
    if assert_real and not use_real:
        raise RuntimeViolation("--assert-real requires --real; refusing to report stub execution as a real run")


def _print_stub_warning_if_needed(*, use_real: bool) -> None:
    if not use_real:
        banner = "\n================== [STUB MODE] ==================\n"
        banner += "No real CLI adapter ran. Output is simulated.\n"
        banner += "Pass --real for live execution or --assert-real to fail fast.\n"
        banner += "=================================================\n"
        print(banner, file=sys.stderr)


def _print_payload(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "ForgeFlow stage-machine orchestrator. Preferred entry is clarify-first; direct start/execute is a fallback "
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
  python3 scripts/run_orchestrator.py execute --task-dir examples/runtime-fixtures/small-doc-task
  # Raise the minimum route floor without lowering persisted or explicit route choice.
  python3 scripts/run_orchestrator.py execute --task-dir examples/runtime-fixtures/small-doc-task --min-route medium

  # Manual stage control: inspect status, then execute current stage, advance, retry, rewind, or escalate.
  # Read-only status path is repo-managed for first-clone shells.
  make setup
  make check-env
  make orchestrator-status
  # Mutating manual stage commands stay explicit operator commands.
  python3 scripts/run_orchestrator.py exec-stage --task-dir examples/runtime-fixtures/small-doc-task --route small --adapter codex
  python3 scripts/run_orchestrator.py advance --task-dir examples/runtime-fixtures/small-doc-task --route small --current-stage clarify --execute --adapter codex
  python3 scripts/run_orchestrator.py retry --task-dir examples/runtime-fixtures/small-doc-task --stage execute --max-retries 2
  python3 scripts/run_orchestrator.py step-back --task-dir examples/runtime-fixtures/small-doc-task --route small --current-stage quality-review
  python3 scripts/run_orchestrator.py escalate --task-dir examples/runtime-fixtures/small-doc-task --from-route small

Notes:
  - clarify-first is canonical; direct start/execute is only an operator fallback surface.
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
    init_parser.add_argument("--task-id", help="task identifier; auto-inferred from objective if omitted")
    init_parser.add_argument("--objective", help="one-sentence task goal; auto-inferred from project context if omitted")
    init_parser.add_argument("--risk", choices=["low", "medium", "high"], help="risk level; auto-inferred if omitted")

    clarify_parser = subparsers.add_parser(
        "clarify",
        help="analyze objective, detect project context, generate PRD/ARCH/QA drafts and deploy agents",
    )
    clarify_parser.add_argument("--task-dir", required=True)
    clarify_parser.add_argument("--route", help=route_help)

    execute_parser = subparsers.add_parser(
        "execute",
        help="run a route end-to-end; fallback path can auto-route when no prior state exists",
    )
    execute_parser.add_argument("--task-dir", required=True)
    execute_parser.add_argument("--route", help=route_help)
    execute_parser.add_argument("--min-route", choices=ROUTE_ORDER, help=min_route_help)

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
    advance_parser.add_argument("--adapter", choices=SUPPORTED_REAL_ADAPTERS, default="claude")
    advance_parser.add_argument("--role", default=None, help="override role when --execute is used")
    advance_parser.add_argument("--artifacts", nargs="+", default=None, help="artifact names to stream when --execute is used")
    advance_parser.add_argument("--real", action="store_true", help="use real CLI adapters when --execute is used")
    advance_parser.add_argument(
        "--assert-real",
        action="store_true",
        help="fail fast unless --real is also set when --execute is used",
    )

    retry_parser = subparsers.add_parser("retry", help="retry the current stage within budget")
    retry_parser.add_argument("--task-dir", required=True)
    retry_parser.add_argument("--stage", required=True)
    retry_parser.add_argument("--max-retries", type=int, default=2)

    step_back_parser = subparsers.add_parser("step-back", help="rewind to the previous stage")
    step_back_parser.add_argument("--task-dir", required=True)
    step_back_parser.add_argument("--route", help=route_help)
    step_back_parser.add_argument("--min-route", choices=ROUTE_ORDER, help=min_route_help)
    step_back_parser.add_argument("--current-stage", required=True)

    escalate_parser = subparsers.add_parser("escalate", help="escalate a route to high")
    escalate_parser.add_argument("--task-dir", required=True)
    escalate_parser.add_argument("--from-route", required=True)

    exec_stage_parser = subparsers.add_parser("exec-stage", help="execute the current stage via an LLM adapter")
    exec_stage_parser.add_argument("--task-dir", required=True)
    exec_stage_parser.add_argument("--route", help=route_help)
    exec_stage_parser.add_argument("--min-route", choices=ROUTE_ORDER, help=min_route_help)
    exec_stage_parser.add_argument("--adapter", choices=SUPPORTED_REAL_ADAPTERS, default="claude")
    exec_stage_parser.add_argument("--role", default=None, help="override role (auto-detected from stage if omitted)")
    exec_stage_parser.add_argument("--artifacts", nargs="+", default=None, help="artifact names to stream")
    exec_stage_parser.add_argument("--real", action="store_true", help="use real CLI adapters instead of stubs")
    exec_stage_parser.add_argument(
        "--assert-real",
        action="store_true",
        help="fail fast unless --real is also set; useful for CI jobs that must not silently run stubs",
    )

    validate_workflow_parser = subparsers.add_parser(
        "validate-workflow",
        help="validate a project .forgeflow/workflow.yaml overlay without executing stages",
    )
    validate_workflow_parser.add_argument(
        "--project-root",
        default=".",
        help="project root containing .forgeflow/workflow.yaml; defaults to current directory",
    )
    validate_workflow_parser.add_argument(
        "--workflow-path",
        help="explicit workflow overlay path; defaults to <project-root>/.forgeflow/workflow.yaml",
    )

    return parser


def _cwd_is_plugin_cache(cwd: Path) -> bool:
    parts = cwd.resolve().parts
    for index, part in enumerate(parts):
        if part == ".claude" and parts[index + 1 : index + 3] == ("plugins", "cache"):
            return True
        if part == ".codex" and len(parts) > index + 1 and parts[index + 1] in {"plugin", "plugins"}:
            return True
    return False


def _default_task_dir_for_init(task_id: str) -> Path:
    cwd = Path.cwd().resolve()
    if _cwd_is_plugin_cache(cwd):
        raise RuntimeViolation(
            "init default task-dir resolved inside a plugin cache; pass --task-dir pointing at the target project"
        )
    return (cwd / ".forgeflow" / "tasks" / task_id).resolve()


_DEFAULT_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"


def _slugify_init_objective(value: str) -> str:
    import re

    words = re.sub(r"[^a-z0-9\s-]", "", value.lower()).split()
    slug = "-".join(words[:6])
    if not slug:
        slug = f"task-{datetime.now().strftime(_DEFAULT_TIMESTAMP_FORMAT)}"
    return slug[:64]


def _init_task_id_from_args(task_dir: Path | None, task_id: str | None, objective: str | None) -> str:
    if task_id:
        return task_id
    if objective:
        return _slugify_init_objective(objective)
    if task_dir is not None:
        return task_dir.name
    return f"task-{datetime.now().strftime(_DEFAULT_TIMESTAMP_FORMAT)}"


def _task_dir_is_plugin_cache(task_dir: Path) -> bool:
    return _cwd_is_plugin_cache(task_dir)


def _command_mutates_task(command: str) -> bool:
    return command in {"start", "init", "clarify", "execute", "resume", "advance", "retry", "step-back", "escalate", "exec-stage"}


def _guard_mutating_task_dir(command: str, task_dir: Path) -> None:
    if not _command_mutates_task(command):
        return
    if _task_dir_is_plugin_cache(task_dir):
        raise RuntimeViolation(
            f"{command} refuses to mutate task artifacts inside a plugin or marketplace cache; "
            "pass --task-dir pointing at the target project .forgeflow/tasks/<task-id> directory"
        )


def _workflow_payload(*, project_root: Path, override_path: Path, policy) -> dict:
    workflow = resolve_project_workflow(project_root, policy, override_path=override_path)
    return {
        "status": "valid",
        "project_root": str(project_root),
        "override_path": str(override_path),
        "workflow_name": workflow.name,
        "schema_version": workflow.schema_version,
        "routes": workflow.routes,
        "steps": {
            step_id: {
                "id": step.id,
                "type": step.type,
                "role": step.role,
                "artifact_out": step.artifact_out,
                "required_for_entry": step.required_for_entry,
                "gate": step.gate,
                "non_negotiables": step.non_negotiables,
            }
            for step_id, step in workflow.steps.items()
        },
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        task_dir_arg = getattr(args, "task_dir", None)
        init_task_id: str | None = None
        policy = load_runtime_policy(ROOT)
        if args.command == "validate-workflow":
            project_root = Path(args.project_root).resolve()
            override_path = Path(args.workflow_path).resolve() if args.workflow_path else project_root / ".forgeflow" / "workflow.yaml"
            _print_payload(_workflow_payload(project_root=project_root, override_path=override_path, policy=policy))
            return 0

        if args.command == "init":
            explicit_task_dir = Path(task_dir_arg).resolve() if task_dir_arg else None
            init_task_id = _init_task_id_from_args(explicit_task_dir, getattr(args, "task_id", None), getattr(args, "objective", None))
            task_dir = explicit_task_dir or _default_task_dir_for_init(init_task_id)
        elif task_dir_arg:
            task_dir = Path(task_dir_arg).resolve()
        else:
            parser.error("--task-dir is required for this command")
        _guard_mutating_task_dir(args.command, task_dir)

        route_name = effective_route(
            task_dir=task_dir,
            explicit_route=getattr(args, "route", None),
            min_route=getattr(args, "min_route", None),
            violation_factory=RuntimeViolation,
        )
        if args.command == "start":
            _print_payload(start_task(task_dir=task_dir, policy=policy, route_name=route_name))
        elif args.command == "init":
            _print_payload(
                init_task(
                    task_dir=task_dir,
                    policy=policy,
                    task_id=init_task_id,
                    objective=args.objective,
                    risk_level=args.risk,
                )
            )
        elif args.command == "clarify":
            _print_payload(
                clarify_task(
                    task_dir=task_dir,
                    policy=policy,
                )
            )
        elif args.command == "execute":
            _print_payload(run_route(task_dir=task_dir, policy=policy, route_name=route_name))
        elif args.command == "resume":
            _print_payload(resume_task(task_dir=task_dir, policy=policy, route_name=route_name))
        elif args.command == "status":
            _print_payload(status_summary(task_dir=task_dir, policy=policy, route_name=route_name))
        elif args.command == "advance":
            if args.execute:
                _assert_real_requested(use_real=args.real, assert_real=args.assert_real)
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
        elif args.command == "exec-stage":
            _assert_real_requested(use_real=args.real, assert_real=args.assert_real)
            run_state_path = task_dir / "run-state.json"
            if not run_state_path.exists():
                print("ERROR: run-state.json not found; start or resume the task first.", file=sys.stderr)
                return 1
            run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
            current_stage = run_state.get("current_stage")
            if not current_stage:
                print("ERROR: current_stage not set in run-state.", file=sys.stderr)
                return 1
            role = args.role or role_for_stage(current_stage, violation_factory=RuntimeViolation)
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
            _print_stub_warning_if_needed(use_real=args.real)
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
