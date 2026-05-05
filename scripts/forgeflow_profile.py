#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forgeflow_runtime.profiling import (  # noqa: E402
    PipelineProfile,
    StageProfile,
    compare_profiles,
    detect_bottlenecks,
    format_comparison,
    format_summary,
)


def profile_path(task_dir: str | Path) -> Path:
    path = Path(task_dir).resolve()
    if path.is_file():
        return path
    return path / "pipeline-profile.json"


def load_profile(path: Path) -> PipelineProfile:
    if not path.is_file():
        raise SystemExit(f"Error: pipeline-profile.json not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error: invalid profile JSON {path}: {exc}") from exc
    return profile_from_payload(payload, source_name=str(path))


def profile_from_payload(payload: dict, *, source_name: str = "profile") -> PipelineProfile:
    required = {"pipeline_id", "route", "stages"}
    missing = sorted(required - set(payload))
    if missing:
        raise SystemExit(f"Error: {source_name} missing required field(s): {', '.join(missing)}")
    stages = tuple(stage_from_payload(stage, source_name=source_name) for stage in payload.get("stages", []))
    return PipelineProfile(
        pipeline_id=str(payload["pipeline_id"]),
        route=str(payload["route"]),
        stages=stages,
        total_duration_s=float(payload.get("total_duration_s", sum(s.duration_s for s in stages))),
        total_cost_usd=float(payload.get("total_cost_usd", sum(s.cost_usd for s in stages))),
        total_input_tokens=int(payload.get("total_input_tokens", sum(s.input_tokens for s in stages))),
        total_output_tokens=int(payload.get("total_output_tokens", sum(s.output_tokens for s in stages))),
        started_at=str(payload.get("started_at", "")),
        finished_at=str(payload.get("finished_at", "")),
    )


def stage_from_payload(payload: dict, *, source_name: str) -> StageProfile:
    required = {"stage", "model", "status", "duration_s", "input_tokens", "output_tokens"}
    missing = sorted(required - set(payload))
    if missing:
        raise SystemExit(f"Error: {source_name} stage missing required field(s): {', '.join(missing)}")
    input_tokens = int(payload["input_tokens"])
    output_tokens = int(payload["output_tokens"])
    return StageProfile(
        stage=str(payload["stage"]),
        model=str(payload["model"]),
        status=str(payload["status"]),
        duration_s=float(payload["duration_s"]),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=int(payload.get("total_tokens", input_tokens + output_tokens)),
        cost_usd=float(payload.get("cost_usd", 0.0)),
        error=payload.get("error"),
    )


def profile_to_payload(profile: PipelineProfile) -> dict:
    payload = asdict(profile)
    payload["stages"] = [asdict(stage) for stage in profile.stages]
    return payload


def cmd_summary(args: argparse.Namespace) -> int:
    profile = load_profile(profile_path(args.task_dir))
    if args.json:
        print(json.dumps(profile_to_payload(profile), ensure_ascii=False, indent=2))
    else:
        print(format_summary(profile))
    return 0


def cmd_bottlenecks(args: argparse.Namespace) -> int:
    profile = load_profile(profile_path(args.task_dir))
    bottlenecks = detect_bottlenecks(profile, top_n=args.top)
    if args.json:
        print(json.dumps({"bottlenecks": [asdict(b) for b in bottlenecks]}, ensure_ascii=False, indent=2))
        return 0
    if not bottlenecks:
        print("No bottlenecks found")
        return 0
    for item in bottlenecks:
        print(f"{item.metric}: {item.label}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    baseline = load_profile(profile_path(args.baseline))
    candidate = load_profile(profile_path(args.candidate))
    result = compare_profiles(baseline, candidate)
    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print(format_comparison(result))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ForgeFlow performance profile helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_summary = sub.add_parser("summary", help="show pipeline profile summary")
    p_summary.add_argument("task_dir", help="task directory or pipeline-profile.json path")
    p_summary.add_argument("--json", action="store_true")
    p_summary.set_defaults(func=cmd_summary)

    p_bottlenecks = sub.add_parser("bottlenecks", help="show slow/cost/token bottlenecks")
    p_bottlenecks.add_argument("task_dir", help="task directory or pipeline-profile.json path")
    p_bottlenecks.add_argument("--top", type=int, default=3)
    p_bottlenecks.add_argument("--json", action="store_true")
    p_bottlenecks.set_defaults(func=cmd_bottlenecks)

    p_compare = sub.add_parser("compare", help="compare two profile artifacts")
    p_compare.add_argument("baseline", help="baseline task directory or profile path")
    p_compare.add_argument("candidate", help="candidate task directory or profile path")
    p_compare.add_argument("--json", action="store_true")
    p_compare.set_defaults(func=cmd_compare)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
